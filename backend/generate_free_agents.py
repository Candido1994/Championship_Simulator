import json
import random
from pathlib import Path

from generate_teams import PREFIXES, ROLES, SUFFIXES

DATA = Path(__file__).parent / 'data'


def main():
    teams = json.loads((DATA / 'teams.json').read_text(encoding='utf-8'))[
        'teams'
    ]
    used = {p['nickname'] for t in teams for p in t['players']}
    combos = [p + s for p in PREFIXES for s in SUFFIXES if p + s not in used]
    nicks = random.Random(777).sample(combos, 15)  # seed fixa

    players = []
    for i, role in enumerate(ROLES):
        for j in range(3):  # 3 free agents por função
            nick = nicks[i * 3 + j]
            players.append({
                'id': nick.lower(),
                'nickname': nick,
                'role': role,
            })

    out = DATA / 'free_agents.json'
    out.write_text(
        json.dumps({'free_agents': players}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f'{len(players)} free agents gerados em {out}')


if __name__ == '__main__':
    main()
