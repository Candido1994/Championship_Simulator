'use strict';

const ROLES = ['TOP', 'JGL', 'MID', 'ADC', 'SUP'];
const PHASES = { R16: 'Oitavas', QF: 'Quartas', SF: 'Semifinal', F: 'Final' };
const RESULT = { CHAMPION: 'Campeão', F: 'Vice-campeão', SF: 'Semifinal',
  QF: 'Quartas', R16: 'Oitavas', GROUP: 'Fase de grupos' };

const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmt = n => Number(n).toFixed(2);
const qs = k => new URLSearchParams(location.search).get(k);
const phaseName = p => p.startsWith('group-') ? 'Grupo ' + p.slice(6) : (PHASES[p] || p);
const tl = id => `<a href="team.html?id=${esc(id)}">${esc(App.team[id].name)}</a>`;
const pname = id => (App.player[id] || App.reg[id] || App.hallp[id] || { nickname: id }).nickname;
const pl = id => `<a href="player.html?id=${esc(id)}">${esc(pname(id))}</a>`;

const table = (heads, rows) => {
  // cabeçalho acompanha o alinhamento da coluna (células com class="l" ficam à esquerda)
  const left = rows.length ? (rows[0].match(/<td[^>]*>/g) || []).map(t => /class="l"/.test(t)) : [];
  return `<div class="tablewrap" role="region" aria-label="Tabela de dados" tabindex="0"><table><thead><tr>` +
    `${heads.map((h, i) => `<th scope="col"${left[i] ? ' class="l"' : ''}>${h}</th>`).join('')}</tr></thead>` +
    `<tbody>${rows.join('')}</tbody></table></div>`;
};

const kp = p => p.kda_pond ?? p.kda_avg;  // KDA ponderado (campeonatos antigos só têm o médio)
const BONUS_LABEL = { syn: 'sinergia', riv: 'rivalidade', bub: 'bolha (5º/6º)' };
const bonusTag = b => {
  if (!b || !b.total) return '';
  const parts = Object.keys(BONUS_LABEL).filter(k => b[k]).map(k => `${BONUS_LABEL[k]} +${b[k]}`).join(', ');
  const text = `Bônus de placar +${b.total}: ${parts}`;
  return ` <span class="tag" title="${text}" aria-label="${text}">+${b.total}</span>`;
};

function matchLine(m) {
  const c = id => (id === m.winner ? 'win' : '');
  const why = m.tiebreak === 'assists' ? 'assistências' : 'sorteio';
  const tb = m.tiebreak
    ? ` <span class="tag" title="Desempate por ${why}" aria-label="ponto extra de desempate por ${why}">+1</span>` : '';
  return `<div class="match"><span class="${c(m.team_a)}">${tl(m.team_a)}${bonusTag(m.bonus_a)}</span>` +
    `<b>${m.score_a} x ${m.score_b}${tb}</b><span class="${c(m.team_b)}">${tl(m.team_b)}${bonusTag(m.bonus_b)}</span></div>`;
}

// jogos de um grupo separados por rodada
function roundsHtml(gr) {
  const by = {};
  gr.match_ids.forEach(id => { const m = App.match[id]; (by[m.round || 0] = by[m.round || 0] || []).push(m); });
  return Object.entries(by).map(([r, ms]) =>
    (r > 0 ? `<p class="sub" style="margin:12px 0 2px"><b>Rodada ${r}</b></p>` : '') +
    ms.map(matchLine).join('')).join('');
}

function bars(vals, avg) {
  const max = Math.max(...vals), w = 100 / vals.length;
  const rects = vals.map((v, i) => {
    const h = (v / max) * 36;
    return `<rect x="${i * w + w * 0.1}" y="${38 - h}" width="${w * 0.8}" height="${h}" fill="var(--accent2)"/>`;
  }).join('');
  const y = 38 - (avg / max) * 36;
  return `<svg class="chart" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" ` +
    `aria-label="Gráfico de barras com o KDA de cada partida; a linha tracejada marca a média">${rects}` +
    `<line x1="0" x2="100" y1="${y}" y2="${y}" stroke="var(--accent)" stroke-dasharray="2 2" ` +
    `stroke-width="1" vector-effect="non-scaling-stroke"/></svg>`;
}

const stat = (k, v) => `<div class="card"><div class="k">${k}</div><div class="v">${v}</div></div>`;
const star = p => p.bonus ? ` <span class="tag">★${p.bonus}</span>` : '';
const power = t => t.players.reduce((sum, id) => sum + (App.player[id].bonus || 0), 0);
const tabButtons = (items, cur, fn, label) =>
  `<div class="tabs" role="group" aria-label="${label}">` + items.map(r =>
    `<button class="${r === cur ? 'on' : ''}" aria-pressed="${r === cur}" onclick="${fn}('${r}')">` +
    `${r === 'ALL' ? 'Geral' : r}</button>`).join('') + `</div>`;
const keepFocus = () => { const b = document.querySelector('.tabs button.on'); if (b) b.focus(); };

const PAGES = {
  index(d) {
    const [champ, vice, s1, s2] = d.teams;
    const f = d.knockout[3].series[0];
    const wW = f.winner === f.team_a ? f.wins_a : f.wins_b;
    const wL = f.winner === f.team_a ? f.wins_b : f.wins_a;
    const best = App.player[d.awards.best_overall];
    const roleCards = ROLES.map(r => {
      const p = App.player[d.awards.best_by_role[r]];
      return `<div class="card"><div class="k">Melhor ${r}</div><div class="v">${pl(p.id)}</div>` +
        `<p class="sub">${tl(p.team_id)} · KDA pond. ${fmt(kp(p))}</p></div>`;
    }).join('');
    return `<h1>Campeonato ${d.season}</h1><p class="sub">Seed da simulação: ${d.seed}</p>
    <div class="grid">
      <div class="card gold"><div class="k">Campeão</div><div class="v">🏆 ${tl(champ.id)}</div>
        <p class="sub">Final: ${wW} x ${wL}</p></div>
      <div class="card"><div class="k">Vice-campeão</div><div class="v">${tl(vice.id)}</div></div>
      <div class="card"><div class="k">3º e 4º</div><div class="v">${tl(s1.id)} · ${tl(s2.id)}</div></div>
      <div class="card gold"><div class="k">Melhor jogador geral</div><div class="v">${pl(best.id)}</div>
        <p class="sub">${best.role} · ${tl(best.team_id)} · KDA pond. ${fmt(kp(best))}</p></div>
    </div>
    <h2>Melhor por função</h2><div class="grid roles">${roleCards}</div>`;
  },

  groups(d) {
    const R = d.rules || {};
    const bubble = R.bubble ? ` A partir da rodada ${R.bubble_from}, os times em 5º e 6º recebem +${R.bubble} no placar (bolha).` : '';
    return `<h1>Fase de grupos · ${d.season}</h1><p class="sub">Os 4 primeiros de cada grupo avançam (barra verde). ` +
      `Desempate: placar total, depois confronto direto.${bubble}</p>` +
      Object.entries(d.groups).map(([g, gr]) => `<h2>Grupo ${g}</h2>` +
        table(['Time', 'J', 'V', 'D', 'Pts', 'Placar', 'Contra'], gr.table.map(r =>
          `<tr class="${r.position <= 4 ? 'q' : ''}"><td>${r.position}. ${tl(r.team)}</td>` +
          `<td>${r.played}</td><td>${r.wins}</td><td>${r.losses}</td><td><b>${r.points}</b></td>` +
          `<td>${r.score_for}</td><td>${r.score_against}</td></tr>`)) +
        `<details><summary>Jogos por rodada (${gr.match_ids.length})</summary>` +
        roundsHtml(gr) + `</details>`).join('');
  },

  knockout(d) {
    return `<h1>Mata-mata · ${d.season}</h1><p class="sub">Novo sorteio a cada fase.</p><div class="rounds">` +
      d.knockout.map(r => `<div><h2>${PHASES[r.phase]} · melhor de ${r.best_of}</h2>` +
        r.series.map(s => `<div class="series">
          <div class="row ${s.winner === s.team_a ? 'w' : ''}"><span>${tl(s.team_a)}</span><span>${s.wins_a}</span></div>
          <div class="row ${s.winner === s.team_b ? 'w' : ''}"><span>${tl(s.team_b)}</span><span>${s.wins_b}</span></div>
          <details><summary>Jogos</summary>${s.games.map(id => matchLine(App.match[id])).join('')}</details>
        </div>`).join('') + `</div>`).join('') + `</div>`;
  },

  teams(d) {
    return `<h1>Ranking final dos times · ${d.season}</h1><p class="sub">Eliminados na fase de grupos: vitórias, depois placar total e, por fim, menor placar contra. Nas demais fases: placar total. Força = soma dos níveis ★ do elenco (0 a 25). Sinergia = entrosamento do elenco no início do campeonato (partidas jogadas juntos).</p>` +
      table(['#', 'Time', 'Resultado', 'Grupo', 'Força', 'Sinergia', 'J', 'V', 'D', 'Placar', 'Contra'], d.teams.map(t =>
        `<tr><td>${t.final_rank}</td><td class="l">${tl(t.id)}</td><td class="l">${RESULT[t.eliminated_in]}</td>` +
        `<td>${t.group}</td><td>${power(t)}</td><td>${t.synergy != null ? Math.round(t.synergy * 100) + '%' : '–'}</td><td>${t.matches}</td><td>${t.wins}</td><td>${t.losses}</td>` +
        `<td>${t.score_for}</td><td>${t.score_against}</td></tr>`));
  },

  team(d) {
    const t = App.team[qs('id')];
    if (!t) return '<p>Time não encontrado.</p>';
    const ps = ROLES.map(r => t.players.map(i => App.player[i]).find(p => p.role === r));
    const rivals = (d.rivalries || []).filter(r => r.team === t.id);
    const hist = d.matches.filter(m => m.team_a === t.id || m.team_b === t.id).map(m => {
      const a = m.team_a === t.id;
      const opp = a ? m.team_b : m.team_a;
      const w = m.winner === t.id;
      return `<tr><td>${phaseName(m.phase)}</td><td class="l">${tl(opp)}</td>` +
        `<td>${a ? m.score_a : m.score_b} x ${a ? m.score_b : m.score_a}</td>` +
        `<td class="${w ? 'win' : 'lose'}">${w ? 'V' : 'D'}</td></tr>`;
    });
    return `<h1>${esc(t.name)}</h1><p class="sub">${d.season} · Grupo ${t.group} · ${RESULT[t.eliminated_in]} · ${t.final_rank}º lugar</p>
    <div class="grid stats">${stat('Vitórias', t.wins)}${stat('Derrotas', t.losses)}
      ${stat('Placar total', t.score_for)}${stat('Placar contra', t.score_against)}</div>
    <h2>Elenco em ${d.season}</h2>
    <p class="sub">Força do elenco: <b>${power(t)}</b> (soma dos níveis ★, de 0 a 25)` +
      (t.synergy != null ? ` · Sinergia no início do campeonato: <b>${Math.round(t.synergy * 100)}%</b>` : '') + `</p>` +
      (d.rivalries ? `<p class="sub">Rivalidades ativas: ${rivals.length ? rivals.map(r => `${tl(r.rival)} (+${r.bonus})`).join(', ') : 'nenhuma'}</p>` : '') +
      table(['Função', 'Jogador', 'KDA pond.', 'KDA médio', 'Pontos', 'Assist.', 'Derrotas'], ps.map(p =>
        `<tr><td>${p.role}</td><td class="l">${pl(p.id)}${star(p)}</td><td><b>${fmt(kp(p))}</b></td><td>${fmt(p.kda_avg)}</td>` +
        `<td>${p.points}</td><td>${p.assists}</td><td>${p.defeats}</td></tr>`)) +
      `<h2>Partidas</h2>` + table(['Fase', 'Adversário', 'Placar', 'Res.'], hist);
  },

  players(d) {
    window.setTab = r => { App.tab = r; $('#app').innerHTML = PAGES.players(d); keepFocus(); };
    const cur = App.tab || 'ALL';
    const ids = cur === 'ALL' ? d.rankings.players_overall : d.rankings.players_by_role[cur];
    return `<h1>Ranking de jogadores · ${d.season}</h1>
      <p class="sub">Ranking pelo KDA ponderado: jogos decisivos pesam mais e poucos jogos puxam para a média da liga (desempate: soma de pontos). ★n = nível do jogador.</p>` +
      tabButtons(['ALL', ...ROLES], cur, 'setTab', 'Filtrar por função') +
      table(['#', 'Jogador', 'Função', 'Time', 'KDA pond.', 'KDA médio', 'Pontos', 'Assist.', 'Derrotas', 'Jogos'],
        ids.map((id, i) => { const p = App.player[id];
          return `<tr><td>${i + 1}</td><td class="l">${pl(id)}${star(p)}</td><td>${p.role}</td>` +
            `<td class="l">${tl(p.team_id)}</td><td><b>${fmt(kp(p))}</b></td><td>${fmt(p.kda_avg)}</td><td>${p.points}</td>` +
            `<td>${p.assists}</td><td>${p.defeats}</td><td>${p.matches}</td></tr>`; }));
  },

  player(d) {
    const id = qs('id');
    const h = App.hallp[id], cur = App.player[id];
    const base = h || cur;
    if (!base) return '<p>Jogador não encontrado.</p>';
    let html = `<h1>${esc(base.nickname)}</h1><p class="sub">${base.role} · ` +
      (cur ? tl(cur.team_id) : `sem time em ${d.season}`) + `</p>`;
    if (h) {
      const c = h.career;
      html += `<h2>Carreira</h2><div class="grid stats">` +
        `${stat('Índice de carreira', c.index != null ? Number(c.index).toFixed(1) : '–')}` +
        `${stat('KDA ponderado', fmt(c.kda_pond != null ? c.kda_pond : c.kda_avg))}${stat('KDA médio', fmt(c.kda_avg))}` +
        `${stat('Jogos', c.matches)}${stat('Temporadas', c.seasons)}${stat('Títulos', c.titles)}` +
        `${stat('Melhor geral', h.awards_overall)}${stat('Melhor da função', h.awards_role)}</div>` +
        `<h2>Por campeonato</h2><div id="career-table"><p class="sub">Carregando histórico…</p></div>`;
    }
    if (cur) {
      const hist = App.kh[cur.id] || [];
      const kdas = hist.map(x => x.kda);
      const rows = hist.map(x => {
        const m = App.match[x.match], l = m.players[cur.id];
        const opp = m.team_a === cur.team_id ? m.team_b : m.team_a;
        const w = m.winner === cur.team_id;
        return `<tr><td>${phaseName(m.phase)}</td><td class="l">${tl(opp)}</td><td>${l.points}</td>` +
          `<td>${l.assists}</td><td>${l.defeats}</td><td><b>${fmt(l.kda)}</b></td>` +
          `<td class="${w ? 'win' : 'lose'}">${w ? 'V' : 'D'}</td></tr>`;
      });
      html += `<h2>KDA por partida · ${d.season}</h2>${bars(kdas, cur.kda_avg)}<h2>Histórico · ${d.season}</h2>` +
        table(['Fase', 'Adversário', 'P', 'A', 'D', 'KDA', 'Res.'], rows);
    }
    return html;
  },

  draft(d) {
    const dr = d.draft, s = dr.star;
    const own = {};
    Object.entries(dr.rosters_after).forEach(([t, ids]) => ids.forEach(i => { own[i] = t; }));
    const kda = i => (App.player[i] ? fmt(kp(App.player[i])) : '–');
    return `<h1>Draft após ${d.season}</h1>
      <p class="sub">1º a estrela vai para o pior time; depois o campeão escolhe primeiro entre os free agents, pelo KDA de carreira e pela sinergia com os colegas que ficam.</p>
      <h2>Draft da estrela</h2>
      <div class="card gold"><div class="v">⭐ ${pl(s.player)} <span class="tag">${s.role}</span></div>
        <p class="sub">${tl(s.from_team)} → ${tl(s.to_team)} (leva o bônus). Em troca, ${pl(s.swapped)} vai para ${tl(s.from_team)}.</p></div>
      <h2>Os 3 piores de cada função (liberados)</h2>` +
      table(['Função', 'Jogador', 'Time', 'Posição', 'KDA pond.'], dr.released.map(x =>
        `<tr><td>${x.role}</td><td class="l">${pl(x.player)}</td><td class="l">${tl(x.team)}</td>` +
        `<td>${x.rank_role}º</td><td>${kda(x.player)}</td></tr>`)) +
      `<h2>Escolhas dos free agents</h2>` +
      table(['#', 'Time', 'Função', 'Contratado', 'KDA carreira', 'Sinergia', 'Substitui'], dr.picks.map(x =>
        `<tr><td>${x.order}</td><td class="l">${tl(x.team)}</td><td>${x.role}</td>` +
        `<td class="l">${pl(x.player)}</td><td>${x.career_kda == null ? 'novato' : fmt(x.career_kda)}</td>` +
        `<td>${x.synergy != null ? Math.round(x.synergy * 100) + '%' : '–'}</td>` +
        `<td class="l">${pl(x.replaces)}</td></tr>`)) +
      `<h2>Evolução de nível (bônus acumulado)</h2><p class="sub">Só quem mudou de nível neste campeonato.</p>` +
      table(['Jogador', 'Função', 'Time', 'Antes', 'Depois'],
        [...dr.level_changes].sort((a, b) => b.after - a.after || b.before - a.before).map(x =>
          `<tr><td class="l">${pl(x.player)}</td><td>${App.reg[x.player].role}</td>` +
          `<td class="l">${own[x.player] ? tl(own[x.player]) : 'Free agent'}</td>` +
          `<td>${x.before}</td><td><b>${x.after}</b></td></tr>`));
  },

  hall(d) {
    const H = App.hall;
    if (!H || !H.champions.length) return '<h1>Hall da Fama</h1><p class="sub">Nenhum campeonato registrado ainda.</p>';
    window.setHall = r => { App.hallTab = r; $('#app').innerHTML = PAGES.hall(d); keepFocus(); };
    const cur = App.hallTab || 'ALL';
    const titles = {};
    H.champions.forEach(c => { titles[c.champion] = (titles[c.champion] || 0) + 1; });
    const list = H.players.filter(p => cur === 'ALL' || p.role === cur);
    const champs = [...H.champions].reverse();
    return `<h1>🏛️ Hall da Fama</h1><h2>Campeões</h2>` +
      table(['Temporada', 'Campeão', 'Vice', 'Melhor geral'], champs.map(c =>
        `<tr><td>${c.season}</td><td class="l">🏆 ${tl(c.champion)}</td><td class="l">${tl(c.runner_up)}</td>` +
        `<td class="l">${pl(c.best_overall)}</td></tr>`)) +
      `<h2>Melhores por função</h2>` +
      table(['Temporada', ...ROLES], champs.map(c =>
        `<tr><td>${c.season}</td>${ROLES.map(r => `<td>${pl(c.best_by_role[r])}</td>`).join('')}</tr>`)) +
      `<h2>Títulos por time</h2>` +
      table(['Time', 'Títulos'], Object.entries(titles).sort((a, b) => b[1] - a[1]).map(([t, n]) =>
        `<tr><td class="l">${tl(t)}</td><td>${n}</td></tr>`)) +
      `<h2>Ranking de carreira</h2><p class="sub">Índice = KDA ponderado (relativo à média da liga) + títulos, prêmios de melhor geral e de melhor da função. Desempate: pontos.</p>` +
      tabButtons(['ALL', ...ROLES], cur, 'setHall', 'Filtrar por função') +
      table(['#', 'Jogador', 'Função', 'Temp.', 'Jogos', 'Índice', 'KDA pond.', 'Títulos', 'Melhor geral', 'Melhor função'],
        list.map((p, i) => `<tr><td>${i + 1}</td><td class="l">${pl(p.id)}</td><td>${p.role}</td>` +
          `<td>${p.career.seasons}</td><td>${p.career.matches}</td><td><b>${Number(p.career.index).toFixed(1)}</b></td>` +
          `<td>${fmt(p.career.kda_pond != null ? p.career.kda_pond : p.career.kda_avg)}</td>` +
          `<td>${p.career.titles}</td><td>${p.awards_overall}</td><td>${p.awards_role}</td></tr>`));
  },
};

// Trechos carregados depois que a página aparece (dados sob demanda)
const AFTER = {
  async player() {
    const box = $('#career-table');
    if (!box) return;
    try {
      const res = await fetch(`data/players/${encodeURIComponent(qs('id'))}.jsonl`);
      if (!res.ok) throw new Error('histórico indisponível: ' + res.status);
      const rows = (await res.text()).split('\n').filter(Boolean).map(l => JSON.parse(l));
      box.innerHTML = table(['Temporada', 'Time', 'Rank geral', 'Rank função', 'KDA pond.', 'KDA médio', 'Pontos',
        'Assist.', 'Derrotas', 'Bônus', '<span class="sr-only">Título</span>'],
        rows.map(s => `<tr><td>${s.season}</td><td class="l">${tl(s.team_id)}</td>` +
          `<td>${s.rank_overall}º</td><td>${s.rank_role}º</td><td><b>${fmt(s.kda_pond != null ? s.kda_pond : s.kda_avg)}</b></td>` +
          `<td>${fmt(s.kda_avg)}</td>` +
          `<td>${s.points}</td><td>${s.assists}</td><td>${s.defeats}</td>` +
          `<td>${s.bonus ? '+' + s.bonus : '–'}</td>` +
          `<td>${s.champion ? '<span role="img" aria-label="Campeão">🏆</span>' : ''}</td></tr>`));
    } catch (e) {
      box.innerHTML = '<p class="lose" role="alert">Não foi possível carregar o histórico do jogador.</p>';
      console.error(e);
    }
  },
};

const App = {
  reg: {}, hallp: {}, hall: null, kh: {},

  async run() {
    const page = document.body.dataset.page;
    try {
      const seasons = await (await fetch('data/seasons.json')).json();
      let saved = '';
      try { saved = localStorage.getItem('season') || ''; } catch (e) {}
      this.season = seasons.includes(saved) ? saved : seasons[seasons.length - 1];
      const d = this.data = await (await fetch(`data/season-${this.season}.json`)).json();
      this.team = Object.fromEntries(d.teams.map(t => [t.id, t]));
      this.player = Object.fromEntries(d.players.map(p => [p.id, p]));
      this.match = Object.fromEntries(d.matches.map(m => [m.id, m]));
      this.reg = d.draft.players;
      // KDA de cada jogador, partida a partida, montado a partir das partidas do campeonato
      this.kh = {};
      d.matches.forEach(m => Object.entries(m.players).forEach(([pid, l]) =>
        (this.kh[pid] = this.kh[pid] || []).push({ match: m.id, kda: l.kda })));
      // o resumo do Hall só é necessário nas páginas Hall da Fama e Jogador
      if (page === 'hall' || page === 'player') {
        try {
          this.hall = await (await fetch('data/hall.json')).json();
          this.hallp = Object.fromEntries(this.hall.players.map(p => [p.id, p]));
        } catch (e) { this.hall = null; }
      }
      this.nav(page, seasons);
      $('#app').innerHTML = PAGES[page](d);
      if (AFTER[page]) AFTER[page](d);
    } catch (e) {
      $('#app').innerHTML = '<p class="lose" role="alert">Não foi possível carregar os dados. Rode o backend e ' +
        'abra o site via servidor HTTP (não direto por file://).</p>';
      console.error(e);
    }
  },

  nav(page, seasons) {
    const links = [['index', 'Início'], ['groups', 'Grupos'], ['knockout', 'Mata-mata'],
      ['teams', 'Times'], ['players', 'Jogadores'], ['draft', 'Draft'], ['hall', 'Hall da Fama']];
    const active = { team: 'teams', player: 'players' }[page] || page;
    const current = links.find(([p]) => p === active);
    if (current) document.title = `${current[1]} · MOBA Cup`;
    $('#top').innerHTML = `<span class="brand">🏆 MOBA CUP</span><nav aria-label="Principal">` +
      links.map(([p, t]) => `<a href="${p}.html" class="${p === active ? 'active' : ''}"` +
        `${p === active ? ' aria-current="page"' : ''}>${t}</a>`).join('') +
      `</nav><select id="season" aria-label="Campeonato">${[...seasons].reverse().map(s =>
        `<option ${s === this.season ? 'selected' : ''}>${s}</option>`).join('')}</select>`;
    $('#season').onchange = e => {
      try { localStorage.setItem('season', e.target.value); } catch (err) {}
      location.reload();
    };
  },
};

document.addEventListener('DOMContentLoaded', () => App.run());