import './style.css';
import { actionName, codes, rankNames, tileName, winds, type Advice, type View } from './types';

const app = document.querySelector<HTMLDivElement>('#app')!;
const escape = (s: unknown) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
app.innerHTML = `
  <header class="site-header"><a class="brand" href="#play"><span class="brand-tile">中</span><span>一桌麻将<small>MAHJONG · PLAY LAB</small></span></a>
    <nav aria-label="主导航"><a href="#play" class="active">开始对局</a><a href="#training">训练记录</a><a href="#about">关于人测</a></nav>
    <span class="local-badge"><i></i>全程在本机运行</span></header>
  <main>
    <section id="play-page"><div class="page-heading"><div><p class="eyebrow">HUMAN × AI</p><h1>坐下来，打一盘。</h1><p>和真实训练的 AI 过招。吃、碰、杠、胡，由你选择。</p></div><span class="version-tag">人测候选 01 <span>PPO40 + 启发式保护</span></span></div>
      <div id="error" role="alert" hidden></div>
      <div class="play-layout"><div class="board-wrap"><div class="board-topline"><span id="game-caption">东风圈 · 单盘人测</span><span id="engine-status" role="status">正在加载规则与模型…</span></div>
        <div id="board" class="board"><div class="loading-table"><span class="loading-tile">發</span><h2>正在备牌</h2><p>首次载入需要下载本地运行的模型与规则。</p></div></div>
        <div class="decision-bar" id="decision-bar"><span>牌桌准备中…</span></div>
        <p class="table-note">阶段一规则：完整番种排斥、补牌来源链与整场流程仍在完善。<a href="#about">了解本次人测范围 ↗</a></p>
      </div><aside>
        <section class="panel settings"><div class="panel-heading"><h2>这盘怎么打</h2><span>01 / 对局设置</span></div>
          <div class="segmented"><button id="human-mode" class="chosen" type="button">我来打</button><button id="watch-mode" type="button">AI 观战</button></div>
          <div class="form-row"><label>我的座位<select id="seat"><option value="0">东家</option><option value="1">南家</option><option value="2">西家</option><option value="3">北家</option></select></label><label>牌局种子<input id="seed" inputmode="numeric" type="number" min="0" max="1000000000" value="16000001" /></label></div>
          <button id="start" class="primary full" disabled>加载中…</button>
          <div class="minor-buttons"><button id="pause" disabled>暂停</button><button id="download" disabled>保存回放</button><button id="import">打开回放</button></div>
          <input id="replay-file" type="file" accept=".json,application/json" hidden />
        </section>
        <section class="panel"><div class="panel-heading"><h2>想看看 AI 的想法？</h2><span>02 / 决策参考</span></div><p class="muted">只分析你此刻可见的牌。建议不会限制你的选择。</p><button id="hint" class="outline full" disabled>查看当前建议</button><div id="advice"></div></section>
        <section class="panel log-panel"><div class="panel-heading"><h2>牌桌动态</h2><span id="step-count">等待开局</span></div><ol id="events"><li class="muted">准备就绪后会自动开局。</li></ol></section>
      </aside></div>
    </section>
    <section id="training-page" hidden><div class="page-heading"><div><p class="eyebrow">REAL RUNS, REAL RESULTS</p><h1>每一分，都来自真实对局。</h1><p>冻结模型、独立种子、正式单盘结算。训练运行成功不等于棋力提升。</p></div></div><div id="training-content" class="records-grid">正在读取记录…</div></section>
    <section id="about-page" hidden><div class="page-heading"><div><p class="eyebrow">BEFORE YOU PLAY</p><h1>这次我们在测什么</h1></div></div><div class="about-card panel"><h2>真实模型，阶段一规则。</h2><p>你的三个对手使用 PPO40 神经网络选择标准弃牌，并由 teacher-optimal 保护筛选候选。吃碰杠胡与花牌操作由 qualified-tenpai 启发式处理。真人始终拥有当前规则引擎给出的全部合法选择。</p><p>这是 WMO 2006 MCR 的阶段一实现，不是完整国标麻将成品。完整番种排斥、连续补牌来源链、16 手整场和部分规则边界尚未验收。页面提供单盘对局，不能将当前结果当作完整 MCR 整场棋力。</p><h2>模型达到人测门槛，不代表最强。</h2><p>候选通过了预先规定的 6,400 局独立验收。最新同墙四座测试中，对三个 qualified 对手平均 +0.240 分/盘，95% 置信区间 [0.052, 0.428]。这是带启发式保护的复合策略成绩。后续 SOFY 209 万盘训练尚未证明新模型更强，因此这里仍使用原已验收的 PPO40。全动作无保护模型仍属实验，未接入本页。</p><h2>如何操作</h2><p>点选手牌，再点击「打出」。遇到响应窗口，选择吃、碰、杠、胡或过。所有操作由同一 OCaml 规则核心校验。建议中的百分比是动作选择概率，不是胜率。</p><h2>记录与隐私</h2><p>规则和 ONNX 推理都在浏览器 Worker 中执行，不需要持续在线的推理服务器。对手暗手与尚未裁定的响应不会展示。结束后可下载回放，回放文件包含整盘动作，加载时会明确标记「历史回放」。关闭网页会停止当前对局。</p><p>建议使用近期的 Chrome、Edge、Safari 或 Firefox。无需 WebGPU；默认单线程 WASM 推理。若资源下载失败会显示错误，不会悄悄换成启发式或随机模型。</p></div></section>
  </main><footer><span>一桌麻将 <span class="footer-dot">/</span> 真实训练 · 本机推理</span><span>规则 mcr-wmo2006-stage1 <span class="footer-dot">·</span> 不含浏览器现场训练 <span class="footer-dot">·</span> <a href="./THIRD_PARTY_NOTICES.txt" target="_blank" rel="noopener">第三方许可</a></span></footer>`;

let worker = new Worker(new URL('./game.worker.ts', import.meta.url), { type: 'module' });
const pending = new Map<number, { resolve: (x: any) => void; reject: (e: Error) => void }>();
let requestId = 0;
let state: View | null = null;
let selected: number | null = null;
let generation = 0;
let busy = false;
let paused = false;
let loaded = false;
let chosenMode: 'human' | 'watch' = 'human';
let timer: ReturnType<typeof setTimeout> | undefined;
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
function error(message: string) { $('error').hidden = false; $('error').textContent = message; }
function clearError() { $('error').hidden = true; }
worker.onmessage = event => {
  const item = pending.get(event.data.id);
  if (!item) return;
  pending.delete(event.data.id);
  if (event.data.error) item.reject(new Error(event.data.error)); else item.resolve(event.data.result);
};
worker.onerror = event => {
  error(`浏览器运行环境初始化失败：${event.message}。请使用近期浏览器后重试。`);
  for (const item of pending.values()) item.reject(new Error('规则或模型 Worker 运行失败。'));
  pending.clear();
};
function rpc<T = any>(type: string, data: Record<string, unknown> = {}): Promise<T> {
  return new Promise((resolve, reject) => { const id = ++requestId; pending.set(id, { resolve, reject }); worker.postMessage({ id, type, data: { generation, ...data } }); });
}
function tile(code: string, options: { small?: boolean; action?: number; selected?: boolean; drawn?: boolean } = {}) {
  const suit = /^[WTB]/.test(code) ? code[0] : code.startsWith('J') ? code : 'honor';
  const content = /^[WTB][1-9]$/.test(code) ? `<b>${rankNames[Number(code[1]) - 1]}</b><span>${({ W: '萬', T: '条', B: '筒' })[code[0]]}</span>` : `<b class="single">${tileName(code)}</b>`;
  const classes = `tile suit-${suit}${options.small ? ' small' : ''}${options.selected ? ' selected' : ''}${options.drawn ? ' drawn' : ''}`;
  return options.action !== undefined ? `<button class="${classes}" data-discard="${options.action}" aria-label="选择${escape(tileName(code))}" aria-pressed="${!!options.selected}">${content}</button>` : `<span class="${classes}" aria-label="${escape(tileName(code))}">${content}</span>`;
}
function publicMelds(owner: number) {
  return state!.observation.melds[owner].map(m => {
    if (!m.tile) return '<span class="meld concealed"><i class="tile-back tiny"></i><i class="tile-back tiny"></i><i class="tile-back tiny"></i><i class="tile-back tiny"></i><small>暗杠</small></span>';
    const k = codes.indexOf(m.tile);
    const tiles = m.kind === 'chow' ? codes.slice(k - 1, k + 2) : Array(m.kind === 'kong' ? 4 : 3).fill(m.tile);
    return `<span class="meld">${tiles.map(c => tile(c, { small: true })).join('')}${m.concealed ? '<small>暗杠</small>' : ''}</span>`;
  }).join('');
}
function player(owner: number, position: string) {
  const s = state!;
  const n = Math.max(0, 13 - s.observation.melds[owner].length * 3);
  return `<section class="opponent ${position}${s.actor === owner ? ' current' : ''}" aria-label="${winds[owner]}家 AI"><div class="player-label"><span class="wind-icon">${winds[owner]}</span><div><b>AI ${winds[owner]}家</b><small>已补花 ${s.observation.flower_counts[owner]}</small></div>${s.actor === owner && !s.ended ? '<span class="thinking-dot"></span>' : ''}</div><div class="backs" aria-label="对手暗手，不公开牌种">${Array.from({ length: n }, () => '<i class="tile-back"></i>').join('')}</div><div class="public-melds">${publicMelds(owner)}</div></section>`;
}
function render() {
  if (!state) return;
  const o = state.observation;
  const yourTurn = state.mode === 'human' && state.actor === state.seat && !state.ended;
  const enabled = yourTurn && !busy;
  const hand = o.hand.flatMap((n, k) => Array(n).fill(codes[k]) as string[]);
  const drawnIndex = o.drawn ? hand.lastIndexOf(o.drawn) : -1;
  if (drawnIndex >= 0) hand.splice(drawnIndex, 1);
  const handHtml = hand.map(c => { const id = 12 + codes.indexOf(c); return tile(c, { action: enabled && o.legal_action_ids.includes(id) ? id : undefined, selected: selected === id }); }).join('')
    + (drawnIndex >= 0 ? tile(o.drawn!, { action: enabled && o.legal_action_ids.includes(12 + codes.indexOf(o.drawn!)) ? 12 + codes.indexOf(o.drawn!) : undefined, selected: selected === 12 + codes.indexOf(o.drawn!), drawn: true }) : '')
    + (o.drawn && /^[a-h]$/.test(o.drawn) ? tile(o.drawn, { drawn: true }) : '');
  const riverOrder = [(state.seat + 2) % 4, (state.seat + 1) % 4, (state.seat + 3) % 4, state.seat];
  const rivers = riverOrder.map(owner => `<section class="river" aria-label="${winds[owner]}家牌河"><div class="river-label">${winds[owner]}家<span>${o.rivers[owner].length} 张</span></div><div class="river-tiles">${o.rivers[owner].map(c => tile(c, { small: true })).join('') || '<span class="river-empty">尚未出牌</span>'}</div></section>`).join('');
  let center = `<span class="round-label">东风圈</span><b class="center-wind">${winds[state.seat]}</b><span class="remaining">余牌 <strong>${o.wall_remaining}</strong></span>`;
  if (o.phase.kind === 'response') center = `<span class="round-label">等待响应</span>${tile(o.phase.tile!, { small: true })}<span class="remaining">${winds[o.phase.discarder!]}家</span>`;
  if (state.ended) center = `<span class="round-label">本盘结束</span><b class="center-wind">${o.phase.outcome!.kind === 'win' ? '和' : '流'}</b><span class="remaining">${o.phase.outcome!.kind === 'win' ? winds[o.phase.outcome!.winner!] + '家和牌' : '荒牌流局'}</span>`;
  $('board').innerHTML = `${player((state.seat + 2) % 4, 'north')}${player((state.seat + 3) % 4, 'west')}${player((state.seat + 1) % 4, 'east')}<div class="river-grid">${rivers}</div><div class="table-center">${center}</div><section class="human-player${yourTurn ? ' current' : ''}"><div class="human-info"><span class="wind-icon">${winds[state.seat]}</span><b>${state.mode === 'human' ? '你' : '观测视角'} · ${winds[state.seat]}家</b><span>${state.mode === 'human' ? '真人玩家' : state.mode === 'watch' ? 'AI 自动对局' : '历史回放'}</span><div class="flowers">花牌 ${o.flowers.map(tileName).join(' ') || '—'}</div></div><div class="own-melds">${publicMelds(state.seat)}</div><div class="hand" aria-label="你的手牌">${handHtml}</div></section>`;
  $('game-caption').textContent = `${state.mode === 'human' ? '人机对战' : state.mode === 'watch' ? 'AI 观战' : '历史回放'} · 种子 ${state.seed}`;
  $('engine-status').textContent = state.backend;
  $('step-count').textContent = `第 ${o.revision} 步`;
  $('events').innerHTML = state.log.slice(-8).reverse().map((line, i) => `<li class="${i === 0 ? 'latest' : ''}">${escape(line)}</li>`).join('');
  $('pause').textContent = paused ? '继续' : '暂停';
  ($('pause') as HTMLButtonElement).disabled = state.ended;
  ($('download') as HTMLButtonElement).disabled = !state.ended;
  ($('hint') as HTMLButtonElement).disabled = !enabled;
  ($('start') as HTMLButtonElement).disabled = busy;
  if (state.ended) {
    const outcome = o.phase.outcome!;
    const scores = (outcome.deltas ?? [0, 0, 0, 0]).map((score, i) => `<span>${winds[i]}家 <b class="${score >= 0 ? 'positive' : 'negative'}">${score > 0 ? '+' : ''}${score}</b></span>`).join('');
    $('decision-bar').innerHTML = `<div class="result"><strong>${outcome.kind === 'win' ? `${winds[outcome.winner!]}家和牌 · ${outcome.total_fan} 番` : '本盘流局'}</strong><div class="score-row">${scores}</div>${outcome.awards?.length ? `<details><summary>查看计番</summary><p>${outcome.awards.map(a => `${escape(a.fan)} ${a.points}×${a.count}`).join(' · ')}</p></details>` : ''}</div>`;
  } else if (yourTurn) {
    const discards = o.legal_actions.filter(a => a.id >= 12 && a.id < 46);
    const other = o.legal_actions.filter(a => a.id < 12 || a.id >= 46);
    $('decision-bar').innerHTML = `<div class="turn-copy"><i></i><span>${o.phase.kind === 'response' ? '请选择响应动作' : o.phase.kind === 'flower' ? '请处理摸到的花牌' : selected === null ? '轮到你了，点选一张手牌' : '已选 ' + tileName(codes[selected - 12])}</span></div><div class="action-buttons">${discards.length ? `<button class="primary" id="discard" ${selected === null || busy ? 'disabled' : ''}>${selected === null ? '选择手牌' : '打出' + tileName(codes[selected - 12])}</button>` : ''}${other.map(a => `<button class="${a.id === 0 ? 'win-button' : 'outline'}" data-action="${a.id}" ${busy ? 'disabled' : ''}>${escape(actionName(a, o.phase.tile))}</button>`).join('')}</div>`;
  } else $('decision-bar').innerHTML = `<div class="turn-copy"><i class="${paused ? 'off' : ''}"></i><span>${paused ? '已暂停' : `${winds[state.actor!]}家正在${state.mode === 'replay' ? '回放' : '思考'}…`}</span></div><span class="muted">${state.mode === 'replay' ? `${state.replayPosition} / ${state.replayLength} 步` : '对手的暗手保持隐藏'}</span>`;
}
function schedule() {
  clearTimeout(timer);
  if (!state || state.ended || busy || paused || (state.mode === 'human' && state.actor === state.seat)) return;
  const g = generation;
  timer = setTimeout(async () => {
    if (g !== generation) return;
    busy = true; render();
    try { const next = await rpc<View>('tick'); if (g === generation) { state = next; selected = null; } }
    catch (e) { if (g === generation) { paused = true; error((e as Error).message); } }
    finally { if (g === generation) { busy = false; render(); schedule(); } }
  }, state.mode === 'human' ? 240 : 180);
}
async function start(replay?: unknown) {
  if (!loaded) return;
  clearTimeout(timer); generation++; busy = true; paused = false; selected = null; clearError(); $('advice').innerHTML = '';
  try { state = await rpc<View>('start', { generation, replay, seed: Number(($('seed') as HTMLInputElement).value), seat: Number(($('seat') as HTMLSelectElement).value), mode: chosenMode }); }
  catch (e) { paused = true; error((e as Error).message); }
  finally { busy = false; render(); schedule(); }
}
async function act(id: number) {
  if (busy || !state) return;
  busy = true; clearError(); render();
  try { state = await rpc<View>('act', { action: id, revision: state.observation.revision }); selected = null; $('advice').innerHTML = ''; }
  catch (e) { error((e as Error).message); }
  finally { busy = false; render(); schedule(); }
}
$('board').addEventListener('click', event => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>('[data-discard]');
  if (button && !busy) { selected = Number(button.dataset.discard); render(); $('discard')?.focus(); }
});
$('decision-bar').addEventListener('click', event => {
  const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button');
  if (!button || button.disabled) return;
  if (button.id === 'discard' && selected !== null) void act(selected);
  else if (button.dataset.action !== undefined) void act(Number(button.dataset.action));
});
$('start').onclick = () => { void start(); };
$('human-mode').onclick = () => { chosenMode = 'human'; $('human-mode').classList.add('chosen'); $('watch-mode').classList.remove('chosen'); };
$('watch-mode').onclick = () => { chosenMode = 'watch'; $('watch-mode').classList.add('chosen'); $('human-mode').classList.remove('chosen'); };
$('pause').onclick = () => { paused = !paused; render(); schedule(); };
$('hint').onclick = async () => {
  if (busy || !state) return;
  busy = true; render();
  try {
    const advice = await rpc<Advice>('hint');
    $('advice').innerHTML = `<p class="advice-caption">${advice.kind === 'model' ? '模型建议 · 受保护的动作选择概率' : '启发式建议 · 非网络决策'}</p>${advice.actions.slice(0, 4).map(a => `<div class="advice-action"><span>${escape(actionName(state!.observation.legal_actions.find(x => x.id === a.id)!, state!.observation.phase.tile))}</span><strong>${(a.probability * 100).toFixed(1)}%</strong><i style="width:${a.probability * 100}%"></i></div>`).join('')}${advice.value !== undefined ? `<p class="muted">预期净得分 ${(advice.value * 64).toFixed(1)} · 不是胜率</p>` : ''}`;
  } catch (e) { error((e as Error).message); }
  finally { busy = false; render(); schedule(); }
};
$('download').onclick = async () => {
  try { const data = await rpc('export'); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = `mahjong-${state!.seed}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  catch (e) { error((e as Error).message); }
};
$('import').onclick = () => ($('replay-file') as HTMLInputElement).click();
$('replay-file').onchange = async () => {
  const file = ($('replay-file') as HTMLInputElement).files?.[0];
  if (!file) return;
  try { if (file.size > 2_000_000) throw new Error('回放文件过大。'); await start(JSON.parse(await file.text())); }
  catch (e) { error((e as Error).message); }
  ($('replay-file') as HTMLInputElement).value = '';
};
function navigate() {
  const page = ['play', 'training', 'about'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'play';
  for (const name of ['play', 'training', 'about']) $(`${name}-page`).hidden = name !== page;
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#${page}`));
  if (page !== 'play') { paused = true; clearTimeout(timer); render(); }
}
window.addEventListener('hashchange', navigate); navigate();
const base = new URL(import.meta.env.BASE_URL, document.baseURI).href;
function arenaRecord(data: any): string {
  const names: Record<string, string> = { 'old-guard': '网页模型 + 保护', 'new-guard': '新 PPO + 保护', 'old-raw': '网页模型 · 无弃牌保护', 'new-raw': '新 PPO · 无弃牌保护' };
  const diff = data.paired_vs_old_guard.qualified['new-guard'];
  const interval = (values: number[]) => `[${values.map(v => v.toFixed(3)).join(', ')}]`;
  return `<section class="panel record-wide"><h2>棋力实测 · 同墙四座</h2>
    <p>每个策略 32,000 盘，对战三个冻结 qualified 教师。每副牌墙轮换四个座位，置信区间按 8,000 副牌墙分组。</p>
    <table><thead><tr><th>策略</th><th>净分 / 盘</th><th>95% CI</th></tr></thead><tbody>${Object.entries(names).map(([key, name]) => {
      const score = data.summaries[`${key}-vs-qualified`].score;
      return `<tr><td>${name}</td><td>${score.mean.toFixed(3)}</td><td>${interval(score.ci95)}</td></tr>`;
    }).join('')}</tbody></table>
    <p>主比较：新旧带保护模型的配对差为 ${diff.mean.toFixed(3)}，95% CI ${interval(diff.ci95)}，尚未证明新模型更强。网页继续使用旧模型。</p>
    <p>当前成绩依赖启发式保护。无弃牌保护的策略仍由启发式处理其他动作，不能称为全动作纯网络。加上闭门教师与旧模型直接对战，本轮共 184,000 盘。</p>
    <p class="muted">这是 stage1 规则内的相对成绩，不是完整 MCR 的 Elo 或段位。人测建议连续保存 20–50 盘终局回放，用于定位具体弱点。</p></section>`;
}
function sofyRecord(data: any): string {
  const colors = ['#246b54', '#3d6b9c', '#b46e38', '#946c98'];
  const rows = data.branches.map((branch: any) => ({
    branch: branch.branch,
    points: branch.evaluations.filter((r: any) => /^u\d+-teacher-optimal$/.test(r.name)),
  }));
  const curves = rows.map((row: any) => {
    const points = row.points.map((p: any) => `${35 + (Number(p.name.slice(1, 5)) - 32) / 96 * 630},${195 - p.score / 1.6 * 150}`).join(' ');
    return `<polyline points="${points}" fill="none" stroke="${colors[row.branch]}" stroke-width="2.5"/>`;
  }).join('');
  return `<section class="panel record-wide"><h2>SOFY 大规模 PPO · ${Number(data.games).toLocaleString()} 局</h2>
    <p>四条分支各训练 128 次更新。下图为同一 3,200 局开发集上的冻结快照均分（网络 + teacher-optimal 保护），用于选择模型，不能代替独立验收。</p>
    <svg class="training-chart" viewBox="0 0 700 230" role="img" aria-label="四条 PPO 分支固定开发集的平均净得分">
      <line x1="35" x2="665" y1="195" y2="195" stroke="#d3ded5"/>${curves}
      <text x="5" y="50">1.6</text><text x="5" y="195">0</text><text x="35" y="220">更新 32</text><text x="600" y="220">更新 128</text></svg>
    <p>${rows.map((r: any) => `<span style="color:${colors[r.branch]};margin-right:25px">● 分支 b${r.branch}</span>`).join('')}</p>
    <p>开发集选定 ${escape(data.selected)}。新的 6,400 局独立验收：新候选 ${data.new_score.toFixed(3)} 分/盘，旧候选 ${data.old_score.toFixed(3)}，qualified 教师 ${data.qualified_score.toFixed(3)}。</p>
    <p>相对旧候选 ${data.comparisons.previous.difference >= 0 ? '+' : ''}${data.comparisons.previous.difference.toFixed(3)}，95% CI [${data.comparisons.previous.ci95.map((n: number) => n.toFixed(3)).join(', ')}]。
    通过非劣门槛，但未证明更强；牌桌继续使用原验收模型。</p></section>`;
}
async function load() {
  try { await rpc('load', { base }); loaded = true; ($('start') as HTMLButtonElement).disabled = false; $('start').textContent = '开始新一盘'; await start(); }
  catch (e) { error(`加载失败：${(e as Error).message}`); $('engine-status').textContent = '加载失败'; $('start').textContent = '重新加载'; ($('start') as HTMLButtonElement).disabled = false; $('start').onclick = () => location.reload(); }
}
void load();
void fetch(new URL('training.json', base)).then(async response => {
  if (!response.ok) throw new Error('记录加载失败');
  const data = await response.json();
  const r = data.evaluations.candidate;
  const points: [number, number][] = data.training.history.map((row: any) => [row.update, row.mean_net_score]);
  const min = Math.min(...points.map(p => p[1]), -4); const max = Math.max(...points.map(p => p[1]), 4);
  const line = points.map(([x, y]) => `${35 + (x - 1) / 39 * 630},${195 - (y - min) / (max - min) * 150}`).join(' ');
  $('training-content').innerHTML = `<div class="metric"><small>独立验收</small><strong>${r.games.toLocaleString()}<span> 局</span></strong><p>未参与模型选择的 holdout</p></div><div class="metric"><small>平均净得分</small><strong>+${r.mean_net_score.toFixed(2)}<span> 分 / 盘</span></strong><p>三个冻结 qualified 对手</p></div><div class="metric"><small>和牌 / 放炮 / 流局</small><strong class="rate">${(r.win_rate * 100).toFixed(1)} / ${(r.discard_rate * 100).toFixed(1)} / ${(r.exhaustive_draw_rate * 100).toFixed(1)}<span> %</span></strong><p>席位按 0 / 1 / 2 / 3 轮换</p></div><section class="panel record-wide"><h2>独立评估 · 配对净得分差</h2><p class="muted">与相同种子、相同席位的基线比较；95% 置信区间。</p><table><thead><tr><th>相对基线</th><th>平均差</th><th>95% CI</th><th>结论</th></tr></thead><tbody>${['closed', 'qualified'].map(k => { const c = data.comparisons[k]; return `<tr><td>${k === 'closed' ? '闭门教师' : 'qualified 教师'}</td><td>+${c.mean_difference.toFixed(3)}</td><td>[${c.ci95.map((n: number) => n.toFixed(3)).join(', ')}]</td><td>${k === 'closed' ? '通过优于基线门槛' : '通过非劣门槛，未证明更强'}</td></tr>`; }).join('')}</tbody></table></section><section class="panel record-wide"><h2>后续 PPO 分支 · 真实训练记录</h2><p class="muted">40 次更新 · 19,200 局 · 8 个采样进程。下图是训练批次平均净得分，不是固定对手评估曲线，也不是胜率。</p><svg class="training-chart" viewBox="0 0 700 230" role="img" aria-label="PPO v2 各训练批次真实平均净得分曲线"><line x1="35" x2="665" y1="195" y2="195" stroke="#d3ded5"/><polyline points="${line}" fill="none" stroke="#246b54" stroke-width="2.5"/><text x="35" y="220">更新 1</text><text x="610" y="220">更新 40</text><text x="5" y="50">${max.toFixed(0)}</text><text x="5" y="195">${min.toFixed(0)}</text></svg><p>这个新分支没有超过开发集原候选，所以牌桌仍使用已验收的 PPO40 + 启发式保护，没有自动换成最新权重。</p></section><section class="panel record-wide"><h2>开发集模型比较</h2><p class="muted">用于选择模型的 1,600 局，不作为最终验收。保护配置与原始网络分开记录。</p><div class="comparison-list">${data.selection.candidates.map((c: any) => `<div><span>${escape(c.checkpoint.split('/').at(-1).replace('.pt', ''))}<small>${c.guard === 'none' ? '原始网络 + scaffold' : '网络 + teacher-optimal 保护'}</small></span><b>${c.mean_net_score >= 0 ? '+' : ''}${c.mean_net_score.toFixed(3)}</b></div>`).join('')}</div></section>`;
  if (data.sofy) $('training-content').insertAdjacentHTML('afterbegin', sofyRecord(data.sofy));
  if (data.arena) $('training-content').insertAdjacentHTML('afterbegin', arenaRecord(data.arena));
}).catch(e => { $('training-content').textContent = `${e.message}，请重新加载页面。`; });
