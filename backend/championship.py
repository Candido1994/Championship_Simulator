import itertools
from collections import Counter

from bonus import BUBBLE_FROM, match_bonus, register_elimination
from engine import play_match

GROUP_NAMES = 'ABCD'
KNOCKOUT_ROUNDS = [('R16', 3), ('QF', 3), ('SF', 3), ('F', 5)]


def schedule(members):
    """Calendário de turno e returno (método do círculo): 14 rodadas de 4 jogos."""
    n = len(members)
    fixed, rot = members[0], members[1:]
    rounds = []
    for _ in range(n - 1):
        arr = [fixed] + rot
        rounds.append([(arr[i], arr[n - 1 - i]) for i in range(n // 2)])
        rot = [rot[-1]] + rot[:-1]
    return rounds + [[(b, a) for a, b in rd] for rd in rounds]


def build_table(members, group_matches, rng):
    rows = {
        t.id: dict(
            team=t.id,
            played=0,
            wins=0,
            losses=0,
            points=0,
            score_for=0,
            score_against=0,
        )
        for t in members
    }
    for m in group_matches:
        sides = (
            (m['team_a'], m['score_a'], m['score_b']),
            (m['team_b'], m['score_b'], m['score_a']),
        )
        for tid, sf, sa in sides:
            r = rows[tid]
            r['played'] += 1
            r['score_for'] += sf
            r['score_against'] += sa
            if m['winner'] == tid:
                r['wins'] += 1
                r['points'] += 1
            else:
                r['losses'] += 1

    # 1º pontos, 2º placar total; 3º confronto direto; 4º sorteio
    ordered = sorted(
        rows.values(), key=lambda r: (-r['points'], -r['score_for'])
    )
    final = []
    for _, bucket in itertools.groupby(
        ordered, key=lambda r: (r['points'], r['score_for'])
    ):
        bucket = list(bucket)
        if len(bucket) > 1:
            ids = {r['team'] for r in bucket}
            h2h = Counter(
                m['winner']
                for m in group_matches
                if m['team_a'] in ids and m['team_b'] in ids
            )
            bucket.sort(key=lambda r: (-h2h[r['team']], rng.random()))
        final.extend(bucket)
    for pos, r in enumerate(final, 1):
        r['position'] = pos
    return final


def run_groups(teams, rng, matches, ctx):
    pool = teams[:]
    rng.shuffle(pool)  # sorteio dos grupos
    groups = {}
    for i, name in enumerate(GROUP_NAMES):
        members = pool[i * 8 : (i + 1) * 8]
        pts = {t.id: 0 for t in members}
        sf = {t.id: 0 for t in members}
        local = []
        for r, pairs in enumerate(schedule(members), 1):
            bubble = set()
            if (
                r >= BUBBLE_FROM
            ):  # 5º e 6º da tabela (antes da rodada) recebem o bônus
                order = sorted(
                    members, key=lambda t: (-pts[t.id], -sf[t.id], t.id)
                )
                bubble = {order[4].id, order[5].id}
            for n, (a, b) in enumerate(pairs, 1):
                ba = match_bonus(a, b, ctx, a.id in bubble)
                bb = match_bonus(b, a, ctx, b.id in bubble)
                m = play_match(
                    f'G{name}-R{r:02d}-{n}', f'group-{name}', a, b, rng, ba, bb
                )
                m['round'] = r
                local.append(m)
                for t, score in ((a, m['score_a']), (b, m['score_b'])):
                    sf[t.id] += score
                    ctx.played[t.id] += 1
                pts[m['winner']] += 1
        matches.extend(local)
        groups[name] = {
            'teams': members,
            'match_ids': [m['id'] for m in local],
            'table': build_table(members, local, rng),
        }
    return groups


def play_series(code, phase, best_of, a, b, rng, matches, ctx):
    need = best_of // 2 + 1
    wins = {a.id: 0, b.id: 0}
    game_ids = []
    while max(wins.values()) < need:
        ba = match_bonus(a, b, ctx)
        bb = match_bonus(b, a, ctx)
        m = play_match(
            f'{code}-J{len(game_ids) + 1}', phase, a, b, rng, ba, bb
        )
        matches.append(m)
        game_ids.append(m['id'])
        wins[m['winner']] += 1
        ctx.played[a.id] += 1
        ctx.played[b.id] += 1
    winner = a if wins[a.id] == need else b
    return winner, {
        'code': code,
        'team_a': a.id,
        'team_b': b.id,
        'wins_a': wins[a.id],
        'wins_b': wins[b.id],
        'winner': winner.id,
        'games': game_ids,
    }


def run_knockout(qualified, rng, matches, ctx):
    alive = qualified[:]
    rounds, eliminated = [], {}
    for phase, best_of in KNOCKOUT_ROUNDS:
        rng.shuffle(alive)  # novo sorteio a cada fase
        series_list, nxt = [], []
        for i in range(0, len(alive), 2):
            a, b = alive[i], alive[i + 1]
            winner, s = play_series(
                f'{phase}-{i // 2 + 1}',
                phase,
                best_of,
                a,
                b,
                rng,
                matches,
                ctx,
            )
            series_list.append(s)
            nxt.append(winner)
            loser = b if winner is a else a
            eliminated[loser.id] = phase
            register_elimination(ctx, winner.id, loser.id)
        rounds.append({
            'phase': phase,
            'best_of': best_of,
            'series': series_list,
        })
        alive = nxt
    return alive[0], rounds, eliminated
