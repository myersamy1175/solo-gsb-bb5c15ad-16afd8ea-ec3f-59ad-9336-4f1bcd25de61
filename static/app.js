"use strict";

const EXAMPLE_OK = [
  "起床,洗漱,10,30",
  "洗漱,早饭,15,45",
  "早饭,出门,20,60",
  "出门,开会,40,90",
  "起床,开会,80,240",
  "起床,早饭,25,90",
].join("\n");

// 矛盾示例：
// 1) 开会比早饭晚 30~60；2) 晚饭比开会晚 45~90；3) 早饭比晚饭晚 20~50
// 三式相加 0 <= 95~200 与第三式给出的“晚饭早于早饭”冲突，构成闭合负环。
const EXAMPLE_CONFLICT = [
  "早饭,开会,30,60",
  "开会,晚饭,45,90",
  "晚饭,早饭,20,50",
].join("\n");

// 两版比较示例：修订版放宽了前两链下界、把“出门”合并掉（删除事件），
// 并新增“午休、下班”事件链。
const EXAMPLE_COMPARE_BASE = [
  "起床,洗漱,10,30",
  "洗漱,早饭,15,45",
  "早饭,出门,20,60",
  "出门,开会,40,90",
  "起床,开会,80,240",
].join("\n");

const EXAMPLE_COMPARE_REVISED = [
  "起床,洗漱,15,35",
  "洗漱,早饭,20,50",
  "早饭,开会,50,100",
  "起床,开会,80,240",
  "开会,午休,30,60",
  "午休,下班,60,120",
].join("\n");

// 绝对时间锚定示例：配合可行示例区间，起床钉在 06:30、开会钉在 09:00（相差 150 分钟，
// 落在第 5 行 [80,240] 内），其余事件由区间推出各自的绝对时刻范围。
const EXAMPLE_ANCHORS = [
  "起床,2024-03-05 06:30",
  "开会,2024-03-05 09:00",
].join("\n");

// 互斥说法示例：配合可行示例共同约束。第 1 组 A 侧（起床比开会晚 300~400 分钟）与共同约束
// 第 5 行（开会比起床晚 80~240）冲突，含它的组合被排除；第 2 组两种说法都可行。
// 查询“起床 vs 开会”：2 个可行组合合并区间 [85, 225]，下界 ≥ 1 ⇒ 起床始终先于开会。
const EXAMPLE_PRECEDENCE_GROUPS = [
  "开会,起床,-400,-300 | 起床,开会,80,240",
  "早饭,午休,5,15 | 出门,午休,5,15",
].join("\n");
const EXAMPLE_PRECEDENCE_A = "起床";
const EXAMPLE_PRECEDENCE_B = "开会";

// 最少撤回示例：前 3 行构成闭合负环（同矛盾示例），撤回其中任意 1 行即恢复可行；
// 第 4 行“睡觉→起床”与冲突无关，会保留在每个方案的剩余约束与可行时间线中。
const EXAMPLE_WITHDRAWAL = [
  "早饭,开会,30,60",
  "开会,晚饭,45,90",
  "晚饭,早饭,20,50",
  "睡觉,起床,360,480",
].join("\n");

// 别名归并可行示例：区间里混用同一事件的不同名称（盥洗=洗漱、晨会=开会），
// 第 6 行“洗漱,盥洗,-5,5”为同组内区间（归并后要求 0 落在 [-5,5]，满足），照常参与判定。
const EXAMPLE_ALIAS_OK_TEXT = [
  "起床,洗漱,10,30",
  "盥洗,早饭,15,45",
  "早饭,出门,20,60",
  "出门,晨会,40,90",
  "起床,开会,80,240",
  "洗漱,盥洗,-5,5",
].join("\n");
const EXAMPLE_ALIAS_OK_ALIASES = [
  "洗漱,盥洗",
  "开会,晨会",
].join("\n");

// 别名归并矛盾示例：未归并时“洗漱”“盥洗”是两个事件、区间本身可行；
// 别名把二者归并后，起床→洗漱→早饭→起床 构成闭合负环
// （前两行推出早饭比起床晚 25~75 分钟，与第 3 行“起床比早饭晚 10~20”冲突）。
const EXAMPLE_ALIAS_CONFLICT_TEXT = [
  "起床,洗漱,10,30",
  "盥洗,早饭,15,45",
  "早饭,起床,10,20",
].join("\n");
const EXAMPLE_ALIAS_CONFLICT_ALIASES = "洗漱,盥洗";

// 行程可达性核对——可行示例：与页面可行示例同一组事件，区间给出的时间差足够覆盖
// 家→餐馆(15)、餐馆→公司(25) 的最短通行；另有一条较慢的直达“家→公司 60”，
// 多跳 15+25=40 更短。时间线同时满足全部区间与通行下界。
const EXAMPLE_ITINERARY_OK_TEXT = [
  "起床,早饭,20,120",
  "早饭,开会,30,120",
  "起床,开会,60,300",
].join("\n");
const EXAMPLE_ITINERARY_OK_PLACES = [
  "起床,家",
  "早饭,餐馆",
  "开会,公司",
].join("\n");
const EXAMPLE_ITINERARY_OK_ROUTES = [
  "家,餐馆,15",
  "餐馆,公司,25",
  "家,公司,60",
].join("\n");
const EXAMPLE_ITINERARY_OK_ORDER = ["起床", "早饭", "开会"].join("\n");

// 行程可达性核对——时间冲突示例：两段最短通行合计至少 40 分钟，
// 但第 3 行要求开会比起床最多晚 30 分钟 ⇒ 通行下界与原区间联立形成负环。
const EXAMPLE_ITINERARY_CONFLICT_TEXT = [
  "起床,早饭,10,60",
  "早饭,开会,10,60",
  "起床,开会,0,30",
].join("\n");

// 行程可达性核对——无路可达示例：有向路网只有 家→餐馆，餐馆→公司 无任何有向路径，
// 第 2 个事件段“早饭 → 开会”被标为无路可达。
const EXAMPLE_ITINERARY_UNREACH_ROUTES = "家,餐馆,15";

// 有序事件最大统一间隔——有界示例：配合可行示例区间，顺序 起床→早饭→开会 的最大统一间隔
// 为 75 分钟（起床→早饭 受第 1、2 行链式上界 30+45=75 分钟限制；再增大 1 分钟即不可行）。
const EXAMPLE_MAXGAP_OK_ORDER = ["起床", "早饭", "开会"].join("\n");

// 无上限示例：三段互不相干的区间链，所选顺序 起床→出门→午休 的相邻对都跨事件组件，
// 原区间给不出任何间隔上界 ⇒ g 无上限，展示 g=0（保持先后顺序）的可行时间线。
const EXAMPLE_MAXGAP_UNBOUNDED_TEXT = [
  "起床,洗漱,10,30",
  "出门,开会,40,90",
  "午休,下班,60,120",
].join("\n");
const EXAMPLE_MAXGAP_UNBOUNDED_ORDER = ["起床", "出门", "午休"].join("\n");

// 顺序冲突示例：区间迫使开会比起床晚至少 30 分钟，所选顺序 开会→起床 连 g=0 都不成立。
const EXAMPLE_MAXGAP_CONFLICT_TEXT = [
  "起床,洗漱,10,30",
  "洗漱,开会,20,40",
].join("\n");
const EXAMPLE_MAXGAP_CONFLICT_ORDER = ["开会", "起床"].join("\n");

const $ = (id) => document.getElementById(id);
const resultEl = $("result");
const redundancyEl = $("redundancy-result");
const repairEl = $("repair-result");
const inputEl = $("input");
const lineSelect = $("redundancy-line");
const compareEl = $("compare-result");
const baseEl = $("compare-base");
const revisedEl = $("compare-revised");
const anchorInputEl = $("anchor-input");
const anchorEl = $("anchor-result");
const precEl = $("precedence-result");
const precGroupsEl = $("prec-groups");
const precAEl = $("prec-a");
const precBEl = $("prec-b");
const withdrawEl = $("withdraw-result");
const aliasInputEl = $("alias-input");
const aliasEl = $("alias-result");
const itineraryPlacesEl = $("itinerary-places");
const itineraryRoutesEl = $("itinerary-routes");
const itineraryOrderEl = $("itinerary-order");
const itineraryEl = $("itinerary-result");
const maxgapOrderEl = $("maxgap-order");
const maxgapEl = $("maxgap-result");

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function renderErrors(errors, target = resultEl) {
  const items = errors.map((e) =>
    `<li>${esc(e.message)}</li>`
  ).join("");
  target.innerHTML = `
    <div class="banner err">
      <h2>输入校验未通过</h2>
      <p>请修正下列问题后重新联立（行号对应文本框中的原始行号）：</p>
    </div>
    <div class="card"><ul class="plain">${items}</ul></div>`;
}

function renderOk(data) {
  const rows = data.timeline.map((t) =>
    `<tr><td>${esc(t.event)}</td><td class="num">${t.minute}</td></tr>`
  ).join("");

  const maxMinute = Math.max(...data.timeline.map((t) => t.minute));
  const points = data.timeline.map((t) => `
    <div class="tl-point">
      <div class="tl-dot"></div>
      <div class="tl-name">${esc(t.event)}</div>
      <div class="tl-time">第 ${t.minute} 分钟</div>
    </div>`).join("");

  const checks = data.differences.map((d) => {
    const fit = d.low <= d.actual && d.actual <= d.high;
    return `<tr>
      <td class="num">${d.line}</td>
      <td>${esc(d.a)} → ${esc(d.b)}</td>
      <td class="num">[${d.low}, ${d.high}]</td>
      <td class="num">${d.actual}</td>
      <td>${fit ? '<span class="ok-text">满足</span>' : '<span style="color:var(--err)">不满足</span>'}</td>
    </tr>`;
  }).join("");

  resultEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 区间无冲突</h2>
      <p>共 ${data.event_count} 个事件、${data.line_count} 条约束；以下时间线以最早事件为第 0 分钟，且满足全部区间。</p>
    </div>
    <div class="card">
      <h3>可行时间线</h3>
      <div class="timeline-track">
        <div class="tl-line"></div>
        <div class="tl-grid">${points}</div>
      </div>
      <table>
        <thead><tr><th>事件</th><th class="num">分钟（最早事件 = 0）</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">时间跨度：0 ~ ${maxMinute} 分钟。所有事件可整体平移，差值不变。</p>
    </div>
    <div class="card">
      <h3>逐条核对</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>事件对</th><th class="num">要求区间</th>
          <th class="num">本时间线差值</th><th>结果</th>
        </tr></thead>
        <tbody>${checks}</tbody>
      </table>
    </div>`;
}

// 矛盾链/推导路径步骤的行号引用：区间行显示“第 N 行”，锚点行显示“锚点第 N 行”
function stepLineRef(s) {
  return s.source === "anchor" ? `锚点第 ${s.line} 行` : `第 ${s.line} 行`;
}

// 步骤的界值显示：锚点边显示日期时刻文本，区间边显示分钟界值
function stepBoundText(s) {
  return s.kind === "anchor" ? (s.anchor_time || String(s.bound)) : String(s.bound);
}

// 闭合矛盾链的链式图：事件节点 + 行号/界值标注，最后回到起点形成闭合环
function conflictChainHtml(c) {
  const steps = c.steps;
  const parts = [];
  steps.forEach((s, i) => {
    if (i === 0) parts.push(`<div class="chain-node">${esc(s.from)}</div>`);
    parts.push(`
      <div class="chain-edge">
        <span class="tag ${s.kind}">${stepLineRef(s)} · ${esc(s.kind_label)} ${esc(stepBoundText(s))}</span>
        <span class="rel">${esc(s.relation)}</span>
        <span class="chain-arrow">→</span>
      </div>
      <div class="chain-node">${esc(s.to)}</div>`);
  });
  parts.push(`
    <div class="chain-edge">
      <span class="muted">闭合回到</span>
      <span class="chain-arrow">⟲</span>
    </div>
    <div class="chain-node">${esc(c.closes_to)}</div>`);
  return `<div class="chain">${parts.join("")}</div>`;
}

function renderConflict(data, target = resultEl) {
  const c = data.conflict;
  const steps = c.steps;

  const detailRows = steps.map((s) => `
    <tr>
      <td class="num">${stepLineRef(s)}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${esc(stepBoundText(s))}</td>
      <td>${esc(s.relation)}</td>
    </tr>`).join("");

  target.innerHTML = `
    <div class="banner conflict">
      <h2>✗ 区间存在冲突（闭合矛盾链）</h2>
      <p>下列 ${steps.length} 条原始行首尾相接形成闭合环，环上界值相加为负数
      （<strong>${c.weight_sum} &lt; 0</strong>），即推出“某事件必须早于自己”，无任何时间线可同时满足。</p>
    </div>
    <div class="card">
      <h3>矛盾链</h3>
      ${conflictChainHtml(c)}
    </div>
    <div class="card">
      <h3>涉及的原始行与上下界</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>图中方向</th><th>使用的界</th>
          <th class="num">界值</th><th>含义</th>
        </tr></thead>
        <tbody>${detailRows}</tbody>
      </table>
      <p class="muted">“上界”取该行最多分钟（事件乙 − 事件甲 ≤ 上界）；“下界”取该行最少分钟（事件乙 − 事件甲 ≥ 下界）；
      “锚点”取该锚点行的日期时刻（事件 − 统一零点 = 锚定分钟数）。</p>
    </div>`;
}

async function solve() {
  const text = inputEl.value;
  resultEl.innerHTML = `<div class="card muted">联立中…</div>`;
  try {
    const resp = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    if (data.status === "ok") renderOk(data);
    else if (data.status === "conflict") renderConflict(data);
    else renderErrors(data.errors || [{ line: null, message: "未知错误。" }]);
  } catch (err) {
    resultEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

// ---------- 约束冗余核对 ----------

// 文本变化时刷新可选行（跳过空行，行号保持原始行号）
function refreshLineOptions() {
  const prev = lineSelect.value;
  lineSelect.innerHTML = "";
  let count = 0;
  inputEl.value.split("\n").forEach((raw, i) => {
    const line = raw.trim();
    if (!line) return;
    const opt = document.createElement("option");
    opt.value = String(i + 1);
    opt.textContent = `第 ${i + 1} 行：${line}`;
    lineSelect.appendChild(opt);
    count += 1;
  });
  if (count === 0) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "（请先在上方输入约束行）";
    lineSelect.appendChild(opt);
    return;
  }
  if ([...lineSelect.options].some((o) => o.value === prev)) {
    lineSelect.value = prev;
  }
}

// 推导路径的链式图（复用矛盾链样式）
function pathChainHtml(steps) {
  if (!steps.length) {
    return `<p class="muted">无需任何其他约束：两事件为同一事件，时间差恒为 0。</p>`;
  }
  const parts = [`<div class="chain-node">${esc(steps[0].from)}</div>`];
  steps.forEach((s) => {
    parts.push(`
      <div class="chain-edge">
        <span class="tag ${s.kind}">第 ${s.line} 行 · ${esc(s.kind_label)} ${s.bound}</span>
        <span class="rel">${esc(s.relation)}</span>
        <span class="chain-arrow">→</span>
      </div>
      <div class="chain-node">${esc(s.to)}</div>`);
  });
  return `<div class="chain">${parts.join("")}</div>`;
}

// 推导路径的明细表：原始行号、方向、所用界与界值
function pathTableHtml(steps) {
  if (!steps.length) return "";
  const rows = steps.map((s) => `
    <tr>
      <td class="num">${s.line}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${s.bound}</td>
      <td>${esc(s.relation)}</td>
    </tr>`).join("");
  return `
    <table>
      <thead><tr>
        <th class="num">行号</th><th>图中方向</th><th>使用的界</th>
        <th class="num">界值</th><th>含义</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderRedundancy(data) {
  const removable = data.verdict === "removable";
  const lowText = data.lower_bounded ? String(data.derived_low) : "−∞（无界）";
  const highText = data.upper_bounded ? String(data.derived_high) : "+∞（无界）";
  const rest = data.line_count - 1;

  const reasons = [];
  if (!data.lower_bounded) {
    reasons.push("推导下界无界：删去该行后，其余约束对这两个事件的时间差给不出任何下限。");
  } else if (data.derived_low < data.low) {
    reasons.push(`推导下界 ${data.derived_low} 小于该行下界 ${data.low}：其余约束保证不了“最少 ${data.low} 分钟”。`);
  }
  if (!data.upper_bounded) {
    reasons.push("推导上界无界：删去该行后，其余约束对这两个事件的时间差给不出任何上限。");
  } else if (data.derived_high > data.high) {
    reasons.push(`推导上界 ${data.derived_high} 大于该行上界 ${data.high}：其余约束保证不了“最多 ${data.high} 分钟”。`);
  }

  const banner = removable
    ? `<div class="banner ok">
        <h2>✓ 可删：第 ${data.line} 行是冗余约束</h2>
        <p>删去该行后，其余 ${rest} 条约束推出的最紧区间为 <strong>[${lowText}, ${highText}]</strong>，
        完全落在该行区间 <strong>[${data.low}, ${data.high}]</strong> 内——其余叙述必然满足它，删去不损失信息。</p>
      </div>`
    : `<div class="banner conflict">
        <h2>✗ 必要：第 ${data.line} 行不可删</h2>
        <p>删去该行后，其余 ${rest} 条约束只能推出 <strong>[${lowText}, ${highText}]</strong>，
        未完全落在该行区间 <strong>[${data.low}, ${data.high}]</strong> 内：</p>
        <ul class="plain">${reasons.map((r) => `<li>· ${esc(r)}</li>`).join("")}</ul>
      </div>`;

  const summary = `
    <div class="card">
      <h3>结论依据</h3>
      <table>
        <thead><tr>
          <th>区间</th><th class="num">下界（最少分钟）</th><th class="num">上界（最多分钟）</th>
        </tr></thead>
        <tbody>
          <tr>
            <td>第 ${data.line} 行原区间：${esc(data.a)} → ${esc(data.b)}</td>
            <td class="num">${data.low}</td>
            <td class="num">${data.high}</td>
          </tr>
          <tr>
            <td>删去该行后，其余约束推导区间</td>
            <td class="num">${lowText}</td>
            <td class="num">${highText}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted">判定规则：推导下界 ≥ 原下界 且 推导上界 ≤ 原上界（推导区间完全落在原区间内）⇒ 可删；任一端点无界或超出 ⇒ 必要。</p>
    </div>`;

  const upperCard = data.upper_bounded ? `
    <div class="card">
      <h3>上界推导路径：t(${esc(data.b)}) − t(${esc(data.a)}) ≤ ${data.derived_high}</h3>
      <p class="muted">沿路径各边权值相加即最紧上界 ${data.derived_high}；每环标注原始行号与所用界值。</p>
      ${pathChainHtml(data.upper_path)}
      ${pathTableHtml(data.upper_path)}
    </div>` : `
    <div class="card">
      <h3>上界推导路径</h3>
      <p class="muted">在其余约束中，从 “${esc(data.a)}” 到 “${esc(data.b)}” 没有任何可推导路径，上界标为无界（+∞）。</p>
    </div>`;

  const lowerCard = data.lower_bounded ? `
    <div class="card">
      <h3>下界推导路径：t(${esc(data.b)}) − t(${esc(data.a)}) ≥ ${data.derived_low}</h3>
      <p class="muted">路径由 “${esc(data.b)}” 指向 “${esc(data.a)}”，权值之和为 ${-data.derived_low}，
      即 t(${esc(data.a)}) − t(${esc(data.b)}) ≤ ${-data.derived_low}，等价于 t(${esc(data.b)}) − t(${esc(data.a)}) ≥ ${data.derived_low}。</p>
      ${pathChainHtml(data.lower_path)}
      ${pathTableHtml(data.lower_path)}
    </div>` : `
    <div class="card">
      <h3>下界推导路径</h3>
      <p class="muted">在其余约束中，从 “${esc(data.b)}” 到 “${esc(data.a)}” 没有任何可推导路径，下界标为无界（−∞）。</p>
    </div>`;

  redundancyEl.innerHTML = banner + summary + upperCard + lowerCard;
}

async function checkRedundancy() {
  const line = parseInt(lineSelect.value, 10);
  if (!line) {
    redundancyEl.innerHTML = `
      <div class="banner err"><h2>未选择有效行</h2><p>请先在上方输入约束文本，再选择一条原始行。</p></div>`;
    return;
  }
  redundancyEl.innerHTML = `<div class="card muted">核对中…</div>`;
  try {
    const resp = await fetch("/api/redundancy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value, line }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      renderRedundancy(data);
    } else if (data.status === "conflict") {
      // 原约束冲突：沿用现有求解结果展示
      renderConflict(data, redundancyEl);
      redundancyEl.insertAdjacentHTML("afterbegin",
        `<p class="muted">原约束互相冲突，无法进行冗余核对；以下为现有联立求解结果：</p>`);
    } else {
      // 输入无效：沿用现有求解结果展示
      renderErrors(data.errors || [{ line: null, message: "未知错误。" }], redundancyEl);
      redundancyEl.insertAdjacentHTML("afterbegin",
        `<p class="muted">输入未通过校验，无法进行冗余核对；以下为现有联立求解结果：</p>`);
    }
  } catch (err) {
    redundancyEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

// ---------- 冲突单行修订建议 ----------

// 把建议的替换整行写回文本框对应原始行号（空行与原位保持不变），并触发 input 清空旧结果
function applySuggestion(line, newLine) {
  const lines = inputEl.value.split("\n");
  if (line < 1 || line > lines.length) return;
  lines[line - 1] = newLine;
  inputEl.value = lines.join("\n");
  inputEl.dispatchEvent(new Event("input"));
  solve();  // 立即联立，确认修订后的文本已可解
  inputEl.focus();
}

function renderRepairOk(data) {
  repairEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 无需修订</h2>
      <p>${esc(data.message || "原文本区间无冲突，无需修订。")}
      （共 ${data.event_count} 个事件、${data.line_count} 条约束，可直接“联立核对”查看可行时间线。）</p>
    </div>`;
}

function renderRepairConflict(data) {
  const n = data.suggestion_count;
  const banner = n > 0
    ? `<div class="banner conflict">
        <h2>✗ 区间存在冲突：找到 ${n} 条单行修订建议</h2>
        <p>以下每条建议只放宽<strong>某一行的一个端点</strong>即可消除全部矛盾（已按改动分钟数、原始行号排序）；
        改动量为移到“首次相交的整数分钟”的最小值。点击“填入此建议”会把替换后的整行写回上方文本框。</p>
      </div>`
    : `<div class="banner err">
        <h2>✗ 区间存在冲突：没有单行修复方案</h2>
        <p>已逐一尝试全部 ${data.checked_lines} 条原始行：删去任意一行后，其余行仍然互相矛盾，
        只放宽某一行的某一个端点无法消除冲突，请至少修改两行，或结合矛盾链人工调整。</p>
      </div>`;

  const cards = data.suggestions.map((s) => {
    const dirText = s.endpoint === "low"
      ? `其余 ${data.line_count - 1} 行推出 ${esc(s.a)} → ${esc(s.b)} 的时间差最多为
         <strong>${s.derived_high}</strong> 分钟，小于该行下界 ${s.low}；
         只把<strong>下界（最少分钟）</strong>从 ${s.old_value} 放宽到 <strong>${s.new_value}</strong>
         （改动 ${s.change_minutes} 分钟），区间即与推导区间首次相交。`
      : `其余 ${data.line_count - 1} 行推出 ${esc(s.a)} → ${esc(s.b)} 的时间差至少为
         <strong>${s.derived_low}</strong> 分钟，大于该行上界 ${s.high}；
         只把<strong>上界（最多分钟）</strong>从 ${s.old_value} 放宽到 <strong>${s.new_value}</strong>
         （改动 ${s.change_minutes} 分钟），区间即与推导区间首次相交。`;
    return `
    <div class="card repair-card">
      <h3>第 ${s.line} 行：放宽${esc(s.endpoint_label)}，改动 ${s.change_minutes} 分钟</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>事件对</th><th class="num">原区间</th>
          <th class="num">其余行推导区间</th><th class="num">改动端点</th><th class="num">改动分钟</th>
        </tr></thead>
        <tbody><tr>
          <td class="num">${s.line}</td>
          <td>${esc(s.a)} → ${esc(s.b)}</td>
          <td class="num">[${s.low}, ${s.high}]</td>
          <td class="num">[${s.derived_low}, ${s.derived_high}]</td>
          <td class="num">${esc(s.endpoint_label)} ${s.old_value} → ${s.new_value}</td>
          <td class="num"><strong>${s.change_minutes}</strong></td>
        </tr></tbody>
      </table>
      <p class="muted">${dirText}</p>
      <p class="repair-newline">替换后的整行：<code>${esc(s.new_line)}</code>
        <button class="repair-apply" data-line="${s.line}" data-newline="${esc(s.new_line)}">填入此建议</button>
      </p>
      ${s.forcing_lines.length
        ? `<h3>迫使该端点移动的推导链（第 ${s.forcing_lines.join("、")} 行）</h3>
           ${pathChainHtml(s.forcing_path)}
           ${pathTableHtml(s.forcing_path)}`
        : `<h3>迫使该端点移动的推导链</h3>
           <p class="muted">迫使端点移动的是该行自身之外已无其他约束：两事件为同一事件，时间差恒为 0。</p>`}
    </div>`;
  }).join("");

  repairEl.innerHTML = banner + cards;
  repairEl.querySelectorAll(".repair-apply").forEach((btn) => {
    btn.addEventListener("click", () => {
      applySuggestion(parseInt(btn.dataset.line, 10), btn.dataset.newline);
    });
  });
}

async function fetchRepair() {
  repairEl.innerHTML = `<div class="card muted">逐行尝试修订中…</div>`;
  try {
    const resp = await fetch("/api/repair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      renderRepairOk(data);
    } else if (data.status === "conflict") {
      renderRepairConflict(data);
    } else {
      renderErrors(data.errors || [{ line: null, message: "未知错误。" }], repairEl);
      repairEl.insertAdjacentHTML("afterbegin",
        `<p class="muted">输入未通过校验，无法给出修订建议；请修正后重试。</p>`);
    }
  } catch (err) {
    repairEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-repair").addEventListener("click", fetchRepair);

// ---------- 绝对时间锚定 ----------

// 绝对时刻显示：精确点显示单个时刻，范围显示“最早 ~ 最晚”；超出可表示范围时如实标注
function fmtAbsRange(e) {
  if (e.abs_low === null || e.abs_high === null) {
    return "超出可表示范围";
  }
  return e.exact ? e.abs_low : `${e.abs_low} ~ ${e.abs_high}`;
}

function renderAnchorOk(data) {
  const unlocated = data.event_count - data.located_count;

  const rows = data.events.map((e) => {
    if (!e.located) {
      return `<tr>
        <td>${esc(e.event)}</td>
        <td colspan="2"><span class="tag unlocated">未定位</span></td>
      </tr>`;
    }
    const status = e.exact
      ? `<span class="tag exact">精确</span>`
      : `<span class="tag range">范围（${e.minute_high - e.minute_low} 分钟）</span>`;
    return `<tr>
      <td>${esc(e.event)}</td>
      <td class="num">${esc(fmtAbsRange(e))}</td>
      <td>${status}</td>
    </tr>`;
  }).join("");

  const anchorRows = data.anchors.map((a) => `
    <tr>
      <td class="num">锚点第 ${a.line} 行</td>
      <td>${esc(a.event)}</td>
      <td class="num">${esc(a.time)}</td>
    </tr>`).join("");

  anchorEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 锚定求解完成</h2>
      <p>共 ${data.anchor_count} 条锚点、${data.line_count} 条区间约束、${data.event_count} 个事件：
      <strong>${data.located_count}</strong> 个与锚点连通、已定位${unlocated ? `；<strong>${unlocated}</strong> 个与任何锚点都不连通，标为“未定位”` : ""}。</p>
    </div>
    <div class="card">
      <h3>绝对日期时刻</h3>
      <table>
        <thead><tr>
          <th>事件</th><th class="num">绝对时刻（同一无时区本地时间）</th><th>状态</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">已定位事件的时刻由锚点与区间共同钉死：范围端点为其余约束推出的最紧界，
      区间内任意取值都满足全部约束；未定位事件与任何锚点都不连通，只有相对区间，
      不显示日期以免把任意平移量误认为真实日期。</p>
    </div>
    <div class="card">
      <h3>本次使用的锚点</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>事件</th><th class="num">锚定时刻</th>
        </tr></thead>
        <tbody>${anchorRows}</tbody>
      </table>
    </div>`;
}

async function solveAnchor() {
  anchorEl.innerHTML = `<div class="card muted">锚定联立中…</div>`;
  try {
    const resp = await fetch("/api/anchor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value, anchors: anchorInputEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") renderAnchorOk(data);
    else if (data.status === "conflict") renderConflict(data, anchorEl);
    else renderErrors(data.errors || [{ line: null, message: "未知错误。" }], anchorEl);
  } catch (err) {
    anchorEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-anchor").addEventListener("click", solveAnchor);
$("btn-anchor-example").addEventListener("click", () => {
  anchorInputEl.value = EXAMPLE_ANCHORS;
  if (!inputEl.value.trim()) {
    inputEl.value = EXAMPLE_OK;  // 锚点示例配合可行示例区间演示
    refreshLineOptions();
  }
  solveAnchor();
});
$("btn-anchor-clear").addEventListener("click", () => {
  anchorInputEl.value = "";
  anchorEl.innerHTML = "";
  anchorInputEl.focus();
});
anchorInputEl.addEventListener("input", () => {
  anchorEl.innerHTML = "";  // 锚点已变，旧的锚定结论作废
});

$("btn-solve").addEventListener("click", solve);
$("btn-example-ok").addEventListener("click", () => {
  inputEl.value = EXAMPLE_OK;
  refreshLineOptions();
  solve();
});
$("btn-example-conflict").addEventListener("click", () => {
  inputEl.value = EXAMPLE_CONFLICT;
  refreshLineOptions();
  solve();
});
$("btn-clear").addEventListener("click", () => {
  inputEl.value = "";
  resultEl.innerHTML = "";
  redundancyEl.innerHTML = "";
  repairEl.innerHTML = "";
  anchorEl.innerHTML = "";
  precEl.innerHTML = "";
  withdrawEl.innerHTML = "";
  aliasEl.innerHTML = "";
  itineraryEl.innerHTML = "";
  maxgapEl.innerHTML = "";
  refreshLineOptions();
  inputEl.focus();
});
$("btn-redundancy").addEventListener("click", checkRedundancy);
inputEl.addEventListener("input", () => {
  refreshLineOptions();
  redundancyEl.innerHTML = "";  // 文本已变，旧的冗余结论作废
  repairEl.innerHTML = "";      // 文本已变，旧的修订建议作废
  anchorEl.innerHTML = "";      // 文本已变，旧的锚定结论作废
  precEl.innerHTML = "";        // 共同约束已变，旧的先后查询结论作废
  withdrawEl.innerHTML = "";    // 文本已变，旧的最少撤回结论作废
  aliasEl.innerHTML = "";       // 区间已变，旧的别名归并结论作废
  itineraryEl.innerHTML = "";   // 区间已变，旧的行程可达性结论作废
  maxgapEl.innerHTML = "";      // 区间已变，旧的最大统一间隔结论作废
});
refreshLineOptions();

// ---------- 两版比较 ----------

const KIND_LABEL = {
  changed: "变化",
  unchanged: "未变",
  added: "新增",
  removed: "删除",
  incomparable: "不可比",
};

const CHANGE_LABEL = {
  added: "新增行",
  changed: "已修改",
  unchanged: "区间未改",
};

function fmtDelta(delta) {
  if (delta === null || delta === undefined) return { text: "—", cls: "delta-na" };
  if (delta > 0) return { text: `+${delta}`, cls: "delta-up" };
  if (delta < 0) return { text: `−${Math.abs(delta)}`, cls: "delta-down" };
  return { text: "0", cls: "delta-zero" };
}

function fmtMinute(m) {
  return m === null || m === undefined ? "—" : m;
}

// 证据明细表：在冗余核对路径表基础上增加该行相对基准的变化标记
function comparePathTableHtml(steps) {
  const rows = steps.map((s) => `
    <tr>
      <td class="num">${s.line}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${s.bound}</td>
      <td>${esc(s.relation)}</td>
      <td>${s.change ? `<span class="change-tag ${s.change}">${esc(CHANGE_LABEL[s.change] || s.change)}</span>` : ""}</td>
    </tr>`).join("");
  return `
    <table>
      <thead><tr>
        <th class="num">修订行号</th><th>图中方向</th><th>使用的界</th>
        <th class="num">界值</th><th>含义</th><th>相对基准</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderCompareOk(data) {
  const rows = data.alignment.map((e) => {
    // 后端共同事件统一为 common；有证据（delta≠0 且可比较）显示为“变化”，否则“未变”
    const renderKind = e.kind === "common"
      ? (e.evidence ? "changed" : "unchanged")
      : e.kind;
    const d = fmtDelta(e.delta);
    let lines = "";
    if (e.evidence) {
      lines = e.evidence.is_anchor
        ? `<span class="evidence-lines">（第 0 分钟锚点事件）</span>`
        : `<span class="evidence-lines">第 ${e.evidence.lines.join("、")} 行</span>`;
    }
    return `<tr>
      <td><span class="kind-tag ${renderKind}">${esc(KIND_LABEL[renderKind] || renderKind)}</span></td>
      <td>${esc(e.event)}</td>
      <td class="num">${fmtMinute(e.base_minute)}</td>
      <td class="num">${fmtMinute(e.revised_minute)}</td>
      <td class="num ${d.cls}">${d.text}</td>
      <td>${lines}</td>
    </tr>`;
  }).join("");

  const shiftNote = data.anchor_shifted
    ? `<p class="muted">⚠ 两版第 0 分钟事件不同（基准：${esc(data.base.anchor)}；修订：${esc(data.revised.anchor)}）。
       分钟数仍各自从本版最早事件起算；与公共锚点不连通的事件标为<strong>“不可比”</strong>，其分钟差只是各事件组件独立归零的结果，不构成修订变化。</p>`
    : `<p class="muted">两版共同以“${esc(data.base.anchor)}”为第 0 分钟事件，变化分钟数即相对同一锚点的时刻差。</p>`;

  const banner = `
    <div class="banner ok">
      <h2>✓ 两版比较完成</h2>
      <p>共同事件 ${data.common_count} 个（其中 <strong>${data.changed_count}</strong> 个分钟发生变化）；
      修订版新增 <strong>${data.added_count}</strong> 个事件、删除 <strong>${data.removed_count}</strong> 个事件
      ${data.incomparable_count ? `、<strong>${data.incomparable_count}</strong> 个事件与锚点不连通、不可比` : ""}。
      基准 ${data.base.line_count} 行 / ${data.base.event_count} 事件；修订 ${data.revised.line_count} 行 / ${data.revised.event_count} 事件。</p>
    </div>`;

  const tableCard = `
    <div class="card">
      <h3>事件对齐表</h3>
      <table>
        <thead><tr>
          <th>类型</th><th>事件</th>
          <th class="num">基准时刻</th><th class="num">修订时刻</th>
          <th class="num">变化分钟</th><th>导致变化的修订行</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${shiftNote}
    </div>`;

  // 仅为“分钟发生变化”的共同事件展开修订时刻的推导路径证据
  const evidenceCards = data.alignment
    .filter((e) => e.kind === "common" && e.evidence && !e.evidence.is_anchor)
    .map((e) => {
      const ev = e.evidence;
      const d = fmtDelta(e.delta);
      const dirText = ev.direction === "upper"
        ? `修订时刻顶在该事件相对锚点的最紧<strong>上界 ${ev.bound}</strong>。`
        : `修订时刻顶在该事件相对锚点的最紧<strong>下界 ${ev.bound}</strong>。`;
      return `
      <div class="card evidence-card">
        <h3>变更行证据：${esc(e.event)}（${e.base_minute} → ${e.revised_minute}，${d.text} 分钟）</h3>
        <p class="ev-head">${dirText}推出该时刻用到的修订行为<strong>第 ${ev.lines.join("、")} 行</strong>；
        路径每环标注修订行号、所用界值，以及该行相对基准是“已修改 / 新增 / 区间未改”。</p>
        ${pathChainHtml(ev.path)}
        ${comparePathTableHtml(ev.path)}
      </div>`;
    }).join("");

  compareEl.innerHTML = banner + tableCard + evidenceCards;
}

// 一版无效/矛盾时，在该栏渲染错误列表或闭合矛盾链；不生成任何差异结论
function renderCompareSide(container, title, side) {
  const head = document.createElement("div");
  head.innerHTML = side.status === "conflict"
    ? `<h2>${title}：区间矛盾</h2>
       <p class="compare-side-head">该版本存在闭合矛盾链，不参与差异比较：</p>`
    : `<h2>${title}：校验未通过</h2>
       <p class="compare-side-head">该版本输入无效，不参与差异比较：</p>`;
  const body = document.createElement("div");
  if (side.status === "conflict") {
    renderConflict(side, body);  // 现有矛盾链渲染（含链图与明细表）
  } else {
    renderErrors(side.errors || [{ line: null, message: "未知错误。" }], body);
  }
  container.innerHTML = "";
  container.appendChild(head);
  container.appendChild(body);
}

async function compare() {
  compareEl.innerHTML = `<div class="card muted">两版独立联立中…</div>`;
  try {
    const resp = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base: baseEl.value, revised: revisedEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      renderCompareOk(data);
      return;
    }
    // 任一版无效或矛盾：分别展示对应错误/矛盾链，不给差异结论
    const cols = document.createElement("div");
    cols.className = "compare-cols";
    const baseCard = document.createElement("div");
    const revCard = document.createElement("div");
    baseCard.className = "card";
    revCard.className = "card";
    renderCompareSide(baseCard, "基准文本", data.base);
    renderCompareSide(revCard, "修订文本", data.revised);
    cols.appendChild(baseCard);
    cols.appendChild(revCard);
    compareEl.innerHTML = `
      <div class="banner err">
        <h2>无法生成两版差异结论</h2>
        <p>基准版或修订版存在校验错误或区间矛盾，已在下方分别列出；请修正后重新比较。</p>
      </div>`;
    compareEl.appendChild(cols);
  } catch (err) {
    compareEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-compare").addEventListener("click", compare);
$("btn-compare-example").addEventListener("click", () => {
  baseEl.value = EXAMPLE_COMPARE_BASE;
  revisedEl.value = EXAMPLE_COMPARE_REVISED;
  compare();
});
$("btn-compare-clear").addEventListener("click", () => {
  baseEl.value = "";
  revisedEl.value = "";
  compareEl.innerHTML = "";
  baseEl.focus();
});
// 任一输入框内容变化，旧的比较结果立即作废，避免展示与输入不一致的结论
[baseEl, revisedEl].forEach((el) => {
  el.addEventListener("input", () => { compareEl.innerHTML = ""; });
});

// ---------- 互斥说法下的先后查询 ----------

const PREC_VERDICT = {
  before: { cls: "ok", title: "✓ 甲始终先于乙" },
  after: { cls: "ok", title: "✓ 甲始终后于乙" },
  undetermined: { cls: "conflict", title: "? 先后关系不确定" },
  no_feasible: { cls: "err", title: "✗ 无可行组合，不作先后判断" },
};

function renderPrecedence(data) {
  const v = PREC_VERDICT[data.verdict] || PREC_VERDICT.undetermined;
  const noFeasible = data.verdict === "no_feasible";
  // 合并区间端点：无界显示 ±∞；无可行组合时合并区间无意义，显示 —
  const lowText = noFeasible ? "—" : (data.lower_bounded ? String(data.merged_low) : "−∞（无界）");
  const highText = noFeasible ? "—" : (data.upper_bounded ? String(data.merged_high) : "+∞（无界）");

  let verdictReason;
  if (data.verdict === "before") {
    verdictReason = `全部 ${data.feasible_count} 个可行组合中，t(${esc(data.b)}) − t(${esc(data.a)})
      的合并下界为 <strong>${lowText}</strong> 分钟 ≥ 1 分钟：无论各组互斥说法如何取舍，
      <strong>${esc(data.a)}</strong> 始终先于 <strong>${esc(data.b)}</strong>。`;
  } else if (data.verdict === "after") {
    verdictReason = `全部 ${data.feasible_count} 个可行组合中，t(${esc(data.b)}) − t(${esc(data.a)})
      的合并上界为 <strong>${highText}</strong> 分钟 ≤ −1 分钟：无论各组互斥说法如何取舍，
      <strong>${esc(data.a)}</strong> 始终后于 <strong>${esc(data.b)}</strong>。`;
  } else if (data.verdict === "undetermined") {
    verdictReason = `全部 ${data.feasible_count} 个可行组合的合并区间为
      <strong>[${lowText}, ${highText}]</strong>：合并下界未达到 ≥ 1 分钟、合并上界也未达到 ≤ −1 分钟，
      互斥说法的不同取舍可能改变先后关系，判为不确定。`;
  } else {
    verdictReason = `全部 ${data.combination_count} 个组合与共同约束联立后均互相冲突，
      没有任何可行组合，不作先后判断。`;
  }

  // 候选组对照表：每行的 A/B 两侧说法
  const fmtSide = (s) => `${s.a},${s.b},${s.low},${s.high}`;
  const groupRows = data.groups.map((g) => `<tr>
      <td class="num">第 ${g.line} 行</td>
      <td><code>${esc(fmtSide(g.sides[0]))}</code></td>
      <td><code>${esc(fmtSide(g.sides[1]))}</code></td>
    </tr>`).join("");

  // 组合明细表：每组所选一侧、联立结果、可行组合的 t(乙)−t(甲) 最紧区间
  const comboRows = data.combinations.map((c) => {
    const picks = c.picks.map((p) => `第${p.line}行${p.side}侧`).join("、");
    if (!c.feasible) {
      return `<tr class="combo-conflict">
        <td class="num">${c.index}</td>
        <td>${esc(picks)}</td>
        <td><span class="tag unlocated">冲突，排除</span></td>
        <td class="num">—</td>
      </tr>`;
    }
    const lo = c.lower_bounded ? String(c.low) : "−∞";
    const hi = c.upper_bounded ? String(c.high) : "+∞";
    return `<tr>
      <td class="num">${c.index}</td>
      <td>${esc(picks)}</td>
      <td><span class="tag exact">可行</span></td>
      <td class="num">[${lo}, ${hi}]</td>
    </tr>`;
  }).join("");

  precEl.innerHTML = `
    <div class="banner ${v.cls}">
      <h2>${v.title}</h2>
      <p>${verdictReason}</p>
    </div>
    <div class="card">
      <h3>组合统计与合并区间</h3>
      <table>
        <thead><tr>
          <th class="num">候选组</th><th class="num">组合总数</th>
          <th class="num">可行组合</th><th class="num">冲突组合</th>
          <th class="num">合并下界</th><th class="num">合并上界</th>
        </tr></thead>
        <tbody><tr>
          <td class="num">${data.group_count}</td>
          <td class="num">${data.combination_count}</td>
          <td class="num">${data.feasible_count}</td>
          <td class="num">${data.conflict_count}</td>
          <td class="num">${lowText}</td>
          <td class="num">${highText}</td>
        </tr></tbody>
      </table>
      <p class="muted">合并区间：跨可行组合取 t(乙) − t(甲) 最紧下界的最小值、最紧上界的最大值；
      任一可行组合对应端无界则合并端无界。判定规则：合并下界 ≥ 1 分钟 ⇒ 甲始终先于乙；
      合并上界 ≤ −1 分钟 ⇒ 甲始终后于乙；否则不确定；无可行组合不作先后判断。</p>
    </div>
    <div class="card">
      <h3>候选组（每行二选一）</h3>
      <table>
        <thead><tr><th class="num">行号</th><th>A 侧说法</th><th>B 侧说法</th></tr></thead>
        <tbody>${groupRows}</tbody>
      </table>
    </div>
    <div class="card">
      <h3>组合明细（共 ${data.combination_count} 个）</h3>
      <table>
        <thead><tr>
          <th class="num">组合</th><th>选取</th><th>联立结果</th>
          <th class="num">t(乙) − t(甲) 最紧区间</th>
        </tr></thead>
        <tbody>${comboRows}</tbody>
      </table>
    </div>`;
}

async function queryPrecedence() {
  precEl.innerHTML = `<div class="card muted">枚举组合联立中…</div>`;
  try {
    const resp = await fetch("/api/precedence", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: inputEl.value,
        groups: precGroupsEl.value,
        a: precAEl.value,
        b: precBEl.value,
      }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      renderPrecedence(data);
    } else {
      renderErrors(data.errors || [{ line: null, message: "未知错误。" }], precEl);
    }
  } catch (err) {
    precEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-precedence").addEventListener("click", queryPrecedence);
$("btn-precedence-example").addEventListener("click", () => {
  precGroupsEl.value = EXAMPLE_PRECEDENCE_GROUPS;
  precAEl.value = EXAMPLE_PRECEDENCE_A;
  precBEl.value = EXAMPLE_PRECEDENCE_B;
  if (!inputEl.value.trim()) {
    inputEl.value = EXAMPLE_OK;  // 互斥示例配合可行示例共同约束演示
    refreshLineOptions();
  }
  queryPrecedence();
});
$("btn-precedence-clear").addEventListener("click", () => {
  precGroupsEl.value = "";
  precEl.innerHTML = "";
  precGroupsEl.focus();
});
// 候选组或查询事件变化，旧的先后查询结论立即作废
[precGroupsEl, precAEl, precBEl].forEach((el) => {
  el.addEventListener("input", () => { precEl.innerHTML = ""; });
});

// ---------- 最少撤回 ----------

// 剩余约束可行时间线：无事件（撤回全部行）时显示空时间线提示
function timelineTableHtml(timeline) {
  if (!timeline.length) {
    return `<p class="muted">空时间线：剩余约束为空（已撤回全部行），空约束集视为可行。</p>`;
  }
  const rows = timeline.map((t) =>
    `<tr><td>${esc(t.event)}</td><td class="num">${t.minute}</td></tr>`).join("");
  return `
    <table>
      <thead><tr><th>事件</th><th class="num">分钟（最早事件 = 0）</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderWithdrawals(data) {
  const min = data.minimum;

  // 横幅：零撤回（原文可行 / 空约束集）与“最少撤回 k 行”三种语气
  let banner;
  if (min === 0 && data.total_lines === 0) {
    banner = `
      <div class="banner ok">
        <h2>✓ 空约束集可行：零撤回</h2>
        <p>${esc(data.message)}</p>
      </div>`;
  } else if (min === 0) {
    banner = `
      <div class="banner ok">
        <h2>✓ 原文无冲突：零撤回方案</h2>
        <p>${esc(data.message)} 共检查 ${data.checked_combinations} 个撤回组合。</p>
      </div>`;
  } else {
    banner = `
      <div class="banner conflict">
        <h2>最少撤回 ${min} 行（共 ${data.plans.length} 个方案）</h2>
        <p>${esc(data.message)} 共检查 ${data.checked_combinations} 个撤回组合；
        各方案撤回的原始行号不同，但撤回行数同为最少的 <strong>${min}</strong> 行。</p>
      </div>`;
  }

  // 撤回行对照：原始行号 + 上方文本框中的原文内容（空行不会被撤回）
  const rawLines = inputEl.value.split("\n");
  const cards = data.plans.map((p) => {
    const withdrawnRows = p.withdrawn_lines.map((ln) =>
      `<tr><td class="num">第 ${ln} 行</td><td><code>${esc(rawLines[ln - 1] !== undefined ? rawLines[ln - 1].trim() : "")}</code></td></tr>`
    ).join("");
    const withdrawnBlock = p.withdrawn_lines.length
      ? `<table>
           <thead><tr><th class="num">撤回的原始行号</th><th>该行原文</th></tr></thead>
           <tbody>${withdrawnRows}</tbody>
         </table>`
      : `<p class="muted">不撤回任何行。</p>`;
    const heading = p.withdrawn_lines.length
      ? `方案 ${p.index}：撤回 ${p.withdraw_count} 行（第 ${p.withdrawn_lines.join("、")} 行），保留 ${p.remaining_count} 行`
      : `方案 ${p.index}：零撤回，保留全部 ${p.remaining_count} 行`;
    return `
    <div class="card withdraw-card">
      <h3>${heading}</h3>
      ${withdrawnBlock}
      <h3>剩余约束的一条可行时间线</h3>
      ${timelineTableHtml(p.timeline)}
    </div>`;
  }).join("");

  // 原文矛盾时附原始闭合矛盾链（可展开查看是哪几句话“打了架”）
  const conflictBlock = (min > 0 && data.conflict)
    ? `<details class="card withdraw-conflict">
         <summary>查看原文的闭合矛盾链（撤回前为何不可行）</summary>
         <div id="withdraw-conflict-body"></div>
       </details>`
    : "";

  withdrawEl.innerHTML = banner + cards + conflictBlock;
  if (min > 0 && data.conflict) {
    // 复用现有矛盾链渲染（链图 + 涉及原始行明细表）
    renderConflict({ conflict: data.conflict }, $("withdraw-conflict-body"));
  }
}

async function findWithdrawals() {
  withdrawEl.innerHTML = `<div class="card muted">按撤回行数递增搜索中…</div>`;
  try {
    const resp = await fetch("/api/withdrawals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") {
      renderWithdrawals(data);
    } else {
      renderErrors(data.errors || [{ line: null, message: "未知错误。" }], withdrawEl);
      withdrawEl.insertAdjacentHTML("afterbegin",
        `<p class="muted">输入未通过校验，无法进行最少撤回搜索；请修正后重试。</p>`);
    }
  } catch (err) {
    withdrawEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-withdraw").addEventListener("click", findWithdrawals);
$("btn-withdraw-example").addEventListener("click", () => {
  inputEl.value = EXAMPLE_WITHDRAWAL;
  refreshLineOptions();
  findWithdrawals();
});

// ---------- 事件别名归并核对 ----------

// 别名组卡片：每组统一事件名、组内原名称与是否出现在区间时间线中（可行/冲突共用）
function aliasGroupsCardHtml(data) {
  if (!data.groups.length) {
    return `
      <div class="card">
        <h3>别名组（每组原名称）</h3>
        <p class="muted">没有别名组。</p>
      </div>`;
  }
  const rows = data.groups.map((g, i) => `
    <tr>
      <td class="num">${i + 1}</td>
      <td>${esc(g.representative)}</td>
      <td>${esc(g.members.join("、"))}</td>
      <td>${g.in_timeline ? "在区间时间线中" : "未出现在区间中"}</td>
    </tr>`).join("");
  return `
    <div class="card">
      <h3>别名组（每组原名称）</h3>
      <table>
        <thead><tr>
          <th class="num">组</th><th>统一事件</th><th>组内原名称</th><th>状态</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">按传递关系归并（A=B、B=C ⇒ A、B、C 同组）；统一事件名为组内最先出现的名称，
      区间行两端与图中节点均改用统一事件名，行号保持原始行号。</p>
    </div>`;
}

function renderAliasOk(data) {
  const maxMinute = Math.max(...data.timeline.map((t) => t.minute));
  const points = data.timeline.map((t) => `
    <div class="tl-point">
      <div class="tl-dot"></div>
      <div class="tl-name">${esc(t.event)}</div>
      <div class="tl-time">第 ${t.minute} 分钟</div>
    </div>`).join("");

  const tlRows = data.timeline.map((t) => `
    <tr>
      <td>${esc(t.event)}</td>
      <td>${esc(t.members.join("、"))}</td>
      <td class="num">${t.minute}</td>
    </tr>`).join("");

  const diffRows = data.differences.map((d) => {
    const fit = d.low <= d.actual && d.actual <= d.high;
    const mergedPair = d.same_group
      ? `<span class="tag same">同组内</span> ${esc(d.merged_a)}`
      : `${esc(d.merged_a)} → ${esc(d.merged_b)}`;
    return `<tr>
      <td class="num">${d.line}</td>
      <td>${esc(d.a)} → ${esc(d.b)}</td>
      <td>${mergedPair}</td>
      <td class="num">[${d.low}, ${d.high}]</td>
      <td class="num">${d.actual}</td>
      <td>${fit ? '<span class="ok-text">满足</span>' : '<span style="color:var(--err)">不满足</span>'}</td>
    </tr>`;
  }).join("");

  const withinNote = data.within_group_count
    ? `<p class="muted">第 ${data.within_group_lines.join("、")} 行的两端归并为同一事件（同组内区间）：
       归并后要求 0 落在该行区间内，已照常参与判定。</p>`
    : "";

  aliasEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 别名归并后区间无冲突</h2>
      <p>共 ${data.alias_count} 条别名、${data.merged_group_count} 个别名组：区间文本中的
      ${data.original_event_count} 个事件名称归并为 <strong>${data.event_count}</strong> 个统一事件，
      ${data.line_count} 条区间约束（含 ${data.within_group_count} 条同组内区间）全部满足。
      以下时间线以最早事件为第 0 分钟，节点为统一事件。</p>
    </div>
    <div class="card">
      <h3>归并后的可行时间线</h3>
      <div class="timeline-track">
        <div class="tl-line"></div>
        <div class="tl-grid">${points}</div>
      </div>
      <table>
        <thead><tr><th>统一事件</th><th>组内原名称</th><th class="num">分钟（最早事件 = 0）</th></tr></thead>
        <tbody>${tlRows}</tbody>
      </table>
      <p class="muted">时间跨度：0 ~ ${maxMinute} 分钟。所有事件可整体平移，差值不变。</p>
    </div>
    ${aliasGroupsCardHtml(data)}
    <div class="card">
      <h3>逐条核对（原始行号）</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>原始事件对</th><th>归并后事件对</th>
          <th class="num">要求区间</th><th class="num">归并后差值</th><th>结果</th>
        </tr></thead>
        <tbody>${diffRows}</tbody>
      </table>
      ${withinNote}
    </div>`;
}

function renderAliasConflict(data) {
  const c = data.conflict;
  // 明细表：保留原始区间行号与原始事件名，同时给出归并后的图中方向
  const detailRows = c.steps.map((s) => `
    <tr>
      <td class="num">${stepLineRef(s)}</td>
      <td>${esc(s.row_a || s.from)} → ${esc(s.row_b || s.to)}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${esc(stepBoundText(s))}</td>
      <td>${esc(s.relation)}</td>
    </tr>`).join("");

  aliasEl.innerHTML = `
    <div class="banner conflict">
      <h2>✗ 别名归并造成矛盾</h2>
      <p>按 ${data.alias_count} 条别名归并后，归并节点联立原区间出现闭合矛盾链：下列 ${c.steps.length} 条
      <strong>原始区间行</strong>首尾相接形成闭合环，环上界值相加为负数（<strong>${c.weight_sum} &lt; 0</strong>），
      即推出“某事件必须早于自己”。链上行号为<strong>原始区间行号</strong>、节点名为统一事件名，
      参与的别名组及每组原名称见下表。</p>
    </div>
    ${aliasGroupsCardHtml(data)}
    <div class="card">
      <h3>归并后的闭合矛盾链</h3>
      ${conflictChainHtml(c)}
    </div>
    <div class="card">
      <h3>涉及的原始行与上下界</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>原始事件对</th><th>归并后方向</th><th>使用的界</th>
          <th class="num">界值</th><th>含义</th>
        </tr></thead>
        <tbody>${detailRows}</tbody>
      </table>
      <p class="muted">“原始事件对”为该区间行在文本框中的原写法；“归并后方向”为别名归并后的图中边（统一事件名）；
      “上界”取该行最多分钟，“下界”取该行最少分钟。</p>
    </div>`;
}

async function checkAliases() {
  aliasEl.innerHTML = `<div class="card muted">归并联立中…</div>`;
  try {
    const resp = await fetch("/api/aliases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value, aliases: aliasInputEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") renderAliasOk(data);
    else if (data.status === "conflict") renderAliasConflict(data);
    else renderErrors(data.errors || [{ line: null, message: "未知错误。" }], aliasEl);
  } catch (err) {
    aliasEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-alias").addEventListener("click", checkAliases);
$("btn-alias-example-ok").addEventListener("click", () => {
  inputEl.value = EXAMPLE_ALIAS_OK_TEXT;
  aliasInputEl.value = EXAMPLE_ALIAS_OK_ALIASES;
  refreshLineOptions();
  checkAliases();
});
$("btn-alias-example-conflict").addEventListener("click", () => {
  inputEl.value = EXAMPLE_ALIAS_CONFLICT_TEXT;
  aliasInputEl.value = EXAMPLE_ALIAS_CONFLICT_ALIASES;
  refreshLineOptions();
  checkAliases();
});
$("btn-alias-clear").addEventListener("click", () => {
  aliasInputEl.value = "";
  aliasEl.innerHTML = "";
  aliasInputEl.focus();
});
aliasInputEl.addEventListener("input", () => {
  aliasEl.innerHTML = "";  // 别名已变，旧的归并结论作废
});

// ---------- 行程可达性核对 ----------

// 一段最短路线的链图：地点节点 →（路段行号·分钟）→ 地点节点；同地点显示零分钟
function routeChainHtml(seg) {
  if (seg.same_place) {
    return `<span class="seg-sameplace">同地点（${esc(seg.from_place)}），按零分钟处理，不经过任何路段。</span>`;
  }
  if (!seg.reachable) {
    return `<span class="seg-unreachable">无路可达：地点网络中不存在从 “${esc(seg.from_place)}” 到 “${esc(seg.to_place)}” 的有向路径。</span>`;
  }
  const nodes = [seg.from_place, ...seg.route.map((r) => r.to)];
  const parts = [];
  seg.route.forEach((r, i) => {
    parts.push(`<span class="route-node">${esc(nodes[i])}</span>`);
    parts.push(`<span class="route-edge">→<span class="route-meta"> 路段第 ${r.line} 行 · ${r.minutes} 分钟</span></span>`);
  });
  parts.push(`<span class="route-node">${esc(nodes[nodes.length - 1])}</span>`);
  return `<div class="route-chain">${parts.join("")}
    <span class="route-meta">（合计 <strong>${seg.travel_minutes}</strong> 分钟，途经 ${seg.route.length} 条路段）</span></div>`;
}

// 各事件段总览表（可行/无路可达/冲突共用）：段号、事件对、地点对、同地点/可达、最短分钟、路线
function itinerarySegmentsTableHtml(segments, { withActual = false } = {}) {
  const rows = segments.map((s) => {
    let status;
    if (s.same_place) status = '<span class="tag exact">同地点 · 0 分钟</span>';
    else if (s.reachable) status = '<span class="tag range">可达</span>';
    else status = '<span class="tag unlocated seg-unreachable">无路可达</span>';
    const minutes = s.reachable ? s.travel_minutes : "—";
    const actualCell = withActual
      ? `<td class="num">${s.actual_minutes}</td><td class="num">+${s.slack_minutes}</td>`
      : "";
    return `<tr${s.reachable ? "" : ' class="combo-conflict"'}>
      <td class="num">第 ${s.index} 段</td>
      <td>${esc(s.from_event)} → ${esc(s.to_event)}</td>
      <td>${esc(s.from_place)} → ${esc(s.to_place)}</td>
      <td>${status}</td>
      <td class="num">${minutes}</td>
      ${actualCell}
    </tr>`;
  }).join("");
  const actualHead = withActual
    ? '<th class="num">时间线实际间隔</th><th class="num">较最短通行富余</th>'
    : "";
  return `
    <table>
      <thead><tr>
        <th class="num">事件段</th><th>事件（按发生顺序）</th><th>地点对</th>
        <th>可达性</th><th class="num">最短通行分钟</th>${actualHead}
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// 可行时间线表（含地点；全部参与联立的事件，按分钟排序）
function itineraryTimelineTableHtml(timeline) {
  const rows = timeline.map((t) =>
    `<tr><td>${esc(t.event)}</td><td>${esc(t.place === null || t.place === undefined ? "—" : t.place)}</td>
     <td class="num">${t.minute}</td></tr>`).join("");
  return `
    <table>
      <thead><tr><th>事件</th><th>地点</th><th class="num">分钟（最早事件 = 0）</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// 逐段路线卡片（每段独立展示最短路线与逐路段明细）
function itineraryRouteCardsHtml(segments) {
  return segments.map((s) => {
    const title = `第 ${s.index} 段：${s.from_event}（${s.from_place}）→ ${s.to_event}（${s.to_place}）`;
    if (!s.reachable && !s.same_place) {
      return `<div class="card"><h3>${esc(title)}</h3>${routeChainHtml(s)}</div>`;
    }
    const detailRows = s.same_place ? "" : s.route.map((r) => `
      <tr>
        <td class="num">路段第 ${r.line} 行</td>
        <td>${esc(r.from)} → ${esc(r.to)}</td>
        <td class="num">${r.minutes}</td>
      </tr>`).join("");
    const detailTable = s.same_place ? "" : `
      <table>
        <thead><tr><th class="num">路段行号</th><th>方向</th><th class="num">分钟</th></tr></thead>
        <tbody>${detailRows}</tbody>
      </table>`;
    const actual = s.actual_minutes !== undefined
      ? `<p class="muted">本时间线中该段实际间隔 <strong>${s.actual_minutes}</strong> 分钟，
         较最短通行富余 <strong>${s.slack_minutes}</strong> 分钟（通行下界已满足）。</p>`
      : "";
    return `<div class="card">
      <h3>${esc(title)}</h3>
      ${routeChainHtml(s)}
      ${actual}
      ${detailTable}
    </div>`;
  }).join("");
}

// 通行下界步骤的标签渲染（矛盾链 tag）：复用 tag.travel 配色
function itineraryStepTagHtml(s) {
  if (s.kind === "travel") {
    return `<span class="tag travel">事件段 ${s.segment} · 通行下界 ${s.bound}</span>`;
  }
  return `<span class="tag ${s.kind}">${stepLineRef(s)} · ${esc(s.kind_label)} ${esc(stepBoundText(s))}</span>`;
}

// 行程矛盾链：在通用矛盾链图基础上，通行下界环节补充事件段地点对与最短路线
function itineraryConflictChainHtml(c) {
  const steps = c.steps;
  const parts = [];
  steps.forEach((s, i) => {
    if (i === 0) parts.push(`<div class="chain-node">${esc(s.from)}</div>`);
    let extra = "";
    if (s.kind === "travel") {
      const segTitle = `事件段 ${s.segment}：${esc(s.from_event)}（${esc(s.from_place)}）→ ${esc(s.to_event)}（${esc(s.to_place)}）`;
      const routeDesc = s.route.length
        ? s.route.map((r) => `${esc(r.from)}→${esc(r.to)}(${r.minutes}分,路段第${r.line}行)`).join("，")
        : "同地点零分钟";
      extra = `<span class="route-meta">${segTitle}；最短路线：${routeDesc}，合计 ${s.travel_minutes} 分钟</span>`;
    }
    parts.push(`
      <div class="chain-edge">
        ${itineraryStepTagHtml(s)}
        <span class="rel">${esc(s.relation)}</span>
        ${extra}
        <span class="chain-arrow">→</span>
      </div>
      <div class="chain-node">${esc(s.to)}</div>`);
  });
  parts.push(`
    <div class="chain-edge"><span class="muted">闭合回到</span><span class="chain-arrow">⟲</span></div>
    <div class="chain-node">${esc(c.closes_to)}</div>`);
  return `<div class="chain">${parts.join("")}</div>`;
}

function renderItineraryOk(data) {
  const segRows = data.segments.map((s) => {
    const lines = (s.interval_lines || []).map((ln) => {
      const ok = ln.satisfied ? '<span class="ok-text">满足</span>' : '<span style="color:var(--err)">不满足</span>';
      return `<div>第 ${ln.line} 行 [${ln.low}, ${ln.high}]（${esc(ln.a)}→${esc(ln.b)}）：${ok}</div>`;
    }).join("");
    const placePair = s.same_place
      ? `<span class="seg-sameplace">同地点 · 0 分</span>`
      : `${esc(s.from_place)} → ${esc(s.to_place)}`;
    return `<tr>
      <td class="num">第 ${s.index} 段</td>
      <td>${esc(s.from_event)} → ${esc(s.to_event)}</td>
      <td>${placePair}</td>
      <td class="num">${s.travel_minutes}</td>
      <td class="num">${s.actual_minutes}</td>
      <td class="num">+${s.slack_minutes}</td>
      <td>${lines || '<span class="muted">无直接对应区间行</span>'}</td>
    </tr>`;
  }).join("");

  const maxMinute = Math.max(...data.timeline.map((t) => t.minute));
  const points = data.ordered_itinerary.map((o) => `
    <div class="tl-point">
      <div class="tl-dot"></div>
      <div class="tl-name">${esc(o.event)}</div>
      <div class="tl-time">第 ${o.minute} 分钟 · ${esc(o.place)}</div>
    </div>`).join("");

  itineraryEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 行程可达：时间差区间与通行下界全部相容</h2>
      <p>${esc(data.message)}</p>
    </div>
    <div class="card">
      <h3>按发生顺序的可行时间线</h3>
      <div class="timeline-track">
        <div class="tl-line"></div>
        <div class="tl-grid">${points}</div>
      </div>
      ${itineraryTimelineTableHtml(data.timeline)}
      <p class="muted">时间跨度 0 ~ ${maxMinute} 分钟；所有事件可整体平移，时间差与通行下界不变。</p>
    </div>
    <div class="card">
      <h3>各事件段：最短通行 vs 时间线间隔</h3>
      <table>
        <thead><tr>
          <th class="num">事件段</th><th>事件对</th><th>地点对</th>
          <th class="num">最短通行</th><th class="num">实际间隔</th><th class="num">富余</th>
          <th>覆盖该段的原区间行</th>
        </tr></thead>
        <tbody>${segRows}</tbody>
      </table>
    </div>
    <div class="card">
      <h3>各事件段总览</h3>
      ${itinerarySegmentsTableHtml(data.segments, { withActual: true })}
    </div>
    <h3 style="margin:18px 0 8px">各段最短路线（含逐路段明细）</h3>
    ${itineraryRouteCardsHtml(data.segments)}`;
}

function renderItineraryUnreachable(data) {
  itineraryEl.innerHTML = `
    <div class="banner err">
      <h2>✗ 存在无路可达的事件段</h2>
      <p>${esc(data.message)}</p>
      <p style="margin-top:6px">无路可达的是：<strong>${data.unreachable_segments.map((i) => `第 ${i} 段`).join("、")}</strong>。
      通行路段为<strong>有向</strong>（只有“起点→终点”单向），请补充对应方向的路段，或核对地点名称是否一致；
      在全部相邻事件段可达之前，不进行时间冲突联立。</p>
    </div>
    <div class="card">
      <h3>各事件段可达性总览</h3>
      ${itinerarySegmentsTableHtml(data.segments)}
    </div>
    ${itineraryRouteCardsHtml(data.segments)}`;
}

function renderItineraryConflict(data) {
  const c = data.conflict;
  const segBadges = (data.travel_step_segments || []).map((i) => `第 ${i} 段`).join("、");
  const detailRows = c.steps.map((s) => {
    let ref;
    let extra = "";
    if (s.kind === "travel") {
      ref = `事件段 ${s.segment}`;
      const routeDesc = s.route.length
        ? s.route.map((r) => `${esc(r.from)}→${esc(r.to)}（${r.minutes}分·路段第${r.line}行）`).join("，")
        : "同地点零分钟";
      extra = `<td class="muted">${esc(s.from_event)}（${esc(s.from_place)}）→ ${esc(s.to_event)}（${esc(s.to_place)}）；最短路线：${routeDesc}，合计 ${s.travel_minutes} 分钟</td>`;
    } else {
      ref = stepLineRef(s);
      extra = `<td class="muted">${esc(s.relation)}</td>`;
    }
    return `<tr>
      <td class="num">${ref}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${esc(stepBoundText(s))}</td>
      ${extra}
    </tr>`;
  }).join("");

  itineraryEl.innerHTML = `
    <div class="banner conflict">
      <h2>✗ 行程时间冲突（通行下界 × 原区间）</h2>
      <p>${esc(data.message)}</p>
      <p style="margin-top:6px">矛盾链中的通行下界来自事件段：<strong>${esc(segBadges || "（无）")}</strong>；
      环上界值相加为 <strong>${c.weight_sum} &lt; 0</strong>，意味着“走完这段路所需时间”与某些区间叙述无法同时成立。</p>
    </div>
    <div class="card">
      <h3>闭合矛盾链（含原区间行号、事件段与最短路线）</h3>
      ${itineraryConflictChainHtml(c)}
    </div>
    <div class="card">
      <h3>矛盾依据明细</h3>
      <table>
        <thead><tr>
          <th class="num">来源（区间行 / 事件段）</th><th>图中方向</th><th>使用的界</th>
          <th class="num">界值（分钟）</th><th>含义 / 事件段最短路线</th>
        </tr></thead>
        <tbody>${detailRows}</tbody>
      </table>
      <p class="muted">“通行下界”取该事件段在地点网络中的最短通行分钟（同地点为 0）；“上界/下界”取自上方
      时间差区间文本的原始行号。各事件段的完整最短路线见下方卡片。</p>
    </div>
    <div class="card">
      <h3>各事件段可达性与最短通行</h3>
      ${itinerarySegmentsTableHtml(data.segments)}
    </div>
    ${itineraryRouteCardsHtml(data.segments)}`;
}

function renderItineraryIntervalConflict(data) {
  itineraryEl.innerHTML = `
    <div class="banner err">
      <h2>✗ 时间差区间自身矛盾</h2>
      <p>${esc(data.message)}</p>
    </div>`;
  renderConflict({ conflict: data.conflict }, itineraryEl);
  itineraryEl.insertAdjacentHTML("beforeend", `
    <div class="card">
      <h3>各事件段可达性与最短通行（仅供参考，未参与上述联立）</h3>
      ${itinerarySegmentsTableHtml(data.segments)}
    </div>
    ${itineraryRouteCardsHtml(data.segments)}`);
}

async function checkItinerary() {
  itineraryEl.innerHTML = `<div class="card muted">求各段最短通行并联立中…</div>`;
  try {
    const resp = await fetch("/api/itinerary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: inputEl.value,
        places: itineraryPlacesEl.value,
        routes: itineraryRoutesEl.value,
        itinerary: itineraryOrderEl.value,
      }),
    });
    const data = await resp.json();
    if (data.status === "ok") renderItineraryOk(data);
    else if (data.status === "unreachable") renderItineraryUnreachable(data);
    else if (data.status === "conflict") renderItineraryConflict(data);
    else if (data.status === "interval_conflict") renderItineraryIntervalConflict(data);
    else renderErrors(data.errors || [{ line: null, message: "未知错误。" }], itineraryEl);
  } catch (err) {
    itineraryEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-itinerary").addEventListener("click", checkItinerary);
$("btn-itinerary-example-ok").addEventListener("click", () => {
  inputEl.value = EXAMPLE_ITINERARY_OK_TEXT;
  itineraryPlacesEl.value = EXAMPLE_ITINERARY_OK_PLACES;
  itineraryRoutesEl.value = EXAMPLE_ITINERARY_OK_ROUTES;
  itineraryOrderEl.value = EXAMPLE_ITINERARY_OK_ORDER;
  refreshLineOptions();
  checkItinerary();
});
$("btn-itinerary-example-conflict").addEventListener("click", () => {
  inputEl.value = EXAMPLE_ITINERARY_CONFLICT_TEXT;
  itineraryPlacesEl.value = EXAMPLE_ITINERARY_OK_PLACES;
  itineraryRoutesEl.value = EXAMPLE_ITINERARY_OK_ROUTES;
  itineraryOrderEl.value = EXAMPLE_ITINERARY_OK_ORDER;
  refreshLineOptions();
  checkItinerary();
});
$("btn-itinerary-example-unreach").addEventListener("click", () => {
  inputEl.value = EXAMPLE_ITINERARY_OK_TEXT;
  itineraryPlacesEl.value = EXAMPLE_ITINERARY_OK_PLACES;
  itineraryRoutesEl.value = EXAMPLE_ITINERARY_UNREACH_ROUTES;
  itineraryOrderEl.value = EXAMPLE_ITINERARY_OK_ORDER;
  refreshLineOptions();
  checkItinerary();
});
$("btn-itinerary-clear").addEventListener("click", () => {
  itineraryPlacesEl.value = "";
  itineraryRoutesEl.value = "";
  itineraryOrderEl.value = "";
  itineraryEl.innerHTML = "";
  itineraryPlacesEl.focus();
});
// 地点 / 路段 / 行程顺序任一变化，旧的行程结论立即作废
[itineraryPlacesEl, itineraryRoutesEl, itineraryOrderEl].forEach((el) => {
  el.addEventListener("input", () => { itineraryEl.innerHTML = ""; });
});

// ---------- 有序事件最大统一间隔 ----------

// 顺序间隔步骤的标签渲染（矛盾链 tag）：标注相邻对序号与统一间隔下界
function maxgapStepTagHtml(s) {
  if (s.kind === "order") {
    return `<span class="tag order">顺序第 ${s.position} 对 · 间隔 ≥ ${s.bound}</span>`;
  }
  return `<span class="tag ${s.kind}">${stepLineRef(s)} · ${esc(s.kind_label)} ${esc(stepBoundText(s))}</span>`;
}

// 顺序冲突的闭合矛盾链：在通用矛盾链图基础上，顺序间隔环节标注相邻对序号
function maxgapConflictChainHtml(c) {
  const parts = [];
  c.steps.forEach((s, i) => {
    if (i === 0) parts.push(`<div class="chain-node">${esc(s.from)}</div>`);
    parts.push(`
      <div class="chain-edge">
        ${maxgapStepTagHtml(s)}
        <span class="rel">${esc(s.relation)}</span>
        <span class="chain-arrow">→</span>
      </div>
      <div class="chain-node">${esc(s.to)}</div>`);
  });
  parts.push(`
    <div class="chain-edge"><span class="muted">闭合回到</span><span class="chain-arrow">⟲</span></div>
    <div class="chain-node">${esc(c.closes_to)}</div>`);
  return `<div class="chain">${parts.join("")}</div>`;
}

// 可行时间线卡片（链式图 + 分钟表；达到 g 或 g=0 的完整时间线共用）
function maxgapTimelineCardHtml(data, title) {
  const maxMinute = Math.max(...data.timeline.map((t) => t.minute));
  const points = data.timeline.map((t) => `
    <div class="tl-point">
      <div class="tl-dot"></div>
      <div class="tl-name">${esc(t.event)}</div>
      <div class="tl-time">第 ${t.minute} 分钟</div>
    </div>`).join("");
  const rows = data.timeline.map((t) =>
    `<tr><td>${esc(t.event)}</td><td class="num">${t.minute}</td></tr>`).join("");
  return `
    <div class="card">
      <h3>${esc(title)}</h3>
      <div class="timeline-track">
        <div class="tl-line"></div>
        <div class="tl-grid">${points}</div>
      </div>
      <table>
        <thead><tr><th>事件</th><th class="num">分钟（最早事件 = 0）</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">时间跨度：0 ~ ${maxMinute} 分钟。所有事件可整体平移，差值不变。</p>
    </div>`;
}

// 相邻所选事件间隔核对表：每对实际间隔与统一间隔要求（g 或 0）
function maxgapGapsCardHtml(data) {
  const rows = data.gaps.map((p) => {
    const ok = p.actual >= data.timeline_g;
    return `<tr>
      <td class="num">第 ${p.position} 对</td>
      <td>${esc(p.from)} → ${esc(p.to)}</td>
      <td class="num">${p.actual}</td>
      <td class="num">≥ ${data.timeline_g}</td>
      <td>${ok ? '<span class="ok-text">满足</span>' : '<span style="color:var(--err)">不满足</span>'}</td>
    </tr>`;
  }).join("");
  return `
    <div class="card">
      <h3>相邻所选事件间隔核对</h3>
      <table>
        <thead><tr>
          <th class="num">相邻对</th><th>顺序（先 → 后）</th>
          <th class="num">本时间线间隔</th><th class="num">统一间隔要求</th><th>结果</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">所选顺序：${data.order.map((n) => esc(n)).join(" → ")}。</p>
    </div>`;
}

// 原区间逐条核对表（与联立核对同口径，时间线为加入顺序间隔后的可行解）
function maxgapDifferencesCardHtml(data) {
  const rows = data.differences.map((d) => {
    const fit = d.low <= d.actual && d.actual <= d.high;
    return `<tr>
      <td class="num">${d.line}</td>
      <td>${esc(d.a)} → ${esc(d.b)}</td>
      <td class="num">[${d.low}, ${d.high}]</td>
      <td class="num">${d.actual}</td>
      <td>${fit ? '<span class="ok-text">满足</span>' : '<span style="color:var(--err)">不满足</span>'}</td>
    </tr>`;
  }).join("");
  return `
    <div class="card">
      <h3>原区间逐条核对</h3>
      <table>
        <thead><tr>
          <th class="num">行号</th><th>事件对</th><th class="num">要求区间</th>
          <th class="num">本时间线差值</th><th>结果</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderMaxgapOk(data) {
  maxgapEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 最大统一间隔 g = ${data.g} 分钟</h2>
      <p>${esc(data.message)}</p>
    </div>
    ${maxgapGapsCardHtml(data)}
    ${maxgapTimelineCardHtml(data, `达到 g = ${data.g} 分钟的完整可行时间线`)}
    ${maxgapDifferencesCardHtml(data)}`;
}

function renderMaxgapUnbounded(data) {
  maxgapEl.innerHTML = `
    <div class="banner ok">
      <h2>✓ 统一间隔无上限</h2>
      <p>${esc(data.message)}</p>
    </div>
    ${maxgapGapsCardHtml(data)}
    ${maxgapTimelineCardHtml(data, "g = 0 的可行时间线（保持先后顺序）")}
    ${maxgapDifferencesCardHtml(data)}`;
}

function renderMaxgapOrderConflict(data) {
  const c = data.conflict;
  const detailRows = c.steps.map((s) => {
    const ref = s.kind === "order" ? `顺序第 ${s.position} 对` : stepLineRef(s);
    const bound = s.kind === "order" ? String(s.bound) : stepBoundText(s);
    return `<tr>
      <td class="num">${ref}</td>
      <td>${esc(s.from)} → ${esc(s.to)}</td>
      <td><span class="tag ${s.kind}">${esc(s.kind_label)}</span></td>
      <td class="num">${esc(bound)}</td>
      <td>${esc(s.relation)}</td>
    </tr>`;
  }).join("");

  maxgapEl.innerHTML = `
    <div class="banner conflict">
      <h2>✗ 顺序冲突：连 g=0 都无法保持所选先后</h2>
      <p>${esc(data.message)}</p>
      <p style="margin-top:6px">环上界值相加为 <strong>${c.weight_sum} &lt; 0</strong>：
      请调整所选事件的先后顺序，或先修订与之冲突的区间行。</p>
    </div>
    <div class="card">
      <h3>闭合矛盾链（含顺序间隔环节）</h3>
      ${maxgapConflictChainHtml(c)}
    </div>
    <div class="card">
      <h3>矛盾依据明细</h3>
      <table>
        <thead><tr>
          <th class="num">来源（区间行 / 顺序对）</th><th>图中方向</th><th>使用的界</th>
          <th class="num">界值</th><th>含义</th>
        </tr></thead>
        <tbody>${detailRows}</tbody>
      </table>
      <p class="muted">“顺序间隔”取第 N 对相邻所选事件的统一间隔下界（g=0 时仅要求保持先后）；
      “上界/下界”取自上方时间差区间文本的原始行号。</p>
    </div>`;
}

// 原区间自身矛盾：沿用现有闭合矛盾链渲染（链图 + 涉及原始行明细表）
function renderMaxgapIntervalConflict(data) {
  maxgapEl.innerHTML = `
    <div class="banner err">
      <h2>✗ 时间差区间自身矛盾</h2>
      <p>${esc(data.message)}</p>
    </div>
    <div id="maxgap-interval-conflict-body"></div>`;
  renderConflict({ conflict: data.conflict }, $("maxgap-interval-conflict-body"));
}

async function queryMaxgap() {
  maxgapEl.innerHTML = `<div class="card muted">联立求最大统一间隔中…</div>`;
  try {
    const resp = await fetch("/api/max-gap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputEl.value, order: maxgapOrderEl.value }),
    });
    const data = await resp.json();
    if (data.status === "ok") renderMaxgapOk(data);
    else if (data.status === "unbounded") renderMaxgapUnbounded(data);
    else if (data.status === "order_conflict") renderMaxgapOrderConflict(data);
    else if (data.status === "interval_conflict") renderMaxgapIntervalConflict(data);
    else renderErrors(data.errors || [{ line: null, message: "未知错误。" }], maxgapEl);
  } catch (err) {
    maxgapEl.innerHTML = `
      <div class="banner err"><h2>请求失败</h2><p>${esc(err.message)}</p></div>`;
  }
}

$("btn-maxgap").addEventListener("click", queryMaxgap);
$("btn-maxgap-example-ok").addEventListener("click", () => {
  inputEl.value = EXAMPLE_OK;  // 有界示例配合可行示例区间演示（g = 75）
  maxgapOrderEl.value = EXAMPLE_MAXGAP_OK_ORDER;
  refreshLineOptions();
  queryMaxgap();
});
$("btn-maxgap-example-unbounded").addEventListener("click", () => {
  inputEl.value = EXAMPLE_MAXGAP_UNBOUNDED_TEXT;
  maxgapOrderEl.value = EXAMPLE_MAXGAP_UNBOUNDED_ORDER;
  refreshLineOptions();
  queryMaxgap();
});
$("btn-maxgap-example-conflict").addEventListener("click", () => {
  inputEl.value = EXAMPLE_MAXGAP_CONFLICT_TEXT;
  maxgapOrderEl.value = EXAMPLE_MAXGAP_CONFLICT_ORDER;
  refreshLineOptions();
  queryMaxgap();
});
$("btn-maxgap-clear").addEventListener("click", () => {
  maxgapOrderEl.value = "";
  maxgapEl.innerHTML = "";
  maxgapOrderEl.focus();
});
maxgapOrderEl.addEventListener("input", () => {
  maxgapEl.innerHTML = "";  // 顺序已变，旧的最大统一间隔结论作废
});
