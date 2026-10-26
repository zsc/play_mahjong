import { codes, rankNames, tileName, winds, type View } from './types';

const escape = (s: unknown) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
function tile(code: string, options: { small?: boolean; action?: number; selected?: boolean; drawn?: boolean; winning?: boolean } = {}) {
  const suit = /^[WTB]/.test(code) ? code[0] : code.startsWith('J') ? code : 'honor';
  const content = /^[WTB][1-9]$/.test(code) ? `<b>${rankNames[Number(code[1]) - 1]}</b><span>${({ W: '萬', T: '条', B: '筒' })[code[0]]}</span>` : `<b class="single">${tileName(code)}</b>`;
  const classes = `tile suit-${suit}${options.small ? ' small' : ''}${options.selected ? ' selected' : ''}${options.drawn ? ' drawn' : ''}${options.winning ? ' winning-tile' : ''}`;
  const label = `${options.winning ? '和牌张：' : ''}${tileName(code)}`;
  return options.action !== undefined ? `<button class="${classes}" data-discard="${options.action}" data-tile="${code}" aria-label="选择${escape(label)}" aria-pressed="${!!options.selected}">${content}</button>` : `<span class="${classes}" data-tile="${code}" aria-label="${escape(label)}">${content}</span>`;
}

export function meldHtml(state: View, owner: number): string {
  return state.table[owner].melds.map(m => {
    // Concealed kongs stay face down on the table until settlement, even for the owner.
    if (m.concealed && !state.ended) return `<span class="meld concealed" aria-label="暗杠，四张背面"><i class="tile-back tiny"></i><i class="tile-back tiny"></i><i class="tile-back tiny"></i><i class="tile-back tiny"></i><small>暗杠</small></span>`;
    const k = codes.indexOf(m.tile!);
    const tiles: string[] = m.kind === 'chow' ? codes.slice(k - 1, k + 2) : Array(m.kind === 'kong' ? 4 : 3).fill(m.tile);
    let claimedIndex = -1;
    if (m.claimed_from !== null && m.claimed_tile) {
      const index = tiles.indexOf(m.claimed_tile);
      if (index >= 0) {
        tiles.splice(index, 1);
        const relative = (m.claimed_from - owner + 4) % 4;
        claimedIndex = relative === 3 ? 0 : relative === 2 ? 1 : tiles.length;
        tiles.splice(claimedIndex, 0, m.claimed_tile);
      }
    }
    const name = m.concealed ? '暗杠' : m.kind === 'chow' ? '吃' : m.kind === 'pung' ? '碰' : '明杠';
    const source = m.claimed_from !== null ? `，取自${winds[m.claimed_from]}家` : '';
    return `<span class="meld${m.concealed ? ' concealed revealed' : ''}" aria-label="${name}${source}">${tiles.map((c, i) => i === claimedIndex ? `<span class="claimed-tile" aria-label="取自${winds[m.claimed_from!]}家">${tile(c, { small: true })}</span>` : tile(c, { small: true })).join('')}<small>${name}</small></span>`;
  }).join('');
}

function handHtml(state: View, owner: number, enabled: boolean, selected: number | null): string {
  const o = state.observation;
  const counts = state.ended ? state.table[owner].hand! : owner === state.seat ? o.hand : null;
  if (!counts) {
    const extra = ['discard', 'flower'].includes(o.phase.kind) && o.phase.seat === owner ? 1 : 0;
    const n = 13 - o.melds[owner].length * 3 + extra;
    return `<div class="concealed-hand" aria-label="${winds[owner]}家暗手，牌种不公开">${Array.from({ length: n }, () => '<i class="tile-back"></i>').join('')}</div>`;
  }
  const hand = counts.flatMap((n, k) => Array(n).fill(codes[k]) as string[]);
  const winner = state.ended && o.phase.outcome?.winner === owner;
  const separate = winner ? o.phase.outcome!.winning_tile : !state.ended && owner === state.seat ? o.drawn : null;
  const index = separate ? hand.lastIndexOf(separate) : -1;
  if (index >= 0) hand.splice(index, 1);
  const face = (c: string, drawn = false) => {
    const id = 12 + codes.indexOf(c);
    return tile(c, { action: enabled && codes.includes(c) && owner === state.seat && o.legal_action_ids.includes(id) ? id : undefined,
      selected: selected === id && owner === state.seat, drawn, winning: !!winner && drawn });
  };
  return `<div class="${owner === state.seat ? 'hand' : 'revealed-hand'}${state.ended ? ' settled-hand' : ''}" aria-label="${owner === state.seat ? '你的手牌' : winds[owner] + '家亮牌'}">${hand.map(c => face(c)).join('')}${index >= 0 ? face(separate!, true) : ''}${separate && /^[a-h]$/.test(separate) ? face(separate, true) : ''}</div>`;
}

export function renderTable(state: View, enabled: boolean, selected: number | null): string {
  const o = state.observation;
  const positions = ['south', 'east', 'north', 'west'];
  const seats = positions.map((position, relative) => {
    const owner = (state.seat + relative) % 4;
    const winner = o.phase.outcome?.winner === owner;
    const name = owner === state.seat && state.mode === 'human' ? '你' : 'AI';
    return `<section class="table-seat seat-${position}${winner ? ' winner' : ''}${state.actor === owner && !state.ended ? ' current' : ''}" data-seat="${owner}" aria-label="${winds[owner]}家${winner ? '，和牌' : ''}">
      <div class="exposed-area"><div class="public-melds" aria-label="${winds[owner]}家副露">${meldHtml(state, owner)}</div><div class="flower-tiles" aria-label="${winds[owner]}家花牌">${state.table[owner].flowers.map(c => tile(c, { small: true })).join('')}</div></div>
      ${handHtml(state, owner, enabled, selected)}
      <div class="player-label"><span class="wind-icon">${winds[owner]}</span><b>${name} · ${winds[owner]}家</b>${winner ? '<strong class="winner-badge">和牌</strong>' : ''}${state.actor === owner && !state.ended ? '<span class="thinking-dot"></span>' : ''}</div></section>`;
  }).join('');
  const rivers = positions.map((position, relative) => {
    const owner = (state.seat + relative) % 4;
    return `<div class="river-position river-${position}"><section class="river${o.rivers[owner].length > 24 ? ' long-river' : ''}" data-seat="${owner}" aria-label="${winds[owner]}家牌河"><div class="river-tiles">${o.rivers[owner].map(c => tile(c, { small: true })).join('')}</div></section></div>`;
  }).join('');
  let center = `<span class="round-label">东风圈</span><b class="center-wind">${winds[state.seat]}</b><span class="remaining">余牌 <strong>${o.wall_remaining}</strong></span>`;
  if (o.phase.kind === 'response') center = `<span class="round-label">等待响应</span><b class="response-name">${tileName(o.phase.tile!)}</b><span class="remaining">${winds[o.phase.discarder!]}家出牌</span>`;
  if (state.ended) center = `<span class="round-label">已结算 · 亮牌</span><b class="center-wind">${o.phase.outcome!.kind === 'win' ? '和' : '流'}</b><span class="remaining">${o.phase.outcome!.kind === 'win' ? winds[o.phase.outcome!.winner!] + '家和牌' : '荒牌流局'}</span>`;
  return `${seats}${rivers}<div class="table-center">${center}</div>`;
}

// A readable, viewer-facing copy for checking the winner on small screens.
export function winningHandSummary(state: View): string {
  const winner = state.observation.phase.outcome?.winner;
  if (!state.ended || winner === undefined) return '';
  return `<div class="winning-summary"><span>和牌手牌 <small>金色牌为和牌张</small></span><div class="winning-summary-tiles">${handHtml(state, winner, false, null)}<div class="public-melds">${meldHtml(state, winner)}</div></div></div>`;
}
