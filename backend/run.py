import argparse
import json
import os
import random
import re
from pathlib import Path

from bonus import (
    RULES,
    Context,
    active_rivalries,
    prune_elims,
    synergy,
    update_pairs,
)
from championship import run_groups, run_knockout
from draft import run_draft
from engine import ROLES, Player, Team
from hall import career_kda, compact_season, season_key, update_hall
from league import load_league, next_season_id, save_league
from rankings import player_stats, rank_players, rank_teams, team_totals

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'docs' / 'data'


def build_teams(league):
    teams = []
    for tid, name in league['team_names'].items():
        pls = []
        for pid in league['rosters'][tid]:
            info = league['players'][pid]
            pls.append(
                Player(
                    pid,
                    info['nickname'],
                    info['role'],
                    tid,
                    league['bonus'].get(pid, 0),
                )
            )
        assert len(pls) == 5 and sorted(p.role for p in pls) == sorted(ROLES)
        teams.append(Team(tid, name, pls))
    assert len(teams) == 32
    return teams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', help='campeonato a simular, ex.: 2026-A')
    ap.add_argument(
        '--next',
        action='store_true',
        help='simula o próximo campeonato registrado em league.json',
    )
    ap.add_argument(
        '--start',
        default='2026-A',
        help='primeiro campeonato (usado só quando ainda não existe league.json)',
    )
    ap.add_argument('--seed', type=int)
    args = ap.parse_args()

    if bool(args.season) == bool(args.next):
        raise SystemExit('Use --season AAAA-X ou --next (apenas um dos dois)')
    league = load_league()
    if args.next:
        args.season = league['next_season'] or args.start
    if not re.fullmatch(r'\d{4}-[AB]', args.season):
        raise SystemExit('Use o formato AAAA-A ou AAAA-B (ex.: 2026-A)')
    if league['next_season'] and args.season != league['next_season']:
        raise SystemExit(
            f'Próxima temporada esperada: {league["next_season"]}'
        )
    season_file = OUT_DIR / f'season-{args.season}.json'
    if season_file.exists():
        raise SystemExit(
            'Temporada já simulada. Para resetar apague '
            'backend/data/league.json e docs/data/*'
        )

    seed = (
        args.seed
        if args.seed is not None
        else random.SystemRandom().randrange(2**32)
    )
    rng = random.Random(seed)

    teams = build_teams(league)
    by_id = {t.id: t for t in teams}
    players = [p for t in teams for p in t.players]

    # contexto das mecânicas de bônus (sinergia, rivalidade, bolha)
    ctx = Context(league['pairs'], league['elims'], league['season_no'])
    syn_start = {
        t.id: synergy([p.id for p in t.players], ctx.pairs) for t in teams
    }
    rivalries = active_rivalries(ctx.elims, ctx.season_no)

    matches = []
    groups = run_groups(teams, rng, matches, ctx)
    qualified = [
        by_id[r['team']] for g in groups.values() for r in g['table'][:4]
    ]
    champion, rounds, eliminated = run_knockout(qualified, rng, matches, ctx)

    totals = team_totals(teams, matches)
    team_rank = rank_teams(teams, champion, eliminated, totals, rng)
    stats, league_kda = player_stats(players, matches)
    overall, by_role = rank_players(stats)

    # histórico de partidas juntos (inclui este campeonato) e KDA de carreira
    update_pairs(ctx.pairs, teams, totals)
    hist = career_kda(OUT_DIR)
    draft = run_draft(
        league, team_rank, overall, by_role, hist, rng, ctx.pairs
    )

    team_group = {t.id: g for g, d in groups.items() for t in d['teams']}
    teams_out = []
    for pos, tid in enumerate(team_rank, 1):
        t = by_id[tid]
        teams_out.append({
            'id': t.id,
            'name': t.name,
            'group': team_group[t.id],
            'final_rank': pos,
            'eliminated_in': (
                'CHAMPION'
                if t.id == champion.id
                else eliminated.get(t.id, 'GROUP')
            ),
            **totals[t.id],
            'synergy': round(syn_start[t.id], 3),
            'players': [p.id for p in t.players],
        })

    season = {
        'season': args.season,
        'seed': seed,
        'rules': RULES,
        'league_kda': round(league_kda, 4),
        'teams': teams_out,
        'players': list(stats.values()),
        'groups': {
            g: {
                'teams': [t.id for t in d['teams']],
                'table': d['table'],
                'match_ids': d['match_ids'],
            }
            for g, d in groups.items()
        },
        'knockout': rounds,
        'matches': matches,
        'rivalries': rivalries,
        'rankings': {
            'teams': team_rank,
            'players_overall': overall,
            'players_by_role': by_role,
        },
        'awards': {
            'champion': champion.id,
            'best_overall': overall[0],
            'best_by_role': {r: ids[0] for r, ids in by_role.items()},
        },
        'draft': draft,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    compact_season(season)
    season_file.write_text(dump(season), encoding='utf-8')
    ids = sorted(
        (p.stem[len('season-') :] for p in OUT_DIR.glob('season-*.json')),
        key=season_key,
    )
    (OUT_DIR / 'seasons.json').write_text(dump(ids), encoding='utf-8')
    update_hall(OUT_DIR, season)

    league['rosters'] = draft['rosters_after']
    league['free_agents'] = draft['free_agents_after']
    league['bonus'] = draft['next_bonus']
    league['pairs'] = ctx.pairs
    league['season_no'] += 1
    league['elims'] = prune_elims(ctx.elims, league['season_no'])
    league['next_season'] = next_season_id(args.season)
    save_league(league)

    best = stats[overall[0]]
    s = draft['star']
    print(f'Temporada {args.season} (seed {seed})')
    print(f'Campeão: {by_id[champion.id].name}')
    print(f'Melhor geral: {best["nickname"]} (KDA pond. {best["kda_pond"]})')
    print(f'Draft: {best["nickname"]} -> {by_id[s["to_team"]].name}')
    print(f'Próxima temporada: {league["next_season"]}')

    # no GitHub Actions: expõe o campeonato simulado para as próximas etapas
    gh_out = os.environ.get('GITHUB_OUTPUT')
    if gh_out:
        with open(gh_out, 'a', encoding='utf-8') as f:
            f.write(
                f'season={args.season}\nchampion={by_id[champion.id].name}\n'
            )


if __name__ == '__main__':
    main()
