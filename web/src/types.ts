export type LegalAction = { id: number; key: string };
export type Meld = { kind: 'chow' | 'pung' | 'kong'; tile: string | null; concealed: boolean; claimed_from: number | null };
export type Outcome = { kind: 'win' | 'exhaustive-draw'; winner?: number; discarder?: number | null;
  winning_tile?: string;
  total_fan?: number; qualifying_fan?: number; flower_fan?: number; deltas?: number[];
  awards?: { fan: string; points: number; count: number }[] };
export type Observation = {
  observation_version: number; action_catalog_version: number; action_count: number;
  seat: number; seat_wind: string; round_wind: string; hand: number[]; drawn: string | null;
  flowers: string[]; flower_counts: number[]; melds: Meld[][]; rivers: string[][]; known_counts: number[];
  wall_remaining: number; revision: number;
  phase: { kind: 'discard' | 'flower' | 'response' | 'ended'; seat?: number; discarder?: number; tile?: string; outcome?: Outcome };
  discard_hints: { shanten: number[]; ukeire: number[]; qualifying_waits: number[]; qualifying_value: number[] };
  legal_action_ids: number[]; legal_actions: LegalAction[];
};
export type Replay = { format: 'mahjong-browser-replay-v1'; ruleset_id: string; seed: number; seat: number;
  checkpoint_sha256: string; contains_hidden_actions: true;
  actions: { seat: number; action_id: number }[]; outcome: Outcome };
export type View = { observation: Observation; actor: number | null; seat: number; seed: number;
  mode: 'human' | 'watch' | 'replay'; log: string[]; ended: boolean; backend: string; modelId: string;
  table: { flowers: string[]; melds: (Meld & { claimed_tile?: string })[]; hand?: number[] }[];
  replayPosition?: number; replayLength?: number };
export type Advice = { kind: 'model' | 'heuristic'; actions: { id: number; probability: number }[]; value?: number };
export const codes = [...['W', 'T', 'B'].flatMap(s => Array.from({ length: 9 }, (_, i) => `${s}${i + 1}`)),
  'F1', 'F2', 'F3', 'F4', 'J3', 'J2', 'J1'];
export const winds = ['东', '南', '西', '北'];
export const rankNames = ['一', '二', '三', '四', '五', '六', '七', '八', '九'];
export function tileName(code: string): string {
  if (/^[WTB][1-9]$/.test(code)) return rankNames[Number(code[1]) - 1] + ({ W: '万', T: '条', B: '筒' }[code[0]] ?? '');
  const other: Record<string, string> = { F1: '东', F2: '南', F3: '西', F4: '北', J3: '中', J2: '发', J1: '白',
    a: '春', b: '夏', c: '秋', d: '冬', e: '梅', f: '兰', g: '竹', h: '菊' };
  return other[code] ?? '暗牌';
}
export function actionName(action: LegalAction, responseTile?: string): string {
  const names: Record<string, string> = { hu: '胡牌', pass: '过', 'expose-flower': '补花', pung: '碰', kong: '明杠' };
  if (names[action.key]) return names[action.key];
  for (const [prefix, label] of [['discard-flower-', '弃花'], ['concealed-kong-', '暗杠'], ['added-kong-', '加杠'], ['discard-', '打出']]) {
    if (action.key.startsWith(prefix)) return label + tileName(action.key.slice(prefix.length));
  }
  if (action.key.startsWith('chow-')) {
    const rank = Number(action.key.slice(5));
    return `吃 ${[rank, rank + 1, rank + 2].map(r => tileName(`${responseTile?.[0] ?? 'W'}${r}`)).join('·')}`;
  }
  throw new Error('未知动作目录');
}
