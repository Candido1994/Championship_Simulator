"""Bônus de placar: sinergia, rivalidade e bolha da fase de grupos.

Todos entram como pontos somados ao placar do time na partida (não alteram o
KDA dos jogadores) e o total por partida é limitado por TOTAL_CAP.
"""

import itertools
from collections import Counter

SYN_MAX = 3  # bônus máximo de sinergia (elenco com todos os pares entrosados)
SYN_CAP = (
    120  # partidas juntas para um par atingir sinergia total (~6 campeonatos)
)
RIV_UNIT = 1  # pontos por eliminação sofrida para o mesmo rival
RIV_CAP = 2  # bônus máximo de rivalidade
RIV_WINDOW = (
    8  # campeonatos considerados (eliminações mais antigas deixam de contar)
)
BUBBLE = 3  # bônus dos times em 5º e 6º no grupo
BUBBLE_FROM = 6  # rodada (de 14) em que a bolha passa a valer
TOTAL_CAP = 4  # bônus total máximo por partida

RULES = {
    'syn_max': SYN_MAX,
    'syn_cap': SYN_CAP,
    'riv_unit': RIV_UNIT,
    'riv_cap': RIV_CAP,
    'riv_window': RIV_WINDOW,
    'bubble': BUBBLE,
    'bubble_from': BUBBLE_FROM,
    'total_cap': TOTAL_CAP,
}


class Context:
    """Estado compartilhado durante um campeonato."""

    def __init__(self, pairs, elims, season_no):
        self.pairs = pairs  # {"a|b": partidas jogadas juntos}
        self.elims = elims  # {"vencedor|eliminado": [nº dos campeonatos]}
        self.season_no = season_no  # campeonatos já concluídos antes deste
        self.played = Counter()  # jogos de cada time neste campeonato


def pair_key(a, b):
    return '|'.join(sorted((a, b)))


def pair_value(pairs, a, b, extra=0):
    return min(1.0, (pairs.get(pair_key(a, b), 0) + extra) / SYN_CAP)


def synergy(ids, pairs, extra=0):
    """Sinergia do elenco (0 a 1): média dos 10 pares de jogadores."""
    combos = list(itertools.combinations(ids, 2))
    return sum(pair_value(pairs, a, b, extra) for a, b in combos) / len(combos)


def rivalry_count(elims, rival_id, team_id, season_no):
    """Quantas vezes rival_id eliminou team_id dentro da janela."""
    return sum(
        1
        for s in elims.get(f'{rival_id}|{team_id}', [])
        if season_no - s <= RIV_WINDOW
    )


def match_bonus(team, opp, ctx, bubble=False):
    ids = [p.id for p in team.players]
    syn = round(SYN_MAX * synergy(ids, ctx.pairs, ctx.played[team.id]))
    riv = min(
        RIV_CAP,
        RIV_UNIT * rivalry_count(ctx.elims, opp.id, team.id, ctx.season_no),
    )
    bub = BUBBLE if bubble else 0
    out = {k: v for k, v in (('syn', syn), ('riv', riv), ('bub', bub)) if v}
    out['total'] = min(TOTAL_CAP, syn + riv + bub)
    return out


def register_elimination(ctx, winner_id, loser_id):
    """O vencedor da série elimina o perdedor; a dívida do vencedor com o perdedor zera."""
    ctx.elims.setdefault(f'{winner_id}|{loser_id}', []).append(ctx.season_no)
    ctx.elims.pop(f'{loser_id}|{winner_id}', None)


def active_rivalries(elims, season_no):
    out = []
    for key in sorted(elims):
        winner, loser = key.split('|')
        n = rivalry_count(elims, winner, loser, season_no)
        if n:
            out.append({
                'team': loser,
                'rival': winner,
                'bonus': min(RIV_CAP, RIV_UNIT * n),
            })
    return out


def update_pairs(pairs, teams, totals):
    """Soma ao histórico as partidas que cada par de jogadores jogou junto."""
    for t in teams:
        games = totals[t.id]['matches']
        for a, b in itertools.combinations([p.id for p in t.players], 2):
            k = pair_key(a, b)
            pairs[k] = pairs.get(k, 0) + games


def prune_elims(elims, next_season_no):
    """Descarta eliminações fora da janela (mantém o arquivo pequeno)."""
    out = {}
    for key, seasons in elims.items():
        keep = [s for s in seasons if next_season_no - s <= RIV_WINDOW]
        if keep:
            out[key] = keep
    return out
