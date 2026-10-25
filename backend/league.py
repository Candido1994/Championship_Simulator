import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
LEAGUE_FILE = DATA / 'league.json'


def next_season_id(season):
    year, half = season.split('-')
    return f'{year}-B' if half == 'A' else f'{int(year) + 1}-A'


def init_league():
    teams = json.loads((DATA / 'teams.json').read_text(encoding='utf-8'))[
        'teams'
    ]
    fas = json.loads((DATA / 'free_agents.json').read_text(encoding='utf-8'))[
        'free_agents'
    ]
    players, rosters = {}, {}
    for t in teams:
        rosters[t['id']] = []
        for p in t['players']:
            pid = p['nickname'].lower()
            players[pid] = {
                'id': pid,
                'nickname': p['nickname'],
                'role': p['role'],
            }
            rosters[t['id']].append(pid)
    for p in fas:
        players[p['id']] = dict(p)
    return {
        'next_season': None,
        'season_no': 0,  # campeonatos já concluídos
        'team_names': {t['id']: t['name'] for t in teams},
        'players': players,
        'rosters': rosters,
        'free_agents': [p['id'] for p in fas],
        'bonus': {},  # nível de cada jogador (0 a 5)
        'pairs': {},  # partidas que cada par jogou junto (sinergia)
        'elims': {},  # eliminações entre times (rivalidade)
    }


def load_league():
    if LEAGUE_FILE.exists():
        league = json.loads(LEAGUE_FILE.read_text(encoding='utf-8'))
        league.setdefault('season_no', 0)
        league.setdefault('pairs', {})
        league.setdefault('elims', {})
        return league
    return init_league()


def save_league(league):
    # formato compacto: o histórico de pares pode ter milhares de entradas
    LEAGUE_FILE.write_text(
        json.dumps(league, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8',
    )
