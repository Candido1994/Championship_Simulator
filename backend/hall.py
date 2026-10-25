"""Hall da Fama incremental.

Arquivos gerados em docs/data:
  hall.json            resumo leve: campeões e carreira de cada jogador
  players/<id>.jsonl   uma linha por campeonato disputado (só recebe novas linhas)

Cada campeonato novo atualiza apenas o resumo e acrescenta linhas, então o
custo por execução não cresce com o número de campeonatos já simulados.

Índice de carreira = 100 x KDA ponderado / média da liga
                     + 1,5 x títulos + 4 x melhor geral + 2 x melhor da função

Uso (opcional):
  python hall.py --rebuild   reconstrói tudo a partir dos season-*.json
  python hall.py --compact   reescreve os season-*.json antigos em formato enxuto
"""

import argparse
import json
from pathlib import Path

HALL_FILE = 'hall.json'
PLAYERS_DIR = 'players'

SHRINK_K = 10  # mesmo peso usado no KDA ponderado de cada campeonato
W_TITLE = 1.5
W_BEST_OVERALL = 4
W_BEST_ROLE = 2


def season_key(s):
    year, half = s.split('-')
    return int(year), half


def _dump(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


def compact_season(s):
    """Remove dados que o site não usa e arredonda o KDA das partidas."""
    for m in s['matches']:
        m.pop('totals', None)
        for line in m['players'].values():
            line['kda'] = round(line['kda'], 4)
    for p in s['players']:
        p.pop('kda_history', None)
    return s


def _empty():
    return {
        'seasons': [],
        'teams': {},
        'champions': [],
        'players': {},
        'mu_sum': 0.0,
        'mu_n': 0,
    }


def _load(data_dir):
    f = Path(data_dir) / HALL_FILE
    if not f.exists():
        return _empty()
    hall = json.loads(f.read_text(encoding='utf-8'))
    if hall['players'] and 'wk' not in hall['players'][0]['career']:
        raise SystemExit(
            'hall.json está em formato antigo. '
            'Rode uma vez: python hall.py --rebuild'
        )
    hall['players'] = {p['id']: p for p in hall['players']}
    return hall


def _apply(hall, s, rows):
    """Soma um campeonato ao resumo e separa as linhas de cada jogador."""
    aw = s['awards']
    hall['seasons'].append(s['season'])
    hall['teams'] = {t['id']: t['name'] for t in s['teams']}
    mu = s.get('league_kda')
    if mu is None:
        mu = sum(p['kda_avg'] for p in s['players']) / len(s['players'])
    hall['mu_sum'] = round(hall['mu_sum'] + mu, 6)
    hall['mu_n'] += 1
    hall['champions'].append({
        'season': s['season'],
        'champion': aw['champion'],
        'runner_up': s['rankings']['teams'][1],
        'best_overall': aw['best_overall'],
        'best_by_role': aw['best_by_role'],
    })
    for p in s['players']:
        e = hall['players'].setdefault(
            p['id'],
            {
                'id': p['id'],
                'nickname': p['nickname'],
                'role': p['role'],
                'awards_overall': 0,
                'awards_role': 0,
                'career': {
                    'seasons': 0,
                    'matches': 0,
                    'points': 0,
                    'assists': 0,
                    'defeats': 0,
                    'kda_w': 0.0,
                    'kda_avg': 0.0,
                    'w': 0.0,
                    'wk': 0.0,
                    'kda_pond': 0.0,
                    'index': 0.0,
                    'titles': 0,
                },
            },
        )
        c = e['career']
        champion = p['team_id'] == aw['champion']
        w = p.get('w', p['matches'])
        wk = p.get('wk', p['kda_avg'] * p['matches'])
        c['seasons'] += 1
        c['matches'] += p['matches']
        c['points'] += p['points']
        c['assists'] += p['assists']
        c['defeats'] += p['defeats']
        c['kda_w'] = round(c['kda_w'] + p['kda_avg'] * p['matches'], 6)
        c['kda_avg'] = round(c['kda_w'] / c['matches'], 4)
        c['w'] = round(c['w'] + w, 2)
        c['wk'] = round(c['wk'] + wk, 4)
        c['titles'] += int(champion)
        rows.setdefault(p['id'], []).append({
            'season': s['season'],
            'team_id': p['team_id'],
            'matches': p['matches'],
            'points': p['points'],
            'assists': p['assists'],
            'defeats': p['defeats'],
            'kda_avg': p['kda_avg'],
            'kda_pond': p.get('kda_pond', p['kda_avg']),
            'rank_overall': p['rank_overall'],
            'rank_role': p['rank_role'],
            'bonus': p['bonus'],
            'champion': champion,
        })
    hall['players'][aw['best_overall']]['awards_overall'] += 1
    for pid in aw['best_by_role'].values():
        hall['players'][pid]['awards_role'] += 1


def _finalize(hall):
    """Recalcula KDA ponderado e índice de carreira (dependem da média da liga)."""
    mu = hall['mu_sum'] / hall['mu_n'] if hall['mu_n'] else 1.0
    for e in hall['players'].values():
        c = e['career']
        c['kda_pond'] = round(
            (c['wk'] + SHRINK_K * mu) / (c['w'] + SHRINK_K), 4
        )
        c['index'] = round(
            100 * c['kda_pond'] / mu
            + W_TITLE * c['titles']
            + W_BEST_OVERALL * e['awards_overall']
            + W_BEST_ROLE * e['awards_role'],
            1,
        )


def _write_rows(data_dir, rows, mode):
    d = Path(data_dir) / PLAYERS_DIR
    d.mkdir(parents=True, exist_ok=True)
    for pid, lst in rows.items():
        with open(d / f'{pid}.jsonl', mode, encoding='utf-8') as f:
            f.write(''.join(_dump(r) + '\n' for r in lst))


def _save(data_dir, hall):
    _finalize(hall)
    out = dict(hall)
    out['players'] = sorted(
        hall['players'].values(),
        key=lambda e: (
            -e['career']['index'],
            -e['career']['points'],
            e['nickname'],
        ),
    )
    (Path(data_dir) / HALL_FILE).write_text(_dump(out), encoding='utf-8')


def update_hall(data_dir, season):
    """Chamado a cada campeonato novo (custo constante)."""
    hall = _load(data_dir)
    if season['season'] in hall['seasons']:
        return
    rows = {}
    _apply(hall, season, rows)
    _write_rows(data_dir, rows, 'a')
    _save(data_dir, hall)


def career_kda(data_dir):
    """KDA ponderado de carreira de cada jogador (usado no draft)."""
    return {
        pid: e['career']['kda_pond']
        for pid, e in _load(data_dir)['players'].items()
    }


def _season_files(data_dir):
    return sorted(
        Path(data_dir).glob('season-*.json'),
        key=lambda p: season_key(p.stem[len('season-') :]),
    )


def rebuild(data_dir):
    hall, rows = _empty(), {}
    for f in _season_files(data_dir):
        _apply(hall, json.loads(f.read_text(encoding='utf-8')), rows)
    pdir = Path(data_dir) / PLAYERS_DIR
    if pdir.exists():
        for old in pdir.glob('*.jsonl'):
            old.unlink()
    _write_rows(data_dir, rows, 'w')
    _save(data_dir, hall)
    print(
        f'Hall reconstruído com {len(hall["seasons"])} campeonatos '
        f'e {len(hall["players"])} jogadores.'
    )


def compact_all(data_dir):
    before = after = 0
    for f in _season_files(data_dir):
        before += f.stat().st_size
        f.write_text(
            _dump(compact_season(json.loads(f.read_text(encoding='utf-8')))),
            encoding='utf-8',
        )
        after += f.stat().st_size
    print(
        f'Campeonatos compactados: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB'
    )


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--compact', action='store_true')
    args = ap.parse_args()
    data = Path(__file__).resolve().parent.parent / 'docs' / 'data'
    if args.compact:
        compact_all(data)
    if args.rebuild:
        rebuild(data)
    if not (args.compact or args.rebuild):
        ap.print_help()
