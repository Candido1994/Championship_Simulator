from engine import ROLES

STAGE_ORDER = {'F': 1, 'SF': 2, 'QF': 3, 'R16': 4, 'GROUP': 5}

# KDA ponderado: peso de cada jogo pela importância da fase (grupos = 1,0)
PHASE_W = {'R16': 1.25, 'QF': 1.5, 'SF': 1.75, 'F': 2.0}
SHRINK_K = 10  # "jogos virtuais" na média da liga: evita que poucos jogos liderem por sorte


def phase_weight(phase):
    return PHASE_W.get(phase, 1.0)


def team_totals(teams, matches):
    tot = {
        t.id: dict(matches=0, wins=0, losses=0, score_for=0, score_against=0)
        for t in teams
    }
    for m in matches:
        for tid, sf, sa in (
            (m['team_a'], m['score_a'], m['score_b']),
            (m['team_b'], m['score_b'], m['score_a']),
        ):
            t = tot[tid]
            t['matches'] += 1
            t['score_for'] += sf
            t['score_against'] += sa
            t['wins' if m['winner'] == tid else 'losses'] += 1
    return tot


def rank_teams(teams, champion, eliminated, totals, rng):
    """Ordem final: campeão, vice, semis, quartas, oitavas e fase de grupos.

    Eliminados na fase de grupos: vitórias, depois placar total e, por fim,
    placar contra (menor é melhor). Nas demais fases: placar total.
    """

    def key(t):
        tot = totals[t.id]
        if t.id == champion.id:
            return (0, 0, -tot['score_for'], 0, rng.random())
        stage = STAGE_ORDER[eliminated.get(t.id, 'GROUP')]
        if stage == STAGE_ORDER['GROUP']:
            return (
                stage,
                -tot['wins'],
                -tot['score_for'],
                tot['score_against'],
                rng.random(),
            )
        return (stage, 0, -tot['score_for'], 0, rng.random())

    return [t.id for t in sorted(teams, key=key)]


def player_stats(players, matches):
    """Retorna (estatísticas por jogador, KDA médio da liga no campeonato)."""
    st = {
        p.id: {
            'id': p.id,
            'nickname': p.nickname,
            'role': p.role,
            'team_id': p.team_id,
            'bonus': p.bonus,
            'matches': 0,
            'points': 0,
            'assists': 0,
            'defeats': 0,
            'kda_sum': 0.0,
            'w': 0.0,
            'wk': 0.0,
        }
        for p in players
    }
    total_kda, lines = 0.0, 0
    for m in matches:
        w = phase_weight(m['phase'])
        for pid, line in m['players'].items():
            s = st[pid]
            s['matches'] += 1
            s['points'] += line['points']
            s['assists'] += line['assists']
            s['defeats'] += line['defeats']
            s['kda_sum'] += line['kda']
            s['w'] += w
            s['wk'] += w * line['kda']
            total_kda += line['kda']
            lines += 1
    mu = total_kda / lines
    for s in st.values():
        s['kda_avg'] = s.pop('kda_sum') / s['matches']
        s['kda_pond'] = (s['wk'] + SHRINK_K * mu) / (s['w'] + SHRINK_K)
        s['w'] = round(s['w'], 2)
        s['wk'] = round(s['wk'], 4)
    return st, mu


def rank_players(stats):
    """Ranking pelo KDA ponderado (desempate: soma de pontos)."""
    key = lambda s: (-s['kda_pond'], -s['points'], s['nickname'])
    overall = sorted(stats.values(), key=key)
    by_role = {
        r: sorted((s for s in stats.values() if s['role'] == r), key=key)
        for r in ROLES
    }
    for i, s in enumerate(overall, 1):
        s['rank_overall'] = i
    for lst in by_role.values():
        for i, s in enumerate(lst, 1):
            s['rank_role'] = i
    for s in stats.values():
        s['kda_avg'] = round(s['kda_avg'], 4)
        s['kda_pond'] = round(s['kda_pond'], 4)
    return (
        [s['id'] for s in overall],
        {r: [s['id'] for s in lst] for r, lst in by_role.items()},
    )
