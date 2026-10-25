import math
from dataclasses import dataclass

ROLES = ['TOP', 'JGL', 'MID', 'ADC', 'SUP']


@dataclass
class Player:
    id: str
    nickname: str
    role: str
    team_id: str
    bonus: int = 0  # nível do jogador (0 a 5); 0 = equilibrado

    def roll(self, rng):
        n = self.bonus
        return {
            'points': rng.randint(1 + n, 20 + n),  # faixa deslocada pelo nível
            'assists': rng.randint(
                1 + n, 20 + n
            ),  # faixa deslocada pelo nível
            'defeats': rng.randint(1, 20 - n),  # teto reduzido pelo nível
        }


@dataclass
class Team:
    id: str
    name: str
    players: list


def play_match(match_id, phase, a, b, rng, bonus_a=None, bonus_b=None):
    """bonus_a / bonus_b: dicts de bônus de placar (sinergia, rivalidade, bolha)."""
    bonus_a, bonus_b = bonus_a or {}, bonus_b or {}
    lines, totals = {}, {}
    for team in (a, b):
        t = {'points': 0, 'assists': 0, 'defeats': 0}
        for p in team.players:
            r = p.roll(rng)
            r['kda'] = (r['points'] + r['assists']) / r['defeats']
            lines[p.id] = r
            for k in t:
                t[k] += r[k]
        totals[team.id] = t

    ta, tb = totals[a.id], totals[b.id]
    score_a = math.ceil((ta['points'] + tb['defeats']) / 2) + bonus_a.get(
        'total', 0
    )
    score_b = math.ceil((tb['points'] + ta['defeats']) / 2) + bonus_b.get(
        'total', 0
    )

    tiebreak = None
    if score_a == score_b:
        if ta['assists'] != tb['assists']:
            tiebreak = 'assists'
            a_wins = ta['assists'] > tb['assists']
        else:
            tiebreak = 'draw'
            a_wins = rng.random() < 0.5
        if a_wins:
            score_a += 1
        else:
            score_b += 1

    match = {
        'id': match_id,
        'phase': phase,
        'team_a': a.id,
        'team_b': b.id,
        'score_a': score_a,
        'score_b': score_b,
        'winner': a.id if score_a > score_b else b.id,
        'tiebreak': tiebreak,
        'players': lines,
    }
    if bonus_a.get('total'):
        match['bonus_a'] = bonus_a
    if bonus_b.get('total'):
        match['bonus_b'] = bonus_b
    return match
