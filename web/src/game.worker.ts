import { BrowserPolicy, call, loadEngine } from './runtime';
import { actionName, winds, type Observation, type Replay, type View, type Advice } from './types';

const policy = new BrowserPolicy();
let loaded = false;
let game: number | null = null;
let seed = 0;
let seat = 0;
let mode: View['mode'] = 'human';
let log: string[] = [];
let actions: Replay['actions'] = [];
let replay: Replay | null = null;
let generation = 0;
function actor(): number | null { return call({ op: 'actor', game }).actor; }
function observe(viewer: number): Observation { return call({ op: 'observe', game, seat: viewer }).observation; }
function view(): View {
  const observation = observe(seat);
  // Observation.drawn belongs to the current drawer. Do not publish another
  // player's draw to the UI; actor observations used by policies are unchanged.
  if (observation.phase.seat !== seat || !['discard', 'flower'].includes(observation.phase.kind)) observation.drawn = null;
  const currentActor = actor();
  if (currentActor !== seat) {
    observation.legal_actions = [];
    observation.legal_action_ids = [];
  }
  return { observation, actor: currentActor, seat, seed, mode, log: log.slice(-100), ended: currentActor === null,
    backend: 'WASM · 本机推理', modelId: policy.manifest.model_id,
    replayPosition: mode === 'replay' ? actions.length : undefined, replayLength: replay?.actions.length };
}
function apply(who: number, action: number) {
  const before = observe(who);
  const legal = before.legal_actions.find(a => a.id === action);
  if (!legal) throw new Error('这个动作已经不可用，请重新选择。');
  call({ op: 'step', game, seat: who, action_id: action });
  actions.push({ seat: who, action_id: action });
  const after = observe(seat);
  // Responses stay private until unified adjudication. Publish only the actual
  // resulting meld/outcome, never another player's pending pass/claim choice.
  if (before.phase.kind !== 'response') {
    const label = who !== seat && action >= 46 && action < 80 ? '暗杠（牌种不公开）' : actionName(legal, before.phase.tile);
    log.push(`${winds[who]}家 · ${label}`);
  }
  after.melds.forEach((melds, owner) => {
    if (melds.length > before.melds[owner].length && before.phase.kind === 'response') {
      const meld = melds.at(-1)!;
      log.push(`${winds[owner]}家 · ${({ chow: '吃牌', pung: '碰牌', kong: '明杠' })[meld.kind]}`);
    }
  });
  if (after.phase.kind === 'ended') {
    call({ op: 'validate', game });
    log.push(after.phase.outcome!.kind === 'win' ? `${winds[after.phase.outcome!.winner!]}家和牌，本盘结束` : '牌墙耗尽，本盘流局');
    if (mode === 'replay' && (actions.length !== replay!.actions.length || JSON.stringify(after.phase.outcome) !== JSON.stringify(replay!.outcome))) {
      throw new Error('回放结果与记录不一致，已停止。');
    }
  }
}
function validateReplay(value: Replay) {
  if (value.format !== 'mahjong-browser-replay-v1' || value.ruleset_id !== 'mcr-wmo2006-stage1' ||
      value.checkpoint_sha256 !== policy.manifest.files.checkpoint.sha256 || !Array.isArray(value.actions) ||
      value.actions.length > 2000 || value.actions.length < 1 || !value.outcome ||
      value.actions.some(a => !Number.isInteger(a.seat) || a.seat < 0 || a.seat > 3 || !Number.isInteger(a.action_id) || a.action_id < 0 || a.action_id >= 122)) {
    throw new Error('回放格式、模型或规则版本不兼容。');
  }
}
async function handle(type: string, data: any) {
  if (type === 'load') {
    if (!loaded) {
      await Promise.all([loadEngine(data.base), policy.load(data.base)]);
      loaded = true;
    }
    return { backend: 'WASM · 本机推理', modelId: policy.manifest.model_id };
  }
  if (!loaded) throw new Error('模型尚未加载完成。');
  if (type === 'start') {
    if (data.replay) validateReplay(data.replay);
    const requestedSeed = data.replay?.seed ?? data.seed;
    const requestedSeat = data.replay?.seat ?? data.seat;
    if (!Number.isInteger(requestedSeed) || requestedSeed < 0 || requestedSeed > 1_000_000_000 || !Number.isInteger(requestedSeat) || requestedSeat < 0 || requestedSeat > 3) throw new Error('牌局种子或座位不合法。');
    if (game !== null) call({ op: 'close', game });
    seed = requestedSeed; seat = requestedSeat; mode = data.replay ? 'replay' : data.mode;
    if (!['human', 'watch', 'replay'].includes(mode)) throw new Error('未知对局模式。');
    generation = data.generation;
    replay = data.replay ?? null;
    game = call({ op: 'new', seed, round_wind: 'F1' }).handle;
    actions = []; log = [`${mode === 'replay' ? '历史回放' : '新对局'} · 种子 ${seed}`];
    return view();
  }
  if (game === null) throw new Error('请先开始对局。');
  if (data.generation !== generation) throw new Error('请求来自上一盘，已忽略。');
  if (type === 'export') {
    const outcome = observe(seat).phase.outcome;
    if (!outcome) throw new Error('请在本盘结束后导出完整回放。');
    return { format: 'mahjong-browser-replay-v1', ruleset_id: 'mcr-wmo2006-stage1', seed, seat,
      checkpoint_sha256: policy.manifest.files.checkpoint.sha256, contains_hidden_actions: true,
      actions, outcome } satisfies Replay;
  }
  const currentActor = actor();
  if (currentActor === null) return view();
  if (type === 'act') {
    if (mode !== 'human' || currentActor !== seat || data.revision !== observe(seat).revision) throw new Error('不是你的当前决策，请等待牌桌更新。');
    apply(seat, data.action);
    return view();
  }
  if (type === 'hint') {
    if (currentActor !== seat || mode !== 'human') throw new Error('轮到你时才能查看当前局面的建议。');
    const observation = observe(seat);
    if (observation.phase.kind === 'discard' && !observation.legal_action_ids.includes(0)) {
      const result = await policy.infer(observation);
      return { kind: 'model', actions: result.actions, value: result.value } satisfies Advice;
    }
    return { kind: 'heuristic', actions: [{ id: call({ op: 'heuristic', game, seat, variant: 'qualified-tenpai' }).action_id, probability: 1 }] } satisfies Advice;
  }
  if (type === 'tick') {
    if (mode === 'human' && currentActor === seat) throw new Error('现在由你选择动作。');
    if (mode === 'replay') {
      const row = replay!.actions[actions.length];
      if (!row || row.seat !== currentActor) throw new Error('回放动作与当前牌局不一致。');
      apply(row.seat, row.action_id);
    } else {
      const observation = observe(currentActor);
      const chosen = observation.phase.kind === 'discard' && !observation.legal_action_ids.includes(0)
        ? (await policy.infer(observation)).action
        : call({ op: 'heuristic', game, seat: currentActor, variant: 'qualified-tenpai' }).action_id;
      apply(currentActor, chosen);
    }
    return view();
  }
  throw new Error('未知请求。');
}

// Serialize state changes even while inference yields to the event loop.
let queue = Promise.resolve();
self.onmessage = (event: MessageEvent) => {
  const { id, type, data } = event.data;
  queue = queue.then(async () => {
    try { self.postMessage({ id, result: await handle(type, data) }); }
    catch (error) { self.postMessage({ id, error: error instanceof Error ? error.message : String(error) }); }
  });
};
