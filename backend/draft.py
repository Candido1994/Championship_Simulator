from bonus import pair_value
from engine import ROLES

LEVEL_CAP = 5  # nível máximo
LEVEL_UP_TOP = 5  # top N da função sobem 1 nível
LEVEL_BEST_OVERALL_EXTRA = 1  # nível extra para o melhor geral do campeonato
LEVEL_DOWN_AFTER = 16  # quem termina abaixo dessa posição desce 1 nível
WORST_PER_ROLE = 3
DRAFT_SYNERGY_W = 0.25  # peso da sinergia na escolha dos free agents


def update_levels(levels, by_role, overall):
    """Nível acumulado: persiste com o jogador entre campeonatos e times.

    Top N da função: +1. Melhor geral: +1 extra (total +2, pois ele
    também é o 1º da função). Abaixo da posição LEVEL_DOWN_AFTER: -1.
    """
    best = overall[0]
    new, changes = dict(levels), []
    for ids in by_role.values():
        for pos, pid in enumerate(ids, 1):
            before = levels.get(pid, 0)
            after = before
            if pos <= LEVEL_UP_TOP:
                after = before + 1
                if pid == best:
                    after += LEVEL_BEST_OVERALL_EXTRA
                after = min(LEVEL_CAP, after)
            elif pos > LEVEL_DOWN_AFTER:
                after = max(0, before - 1)
            if after:
                new[pid] = after
            else:
                new.pop(pid, None)
            if after != before:
                changes.append({
                    'player': pid,
                    'before': before,
                    'after': after,
                })
    return new, changes


def run_draft(league, team_rank, overall, by_role, hist, rng, pairs):
    """hist: {player_id: KDA ponderado de carreira} (só quem tem histórico).
    pairs: partidas jogadas juntos por cada par de jogadores (sinergia)."""
    players = league['players']
    rosters = {t: list(ids) for t, ids in league['rosters'].items()}
    owner = {pid: t for t, ids in rosters.items() for pid in ids}

    # 1) Draft da estrela: vai para o pior time (troca na mesma função)
    star = overall[0]
    from_team = owner[star]
    role = players[star]['role']
    to_team = next(t for t in reversed(team_rank) if t != from_team)
    swapped = next(p for p in rosters[to_team] if players[p]['role'] == role)
    rosters[to_team][rosters[to_team].index(swapped)] = star
    rosters[from_team][rosters[from_team].index(star)] = swapped
    owner[star], owner[swapped] = to_team, from_team
    star_log = {
        'player': star,
        'role': role,
        'from_team': from_team,
        'to_team': to_team,
        'swapped': swapped,
    }

    # 2) Os 3 piores de cada função são liberados
    released = []
    for r in ROLES:
        ranking = by_role[r]
        for pid in ranking[-WORST_PER_ROLE:]:
            released.append({
                'player': pid,
                'team': owner[pid],
                'role': r,
                'rank_role': ranking.index(pid) + 1,
            })

    # 3) Draft dos free agents: do campeão ao último colocado.
    #    Valor do candidato = KDA de carreira relativo à média + peso x sinergia
    #    com os 4 colegas que ficam no elenco (novatos entram neutros no KDA).
    pool = {
        r: [p for p in league['free_agents'] if players[p]['role'] == r]
        for r in ROLES
    }
    vacancies = {}
    for x in released:
        vacancies.setdefault(x['team'], []).append(x)
    mean_kda = sum(hist.values()) / len(hist) if hist else None

    picks = []
    for tid in team_rank:
        for x in sorted(
            vacancies.get(tid, []), key=lambda v: ROLES.index(v['role'])
        ):
            mates = [m for m in rosters[tid] if m != x['player']]

            def syn_with(p):
                return sum(pair_value(pairs, p, m) for m in mates) / len(mates)

            def value(p):
                rel = (
                    (hist[p] / mean_kda - 1)
                    if (mean_kda and p in hist)
                    else 0.0
                )
                return rel + DRAFT_SYNERGY_W * syn_with(p)

            cands = pool[x['role']]
            cands.sort(key=lambda p: (-value(p), rng.random()))
            new = cands.pop(0)
            rosters[tid][rosters[tid].index(x['player'])] = new
            picks.append({
                'order': len(picks) + 1,
                'team': tid,
                'role': x['role'],
                'player': new,
                'replaces': x['player'],
                'career_kda': hist.get(new),
                'synergy': round(syn_with(new), 3),
            })

    free_after = [p for r in ROLES for p in pool[r]] + [
        x['player'] for x in released
    ]
    levels, changes = update_levels(league['bonus'], by_role, overall)
    return {
        'star': star_log,
        'released': released,
        'picks': picks,
        'free_agents_after': free_after,
        'next_bonus': levels,
        'level_changes': changes,
        'rosters_after': rosters,
        'players': {
            pid: {'nickname': p['nickname'], 'role': p['role']}
            for pid, p in players.items()
        },
    }
