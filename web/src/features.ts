import { codes, type Observation } from './types';

export const FEATURE_SIZE = 771;
export const ACTION_COUNT = 122;
export function encodeObservation(o: Observation): Float32Array {
  if (o.observation_version !== 1 || o.action_catalog_version !== 1 || o.action_count !== ACTION_COUNT) {
    throw new Error('观察或动作版本不兼容，无法使用此模型。');
  }
  const f = new Float32Array(FEATURE_SIZE);
  const index = (code: string) => {
    const i = codes.indexOf(code);
    if (i < 0) throw new Error(`未知牌种：${code}`);
    return i;
  };
  const flower = (code: string) => /^[a-h]$/.test(code);
  const clamp = (x: number, max: number) => Math.min(max, Math.max(0, x));
  for (let i = 0; i < 34; i++) {
    f[i] = o.hand[i] / 4;
    f[34 + i] = o.known_counts[i] / 4;
    f[68 + i] = clamp(1 - f[34 + i], 1);
  }
  if (o.drawn) f[flower(o.drawn) ? 144 + o.drawn.charCodeAt(0) - 97 : 102 + index(o.drawn)] = 1;
  for (const c of o.flowers) f[136 + c.charCodeAt(0) - 97] = 1;
  o.melds.forEach((melds, seat) => melds.forEach(m => {
    f[152 + seat * 6 + { chow: 0, pung: 2, kong: 4 }[m.kind] + Number(m.concealed)] += .25;
    if (m.tile) {
      const k = index(m.tile);
      if (m.kind === 'chow') for (let t = k - 1; t <= k + 1; t++) f[176 + seat * 34 + t] += .25;
      else f[176 + seat * 34 + k] += m.kind === 'pung' ? .75 : 1;
    }
  }));
  o.rivers.forEach((river, seat) => {
    const standard = river.filter(c => !flower(c));
    for (const c of standard) f[312 + seat * 34 + index(c)] += .25;
    if (standard.length) f[448 + seat * 34 + index(standard.at(-1)!)] = 1;
  });
  for (let i = 152; i < 448; i++) f[i] = clamp(f[i], 1);
  o.flower_counts.forEach((n, seat) => { f[584 + seat] = n / 8; });
  f[588] = o.wall_remaining / 136;
  f[589 + ['discard', 'flower', 'response', 'ended'].indexOf(o.phase.kind)] = 1;
  if (o.phase.kind === 'response') f[593 + index(o.phase.tile!)] = 1;
  f[627 + ['F1', 'F2', 'F3', 'F4'].indexOf(o.seat_wind)] = 1;
  f[631 + ['F1', 'F2', 'F3', 'F4'].indexOf(o.round_wind)] = 1;
  const hints = [o.discard_hints.shanten, o.discard_hints.ukeire, o.discard_hints.qualifying_waits, o.discard_hints.qualifying_value];
  hints.forEach((values, block) => {
    if (values.length !== 34) throw new Error('模型特征长度不匹配。');
    const divisor = [8, 136, 136, 20000][block];
    values.forEach((x, i) => { f[635 + block * 34 + i] = clamp(x, divisor) / divisor; });
  });
  if (f.some(x => !Number.isFinite(x))) throw new Error('特征包含无效数值。');
  return f;
}

export function guardedDiscards(o: Observation): number[] {
  const actions = o.legal_action_ids.filter(a => a >= 12 && a < 46);
  if (!actions.length) throw new Error('当前没有可用的弃牌动作。');
  const h = o.discard_hints;
  const rank = (a: number) => [h.shanten[a - 12], -h.qualifying_value[a - 12], -h.qualifying_waits[a - 12], -h.ukeire[a - 12]];
  const compare = (a: number[], b: number[]) => { for (let i = 0; i < 4; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };
  const best = actions.map(rank).sort(compare)[0];
  return actions.filter(a => compare(rank(a), best) === 0);
}
