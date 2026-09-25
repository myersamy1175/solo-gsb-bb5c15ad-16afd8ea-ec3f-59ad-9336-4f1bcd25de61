"""差分约束求解：联立事件时间差区间，检测矛盾并给出可行时间线。

事件别名归并核对（solve_aliases）：别名文本每行“事件名,同一事件的另一名称”，
并查集按传递关系把名称归为同一事件（A=B、B=C ⇒ A、B、C 同组）；每组取区间文本中
最先出现的名称作统一事件名，把区间行两端替换为统一事件名后复用同一套差分约束
Bellman-Ford 联立。同组内的区间（两端归并为同一事件）成为自环约束照常参与判定：
要求 0 落在该行区间内，否则构成负环。冲突时闭合矛盾链保留原始区间行号，并附
别名组（每组原名称）与每一步的原始事件名；可解时返回按统一事件归并的时间线，
每个节点附该组原名称。

每条输入行：事件甲, 事件乙, 最少分钟 lo, 最多分钟 hi
含义：lo <= t(乙) - t(甲) <= hi

改写为标准差分约束（最短路）形式：
    t(乙) - t(甲) <= hi        -> 边 甲 -> 乙，权 hi（上界）
    t(甲) - t(乙) <= -lo       -> 边 乙 -> 甲，权 -lo（下界）

引入指向所有事件、权为 0 的虚拟源（实现上等价于把所有距离初始化为 0），
用 Bellman-Ford 判定：第 N 轮仍可松弛 => 存在负环，即区间互相矛盾。

约束冗余核对（check_redundancy）：删去所选行对应的上、下界两条边后，
在其余约束构成的图上分别求 甲->乙 与 乙->甲 的单源最短路：
    甲->乙 最短路 = 其余约束能推出的 t(乙)-t(甲) 最紧上界（不可达则无界）
    乙->甲 最短路取负 = 其余约束能推出的 t(乙)-t(甲) 最紧下界（不可达则无界）
仅当推导区间 [下界, 上界] 完全落在所选行区间 [lo, hi] 内时判为“可删”。

两版比较（compare_texts）：基准文本与修订文本各自独立 parse_text + solve_rows，
任一版校验失败或存在负环时，分别原样带上该版错误/闭合矛盾链，不生成差异结论；
两版均可解时，以“最早事件第 0 分钟”的规范化时刻按事件名对齐，列出共同事件的
两版时刻与变化分钟数，并用 _derive_bound 复用冗余核对同款最短路推导，
把推出修订时刻的修订行（原始行号、所用界值）作为变化证据；同时给出新增、删除事件。

冲突单行修订建议（suggest_repairs）：文本语法有效但联立矛盾时，逐行暂时移除该行的
上、下界约束；其余行仍矛盾的行排除，其余可解时用冗余核对同款最短路求这两个事件
时间差的最紧可行区间，只放宽该行一个端点至首次相交的整数分钟（区间含整数端点，
最小改动即“移到边界”），给出最小改动量、替换后的整行，以及迫使该端点移动的
原始行号与界值推导链；建议按改动分钟数、原始行号排序，无单行修复时明确提示。

绝对时间锚定（solve_anchored）：每条锚点行“事件名,YYYY-MM-DD HH:MM”按同一无时区
本地时间换算为相对统一零点（公历 0001-01-01 00:00）的分钟数 M，引入零点节点 ZERO
与一对等式边（ZERO->事件 权 M、事件->ZERO 权 -M，即“事件相对零点的等式”），与区间行
复用同一套差分约束 Bellman-Ford 联立；同名锚点重复也作为两条等式参与判定（时刻不同
即构成负环）。冲突时闭合矛盾链同时标注区间行号、锚点行号及所用界值；可解时不取任何
任意平移的可行解充当真实日期，而是对每个事件用冗余核对同款单源最短路求其相对零点的
最紧下界/上界：仅与锚点连通（两端都有界）的事件给出绝对日期时刻（精确点或范围），
其余事件标为“未定位”。

互斥说法下的先后查询（solve_precedence）：共同约束沿用事件区间文本；候选组每行
“区间A | 区间B”表示两条只能选一条的互斥说法（最多 6 行，两侧复用区间行格式与同款
字段校验）。枚举全部 2^N 个“每组选一侧”的组合，分别与共同约束联立（同一套差分约束
Bellman-Ford），存在负环的组合判为冲突并排除；对每个可行组合复用冗余核对同款
_derive_bound 求 t(乙) − t(甲) 的最紧下界/上界（推不出的端点为无界），再跨组合合并：
下界取各组合最小值、上界取各组合最大值，任一组合对应端无界则合并端无界。
合并下界 ≥ 1 分钟判“甲始终先于乙”，合并上界 ≤ −1 分钟判“甲始终后于乙”，否则判
“不确定”；无可行组合时不作先后判断。查询的甲、乙必须出现在共同约束中。

最少撤回（find_minimum_withdrawals）：复用 parse_text 与同一套差分约束 Bellman-Ford，
输入为现有区间格式文本（非空行最多 MAX_WITHDRAWAL_LINES=10 条，超限明确报错）。
空约束集（空文本）视为可行，直接返回零撤回方案与空时间线；原文已可行时同样返回
零撤回方案。否则按撤回行数 k=1,2,… 递增枚举 C(n,k) 个原始行号组合，第一个存在可行
剩余子集的 k 即最少撤回数，返回该层全部可行组合（每个方案附剩余约束的一条规范化
可行时间线，撤回全部行时时间线为空）；语法错误逐行返回。

行程可达性核对（check_itinerary）：区间文本沿用现有时间差区间（可留空），另有逐行
“事件,地点”、有向路段“起点,终点,分钟”（非负分钟，重复有向路段取最短）与按发生顺序
排列的事件名（每行一个、互不相同）。先对四类文本逐行校验（重复事件地点、缺失事件
地点、重复行程事件、负通行时间等），再对每对相邻行程事件在地点网络上用 Dijkstra 求
最短通行时间（边权非负；同地点按零分钟）；等距离路线按节点序列字典序与路段行号决胜，
保证结果确定。无路可达的相邻事件段逐段指出且不联立；可达时把每个
“后一事件 − 前一事件 ≥ 最短通行分钟”作为通行下界边（b -> a，权 -d）与原区间一起
跑同一套 Bellman-Ford：负环还原的闭合矛盾链同时含原始区间行号与通行下界环节
（标注事件段序号、地点对及最短路线）；可行时平移到最早事件为第 0 分钟，给出一条满足
全部区间与通行下界的时间线，并逐段给出最短路线、所需分钟、实际间隔与富余。

有序事件最大统一间隔（solve_max_gap）：沿用首页事件区间，另逐行输入至少两个互不重复、
已在区间中出现的事件名，表示希望保持的先后顺序。对给定的非负整数 g，为每对相邻所选
事件（前一事件 a、后一事件 b）加一条间隔下界边 b -> a、权 -g（即 t(b) − t(a) ≥ g），
与原区间复用同一套差分约束 Bellman-Ford 联立。原区间语法错误或自身矛盾时沿用现有
错误或闭合矛盾链（不混入间隔边）；原区间可行但 g=0 已不可行时判顺序冲突，返回含
顺序间隔环节（标注相邻对序号）的闭合矛盾链；没有任何间隔边落在环上（原区间对这些
间隔给不出上界）时 g 无有限上限，给出 g=0 的可行时间线；否则先指数放大再二分求出
最大的可行整数 g，返回 g 与一条达到该间隔、平移到最早事件为第 0 分钟的完整可行时间线。
"""

from __future__ import annotations

import heapq
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import combinations, product

_INT_RE = re.compile(r"^[+-]?\d+$")

# 绝对时间锚定：统一零点（无时区本地时间）与图中零点节点的内部名。
# 内部名以 \x00 开头，用户事件名不可能与之撞名；对外展示统一映射为 ZERO_DISPLAY。
ZERO_DT = datetime(1, 1, 1, 0, 0)
ZERO_NODE = "\x00zero"
ZERO_DISPLAY = "统一零点"

# 锚点日期时间格式：YYYY-MM-DD HH:MM（允许任意空白分隔日期与时刻）
_ANCHOR_DT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})$")


def _display_name(name: str) -> str:
    """图中内部节点名转对外显示名（零点节点显示为“统一零点”）。"""
    return ZERO_DISPLAY if name == ZERO_NODE else name


@dataclass(frozen=True)
class Row:
    line: int
    a: str
    b: str
    low: int
    high: int


@dataclass(frozen=True)
class Edge:
    u: int
    v: int
    w: int
    line: int
    kind: str  # "upper"（上界边）、"lower"（下界边）、"anchor"（锚点等式边）、"travel"（通行下界边）或 "order"（顺序间隔边）
    bound: int  # 原始行中的界值（上界为 high，下界为 low；锚点边为相对零点的分钟数）
    source: str = "interval"  # "interval"（区间行）或 "anchor"（锚点行）
    label: str = ""  # 锚点边展示用的日期时刻文本（YYYY-MM-DD HH:MM）


@dataclass(frozen=True)
class Anchor:
    line: int
    event: str
    minute: int  # 相对统一零点 ZERO_DT 的分钟数
    text: str  # 规范化后的日期时刻文本（YYYY-MM-DD HH:MM）


@dataclass(frozen=True)
class Claim:
    line: int  # 候选组文本的原始行号
    side: str  # "A" 或 "B"：该组互斥说法的左/右侧
    a: str
    b: str
    low: int
    high: int


@dataclass(frozen=True)
class Alias:
    line: int  # 别名文本的原始行号
    a: str
    b: str


@dataclass(frozen=True)
class PlaceRow:
    line: int  # 地点文本的原始行号
    event: str
    place: str


@dataclass(frozen=True)
class RouteRow:
    line: int  # 路段文本的原始行号
    src: str
    dst: str
    minutes: int


# 互斥说法候选组最多行数：每行二选一，组合数为 2 的幂，限制行数保证枚举耗时可控
MAX_GROUP_LINES = 6


def _validate_interval_fields(a: str, b: str, low_s: str, high_s: str) -> tuple[int | None, int | None, list[str]]:
    """校验一条区间的四个字段：事件名非空、上下界为整数分钟、下界不大于上界。

    返回 (low, high, 错误片段列表)；有错误时 low/high 可能为 None，调用方应忽略。
    共同约束行与互斥说法候选组两侧共用同一套校验与措辞。
    """
    errors: list[str] = []
    if not a:
        errors.append("事件甲名称为空")
    if not b:
        errors.append("事件乙名称为空")

    low: int | None = None
    high: int | None = None
    if _INT_RE.match(low_s):
        low = int(low_s)
    else:
        errors.append(f"最少分钟必须是整数分钟，得到 “{low_s}”")
    if _INT_RE.match(high_s):
        high = int(high_s)
    else:
        errors.append(f"最多分钟必须是整数分钟，得到 “{high_s}”")

    if low is not None and high is not None and low > high:
        errors.append(f"下界 {low} 大于上界 {high}，时间差区间为空")
    return low, high, errors


def parse_text(text: str) -> tuple[list[Row], list[dict]]:
    """按行解析与校验。返回 (有效行, 错误列表)。"""
    errors: list[dict] = []
    rows: list[Row] = []

    if not text or not text.strip():
        return rows, [{"line": None, "message": "输入为空：请粘贴“事件甲,事件乙,最少分钟,最多分钟”格式的多行文本。"}]

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为原始行号

        # 兼容中文逗号
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) != 4:
            errors.append({
                "line": line_no,
                "message": f"第{line_no}行：应为 4 个字段（事件甲,事件乙,最少分钟,最多分钟），实际得到 {len(parts)} 个。",
            })
            continue

        a, b, low_s, high_s = parts
        low, high, row_errors = _validate_interval_fields(a, b, low_s, high_s)
        if row_errors:
            errors.append({"line": line_no, "message": f"第{line_no}行：" + "；".join(row_errors) + "。"})
            continue

        rows.append(Row(line_no, a, b, low, high))  # type: ignore[arg-type]

    return rows, errors


def _edge_step(names: list[str], e: Edge) -> dict:
    """把一条约束边还原为可读步骤：来源（区间行/锚点行）、原始行号、方向、所用界与界值。"""
    if e.kind == "anchor":
        # 锚点等式边：ZERO->事件 权 M（不晚于锚定时刻）或 事件->ZERO 权 -M（不早于锚定时刻）
        if names[e.u] == ZERO_NODE:
            relation = f"{names[e.v]} 不晚于 {e.label}（锚定时刻）"
        else:
            relation = f"{names[e.u]} 不早于 {e.label}（锚定时刻）"
        return {
            "from": _display_name(names[e.u]),
            "to": _display_name(names[e.v]),
            "weight": e.w,
            "line": e.line,
            "kind": e.kind,
            "kind_label": "锚点",
            "bound": e.bound,
            "source": "anchor",
            "anchor_time": e.label,
            "relation": relation,
        }
    if e.kind == "upper":
        relation = f"{names[e.v]}−{names[e.u]} ≤ {e.bound}"
        kind_label = "上界（最多）"
    else:
        # 边 v -> u、权 -low 对应 names[v]−names[u] >= low，即 u 事件比 v 事件早至少 low
        relation = f"{names[e.u]}−{names[e.v]} ≥ {e.bound}"
        kind_label = "下界（最少）"
    return {
        "from": _display_name(names[e.u]),
        "to": _display_name(names[e.v]),
        "weight": e.w,
        "line": e.line,
        "kind": e.kind,
        "kind_label": kind_label,
        "bound": e.bound,
        "source": "interval",
        "relation": relation,
    }


def _build_graph(rows: list[Row]) -> tuple[list[str], dict[str, int], list[Edge]]:
    """事件按首次出现顺序编号，并把每行转换为上界、下界两条边。"""
    names: list[str] = []
    index: dict[str, int] = {}
    for r in rows:
        for name in (r.a, r.b):
            if name not in index:
                index[name] = len(names)
                names.append(name)

    edges: list[Edge] = []
    for r in rows:
        ia, ib = index[r.a], index[r.b]
        edges.append(Edge(ia, ib, r.high, r.line, "upper", r.high))
        edges.append(Edge(ib, ia, -r.low, r.line, "lower", r.low))
    return names, index, edges


def _relax_all(names: list[str], edges: list[Edge]) -> tuple[list[int], list[tuple[int, Edge] | None], int | None]:
    """全源 Bellman-Ford：所有距离初始化为 0（等价于虚拟源向每个顶点连权 0 的边）。

    返回 (dist, pred, last_relaxed)；last_relaxed 非 None 表示第 N 轮仍可松弛，即存在负环。
    """
    n = len(names)
    dist = [0] * n
    pred: list[tuple[int, Edge] | None] = [None] * n
    last_relaxed: int | None = None

    # Bellman-Ford：共 N 轮，第 N 轮仍可松弛 => 存在负环
    for iteration in range(n):
        relaxed = False
        for e in edges:
            cand = dist[e.u] + e.w
            if cand < dist[e.v]:
                dist[e.v] = cand
                pred[e.v] = (e.u, e)
                relaxed = True
                if iteration == n - 1:
                    last_relaxed = e.v
        if not relaxed:
            break
    return dist, pred, last_relaxed


def solve_rows(rows: list[Row]) -> dict:
    """对已通过校验的行联立 Bellman-Ford，返回内部求解结构（供 solve / 冗余核对 / 两版比较复用）。

    成功时含 rows/names/index/edges/dist/minutes（minutes 已平移到最早事件为 0）；
    存在负环时直接返回 _conflict_result 的公开矛盾链结构。
    没有任何行（空约束集）时无任何边，天然可行，返回空图与空时间线。
    """
    names, index, edges = _build_graph(rows)
    if not names:
        # 空约束集：无事件无边，任意时间线都可行（最少撤回时撤回全部行会走到这里）
        return {
            "status": "ok",
            "rows": rows,
            "names": names,
            "index": index,
            "edges": edges,
            "dist": [],
            "minutes": [],
        }
    dist, pred, last_relaxed = _relax_all(names, edges)

    if last_relaxed is not None:
        return _conflict_result(names, pred, last_relaxed, len(names))

    # 平移使最早事件落在第 0 分钟（差值不变，约束全部保留）
    base = min(dist)
    minutes = [dist[i] - base for i in range(len(names))]
    return {
        "status": "ok",
        "rows": rows,
        "names": names,
        "index": index,
        "edges": edges,
        "dist": dist,
        "minutes": minutes,
    }


def _format_ok(system: dict) -> dict:
    """把 solve_rows 的内部成功结构转为 /api/solve 的公开返回格式。"""
    names = system["names"]
    minutes = system["minutes"]
    rows = system["rows"]
    index = system["index"]
    dist = system["dist"]

    timeline = [
        {"event": names[i], "minute": minutes[i]}
        for i in range(len(names))
    ]
    timeline.sort(key=lambda x: (x["minute"], x["event"]))

    differences = [
        {
            "line": r.line,
            "a": r.a,
            "b": r.b,
            "low": r.low,
            "high": r.high,
            "actual": dist[index[r.b]] - dist[index[r.a]],
        }
        for r in rows
    ]

    return {
        "status": "ok",
        "timeline": timeline,
        "differences": differences,
        "event_count": len(names),
        "line_count": len(rows),
    }


def _parse_and_solve(text: str) -> tuple[list[Row], dict]:
    """解析校验一版文本并联立。成功返回 solve_rows 内部结构，否则返回公开错误结构。"""
    rows, errors = parse_text(text)
    if errors:
        return rows, {"status": "error", "errors": errors}
    if not rows:
        return rows, {
            "status": "error",
            "errors": [{"line": None, "message": "没有可联立的有效约束行。"}],
        }
    return rows, solve_rows(rows)


def solve(text: str) -> dict:
    _, result = _parse_and_solve(text)
    return _format_ok(result) if result["status"] == "ok" else result


def _extract_cycle_edges(pred, start: int, n: int) -> list[tuple[int, Edge]]:
    """从第 N 轮仍被松弛的顶点出发，沿前驱找回负环，返回正向（u -> v）的环边序列。"""
    x = start
    for _ in range(n):
        step = pred[x]
        if step is None:
            break
        x = step[0]

    cycle_edges: list[tuple[int, Edge]] = []
    seen: set[int] = set()
    cur = x
    while cur not in seen:
        seen.add(cur)
        step = pred[cur]
        if step is None:
            break
        pu, e = step
        cycle_edges.append((pu, e))
        cur = pu

    # 沿前驱收集是逆序的，翻转回边的正向（u -> v）
    cycle_edges.reverse()
    return cycle_edges


def _conflict_result(names: list[str], pred, start: int, n: int, step_builder=_edge_step) -> dict:
    """从前驱链还原负环并转为原始行构成的矛盾链。

    step_builder 决定每条边如何映射为可读步骤（区间/锚点边用 _edge_step，
    行程可达性核对中含通行下界边时用自定义构建器）。
    """
    cycle_edges = _extract_cycle_edges(pred, start, n)
    steps = [step_builder(names, e) for _, e in cycle_edges]

    total = sum(s["weight"] for s in steps)
    return {
        "status": "conflict",
        "conflict": {
            "steps": steps,
            "weight_sum": total,
            "closes_to": steps[0]["from"] if steps else None,
        },
    }


def _bellman_ford(names: list[str], edges: list[Edge], source: int) -> tuple[list[int | None], list[tuple[int, Edge] | None]]:
    """单源最短路（调用前已确认无负环）。不可达顶点的距离为 None。"""
    n = len(names)
    dist: list[int | None] = [None] * n
    dist[source] = 0
    pred: list[tuple[int, Edge] | None] = [None] * n

    for _ in range(n - 1):
        relaxed = False
        for e in edges:
            du = dist[e.u]
            if du is None:
                continue
            cand = du + e.w
            if dist[e.v] is None or cand < dist[e.v]:
                dist[e.v] = cand
                pred[e.v] = (e.u, e)
                relaxed = True
        if not relaxed:
            break
    return dist, pred


def _derive_bound(names: list[str], edges: list[Edge], source: int, target: int) -> tuple[int | None, list[dict]]:
    """t(target) − t(source) 的最紧上界及其推导路径（source -> target 最短路）。

    返回 (上界, 路径步骤)；不可达时上界为 None、路径为空（该端点标为无界）。
    source == target 时上界为 0、路径为空（同一事件时间差恒为 0）。
    """
    dist, pred = _bellman_ford(names, edges, source)
    if dist[target] is None:
        return None, []

    path_edges: list[Edge] = []
    cur = target
    while cur != source:
        step = pred[cur]
        if step is None:  # 不可达时不会走到这里，防御性退出
            break
        pu, e = step
        path_edges.append(e)
        cur = pu
    path_edges.reverse()
    return dist[target], [_edge_step(names, e) for e in path_edges]


def check_redundancy(text: str, line: int) -> dict:
    """约束冗余核对：删去第 line 行后，求其余约束对该行两事件时间差的最紧区间。

    输入无效或原约束互相冲突时，直接返回 solve() 的现有求解结果。
    """
    rows, result = _parse_and_solve(text)
    if result["status"] != "ok":
        return result

    target = next((r for r in rows if r.line == line), None)
    if target is None:
        return {
            "status": "error",
            "errors": [{"line": line, "message": f"第{line}行不是一条有效约束行（空行或不存在的行号），无法核对。"}],
        }

    names = result["names"]
    index = result["index"]

    # 移除所选行对应的上、下界两条约束，其余行照常建边
    edges = [e for e in result["edges"] if e.line != target.line]

    ia, ib = index[target.a], index[target.b]
    # 上界：t(乙) − t(甲) 的最紧上界 = 甲 -> 乙 最短路
    high_val, upper_path = _derive_bound(names, edges, ia, ib)
    # 下界：t(甲) − t(乙) 的最紧上界 = 乙 -> 甲 最短路，取负即 t(乙) − t(甲) 的最紧下界
    low_val, lower_path = _derive_bound(names, edges, ib, ia)
    derived_low = -low_val if low_val is not None else None
    derived_high = high_val

    # 推导区间完全落在所选行区间内 <=> 可删；任一端点无界或超出 <=> 必要
    removable = (
        derived_low is not None
        and derived_high is not None
        and derived_low >= target.low
        and derived_high <= target.high
    )

    return {
        "status": "ok",
        "line": target.line,
        "a": target.a,
        "b": target.b,
        "low": target.low,
        "high": target.high,
        "derived_low": derived_low,
        "derived_high": derived_high,
        "lower_bounded": derived_low is not None,
        "upper_bounded": derived_high is not None,
        "lower_path": lower_path,
        "upper_path": upper_path,
        "verdict": "removable" if removable else "necessary",
        "event_count": len(names),
        "line_count": len(rows),
    }


# ---------- 两版比较 ----------

def _evidence_for(system: dict, anchor: str, target: str, minute: int, annotate) -> dict | None:
    """修订版中确定 target 相对第 0 分钟事件 anchor 的规范化时刻的推导路径证据。

    复用冗余核对同款 _derive_bound：anchor -> target 最短路给出最紧上界，
    target -> anchor 最短路取负给出最紧下界；规范化可行解恰好顶在其中一个紧界上，
    选中与 minute 相等的那条路径，路径上的修订行原始行号即“导致变化的修订行号”。
    target 与 anchor 不连通（属于另一个独立事件组件）时返回 None：两版各按自己的
    最早事件归零，该事件的“分钟变化”只是规范化假象，不构成可比差异。
    """
    names = system["names"]
    edges = system["edges"]
    index = system["index"]
    ia, it = index[anchor], index[target]

    if ia == it:
        return {"is_anchor": True, "direction": None, "bound": 0, "lines": [], "path": []}

    upper_val, upper_path = _derive_bound(names, edges, ia, it)
    back_val, back_path = _derive_bound(names, edges, it, ia)
    lower_val = -back_val if back_val is not None else None
    if upper_val is None and lower_val is None:
        return None  # target 与锚点分属互不连通的事件组件，无法相对比较

    if lower_val is not None and lower_val == minute:
        path, direction, bound = back_path, "lower", lower_val
    elif upper_val is not None and upper_val == minute:
        path, direction, bound = upper_path, "upper", upper_val
    elif lower_val is not None:  # 防御性回退：正常情况下必有一个紧界等于 minute
        path, direction, bound = back_path, "lower", lower_val
    else:
        path, direction, bound = upper_path, "upper", upper_val

    path = annotate(path)
    lines: list[int] = []
    for step in path:  # 同一行的上、下界极端情况下可能都在路径上，行号去重保序
        if step["line"] not in lines:
            lines.append(step["line"])
    return {"is_anchor": False, "direction": direction, "bound": bound, "lines": lines, "path": path}


def compare_texts(base_text: str, revised_text: str) -> dict:
    """两版独立校验、独立联立后按事件名对齐比较。

    任一版无效（error）或互相矛盾（conflict）时，不生成差异结论，
    分别在 base / revised 字段中带回该版的完整公开求解结果（错误列表或闭合矛盾链）。
    """
    base_rows, base_res = _parse_and_solve(base_text)
    revised_rows, revised_res = _parse_and_solve(revised_text)

    if base_res["status"] != "ok" or revised_res["status"] != "ok":
        return {
            "status": "invalid",
            "base": _format_ok(base_res) if base_res["status"] == "ok" else base_res,
            "revised": _format_ok(revised_res) if revised_res["status"] == "ok" else revised_res,
        }

    b_names = base_res["names"]
    r_names = revised_res["names"]
    b_minute = dict(zip(b_names, base_res["minutes"]))
    r_minute = dict(zip(r_names, revised_res["minutes"]))
    b_set, r_set = set(b_names), set(r_names)

    # 两版各自“第 0 分钟”的事件；优先选用两版共有的第 0 分钟事件作锚点，
    # 使共同事件的变化分钟数不夹带整体平移；没有共有锚点时各取本版最早事件。
    b_zeros = [name for name in b_names if b_minute[name] == 0]
    r_zeros = [name for name in r_names if r_minute[name] == 0]
    common_zero = next((name for name in b_zeros if name in r_zeros), None)
    base_anchor = common_zero or b_zeros[0]
    revised_anchor = common_zero or r_zeros[0]

    # 基准行按书写事件对索引，用于标注修订行相对基准是“新增/修改/未变”
    base_pairs: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for r in base_rows:
        base_pairs.setdefault((r.a, r.b), []).append((r.low, r.high))
    revised_by_line = {r.line: r for r in revised_rows}

    def annotate(path: list[dict]) -> list[dict]:
        for step in path:
            row = revised_by_line.get(step["line"])
            label = "unchanged"
            if row is not None:
                base_bounds = base_pairs.get((row.a, row.b))
                if base_bounds is None:
                    label = "added"
                elif (row.low, row.high) not in base_bounds:
                    label = "changed"
            step["change"] = label
        return path

    alignment: list[dict] = []
    changed_count = 0

    # 共同事件：按基准版首次出现顺序对齐
    incomparable_count = 0
    for name in b_names:
        if name not in r_set:
            continue
        bm, rm = b_minute[name], r_minute[name]
        delta = rm - bm
        entry: dict = {
            "kind": "common",
            "event": name,
            "base_minute": bm,
            "revised_minute": rm,
            "delta": delta,
            "evidence": None,
        }
        if delta != 0:
            evidence = _evidence_for(revised_res, revised_anchor, name, rm, annotate)
            if evidence is None:
                # 与两版公共锚点不连通：分钟差只是各组件独立归零的假象，不判为变化
                entry["kind"] = "incomparable"
                incomparable_count += 1
            else:
                changed_count += 1
                entry["evidence"] = evidence
        alignment.append(entry)

    # 删除事件：仅基准版存在（保持基准版首次出现顺序）
    for name in b_names:
        if name not in r_set:
            alignment.append({
                "kind": "removed",
                "event": name,
                "base_minute": b_minute[name],
                "revised_minute": None,
                "delta": None,
                "evidence": None,
            })

    # 新增事件：仅修订版存在（保持修订版首次出现顺序）
    for name in r_names:
        if name not in b_set:
            alignment.append({
                "kind": "added",
                "event": name,
                "base_minute": None,
                "revised_minute": r_minute[name],
                "delta": None,
                "evidence": None,
            })

    return {
        "status": "ok",
        "base": {
            "event_count": len(b_names),
            "line_count": len(base_rows),
            "anchor": base_anchor,
        },
        "revised": {
            "event_count": len(r_names),
            "line_count": len(revised_rows),
            "anchor": revised_anchor,
        },
        "anchor_shifted": base_anchor != revised_anchor,
        "common_count": len(b_set & r_set),
        "changed_count": changed_count,
        "incomparable_count": incomparable_count,
        "added_count": len(r_set - b_set),
        "removed_count": len(b_set - r_set),
        "alignment": alignment,
    }


# ---------- 冲突单行修订建议 ----------

def _row_text(row: Row, low: int, high: int) -> str:
    """把一条约束还原为输入格式的整行文本（事件名原样，界值替换为给定值）。"""
    return f"{row.a},{row.b},{low},{high}"


def suggest_repairs(text: str) -> dict:
    """冲突单行修订建议：找出“只放宽某一行的某一个端点即可消除矛盾”的最小改动。

    流程：复用 parse_text 逐行校验（输入错误直接返回逐行错误）；原文本可解时
    明确说明无需修订；联立矛盾时遍历每条有效约束行，暂时移除该行的上、下界
    两条边后对其余行运行 Bellman-Ford——仍矛盾的行排除（只改该行一个端点救不回
    其余行自身的矛盾）；其余可解时复用冗余核对同款 _derive_bound 求这两个事件
    时间差的最紧可行区间 [dl, dh]：

    - 上界冲突（dh < low）：只放宽下界至 dh（low' = dh，上界不动），改动 low − dh 分钟，
      证据为推出该最紧上界的原始行号与界值推导链；
    - 下界冲突（dl > high）：只放宽上界至 dl（high' = dl，下界不动），改动 dl − high 分钟，
      证据为推出该最紧下界的原始行号与界值推导链。

    区间含整数端点，移到边界即首次相交的整数分钟，改动量最小。建议按改动分钟数、
    原始行号升序排序；没有任何单行修复时明确提示。
    """
    rows, errors = parse_text(text)
    if errors:
        return {"status": "error", "errors": errors}
    if not rows:
        return {
            "status": "error",
            "errors": [{"line": None, "message": "没有可联立的有效约束行。"}],
        }

    result = solve_rows(rows)
    if result["status"] == "ok":
        return {
            "status": "ok",
            "message": "原文本区间无冲突，无需修订。",
            "event_count": len(result["names"]),
            "line_count": len(rows),
        }

    # 冲突分支不含内部结构，重建图（与 solve_rows 同一套建边逻辑）
    names, index, all_edges = _build_graph(rows)

    suggestions: list[dict] = []
    for row in rows:
        # 暂时移除该行的上、下界两条约束，其余行照常联立
        edges = [e for e in all_edges if e.line != row.line]
        rest_rows = [r for r in rows if r.line != row.line]
        if rest_rows and solve_rows(rest_rows)["status"] != "ok":
            continue  # 其余行自身仍矛盾：只改该行一个端点无法修复，排除
        # 其余行为空时无任何约束，必然可解

        ia, ib = index[row.a], index[row.b]
        # 其余约束推出的最紧可行区间 [derived_low, derived_high]（两端必有界，否则其余行无解）
        high_val, upper_path = _derive_bound(names, edges, ia, ib)
        low_val, lower_path = _derive_bound(names, edges, ib, ia)
        derived_high = high_val
        derived_low = -low_val if low_val is not None else None
        if derived_low is None or derived_high is None:
            continue  # 防御：其余行可解时两事件互相可达，两端必有界

        if derived_high < row.low:
            # 上界冲突：只放宽下界至首次相交的整数分钟 derived_high
            suggestions.append({
                "line": row.line,
                "a": row.a,
                "b": row.b,
                "low": row.low,
                "high": row.high,
                "endpoint": "low",
                "endpoint_label": "下界（最少分钟）",
                "old_value": row.low,
                "new_value": derived_high,
                "change_minutes": row.low - derived_high,
                "new_line": _row_text(row, derived_high, row.high),
                "derived_low": derived_low,
                "derived_high": derived_high,
                "forcing_path": upper_path,
                "forcing_lines": [s["line"] for s in upper_path],
            })
        elif derived_low > row.high:
            # 下界冲突：只放宽上界至首次相交的整数分钟 derived_low
            suggestions.append({
                "line": row.line,
                "a": row.a,
                "b": row.b,
                "low": row.low,
                "high": row.high,
                "endpoint": "high",
                "endpoint_label": "上界（最多分钟）",
                "old_value": row.high,
                "new_value": derived_low,
                "change_minutes": derived_low - row.high,
                "new_line": _row_text(row, row.low, derived_low),
                "derived_low": derived_low,
                "derived_high": derived_high,
                "forcing_path": lower_path,
                "forcing_lines": [s["line"] for s in lower_path],
            })
        # 其余情形（该行区间已含推导区间）说明其余行不可能可解，不会走到

    suggestions.sort(key=lambda s: (s["change_minutes"], s["line"]))

    return {
        "status": "conflict",
        "conflict": result["conflict"],
        "suggestions": suggestions,
        "suggestion_count": len(suggestions),
        "checked_lines": len(rows),
        "event_count": len(names),
        "line_count": len(rows),
    }


# ---------- 绝对时间锚定 ----------

def _dt_to_minute(dt: datetime) -> int:
    """无时区本地日期时刻转相对统一零点 ZERO_DT 的分钟数（整数运算，无浮点误差）。"""
    delta = dt - ZERO_DT
    return delta.days * 1440 + delta.seconds // 60


def _minute_to_text(minute: int) -> str | None:
    """相对零点的分钟数转回 “YYYY-MM-DD HH:MM”；超出 datetime 可表示范围时返回 None。"""
    try:
        dt = ZERO_DT + timedelta(minutes=minute)
    except OverflowError:
        return None
    return f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}"


def parse_anchors(text: str) -> tuple[list[Anchor], list[dict]]:
    """按行解析锚点：事件名,YYYY-MM-DD HH:MM（同一无时区本地时间，精确到分钟）。

    返回 (有效锚点, 错误列表)；空行跳过但行号保留为锚点文本的原始行号。
    """
    errors: list[dict] = []
    anchors: list[Anchor] = []

    if not text or not text.strip():
        return anchors, [{"line": None, "message": "锚点输入为空：请粘贴“事件名,YYYY-MM-DD HH:MM”格式的多行文本。"}]

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为锚点文本的原始行号

        # 兼容中文逗号
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) != 2:
            errors.append({
                "line": line_no,
                "message": f"锚点第{line_no}行：应为 2 个字段（事件名,YYYY-MM-DD HH:MM），实际得到 {len(parts)} 个。",
            })
            continue

        name, dt_s = parts
        if not name:
            errors.append({"line": line_no, "message": f"锚点第{line_no}行：事件名为空。"})
            continue

        m = _ANCHOR_DT_RE.match(dt_s)
        if not m:
            errors.append({
                "line": line_no,
                "message": f"锚点第{line_no}行：日期时刻应为 “YYYY-MM-DD HH:MM”（24 小时制，精确到分钟），得到 “{dt_s}”。",
            })
            continue

        year, month, day, hour, minute = (int(g) for g in m.groups())
        try:
            dt = datetime(year, month, day, hour, minute)
        except ValueError:
            errors.append({
                "line": line_no,
                "message": f"锚点第{line_no}行：日期时刻 “{dt_s}” 不存在（请检查月份、日期与时分是否越界）。",
            })
            continue

        anchors.append(Anchor(line_no, name, _dt_to_minute(dt), _minute_to_text(_dt_to_minute(dt)) or dt_s))

    return anchors, errors


def solve_anchored(text: str, anchors_text: str) -> dict:
    """绝对时间锚定：区间约束与锚点等式联立。

    每个锚点换算为相对统一零点（0001-01-01 00:00，无时区本地时间）的分钟数 M，
    引入零点节点 ZERO 与一对等式边（ZERO->事件 权 M、事件->ZERO 权 -M），与区间行
    复用同一套差分约束 Bellman-Ford 联立；同名锚点重复也作为两条等式参与判定，
    时刻不同即构成负环。负环还原的闭合矛盾链同时含区间行号、锚点行号与所用界值。

    可解时不取任何任意平移的可行解充当真实日期：对每个事件用冗余核对同款单源
    最短路求其相对零点的最紧下界/上界，仅当两端都有界（与锚点连通）时给出绝对
    日期时刻（下界==上界为精确点，否则为范围），其余事件标为“未定位”。
    """
    errors: list[dict] = []
    rows: list[Row] = []
    if text and text.strip():
        rows, errors = parse_text(text)  # 复用现有区间校验；区间文本留空即纯锚点模式
    anchors, anchor_errors = parse_anchors(anchors_text)
    errors = errors + anchor_errors
    if errors:
        return {"status": "error", "errors": errors}
    if not rows and not anchors:
        # parse_anchors 对空文本已报错，正常不会走到；防御性返回
        return {"status": "error", "errors": [{"line": None, "message": "没有可联立的区间约束或锚点。"}]}

    # 区间行复用现有建边逻辑，再补入零点节点与每个锚点的等式边
    names, index, edges = _build_graph(rows)
    index[ZERO_NODE] = len(names)
    names.append(ZERO_NODE)
    iz = index[ZERO_NODE]
    for a in anchors:
        ie = index.get(a.event)
        if ie is None:
            ie = len(names)
            index[a.event] = ie
            names.append(a.event)
        edges.append(Edge(iz, ie, a.minute, a.line, "anchor", a.minute, "anchor", a.text))
        edges.append(Edge(ie, iz, -a.minute, a.line, "anchor", a.minute, "anchor", a.text))

    dist, pred, last_relaxed = _relax_all(names, edges)
    if last_relaxed is not None:
        return _conflict_result(names, pred, last_relaxed, len(names))

    # 每个事件相对零点的最紧界：上界 = ZERO->事件 最短路；下界 = -(事件->ZERO 最短路)。
    # 反向图上从 ZERO 跑一次最短路即得全部“事件->ZERO”距离。
    upper_dist, _ = _bellman_ford(names, edges, iz)
    rev_edges = [Edge(e.v, e.u, e.w, e.line, e.kind, e.bound, e.source, e.label) for e in edges]
    lower_dist, _ = _bellman_ford(names, rev_edges, iz)

    events: list[dict] = []
    for i, name in enumerate(names):
        if name == ZERO_NODE:
            continue
        ub, lb = upper_dist[i], lower_dist[i]
        if ub is None or lb is None:
            # 与零点不连通（独立事件组件）：只有相对区间，不编造任何绝对日期
            events.append({
                "event": name,
                "located": False,
                "minute_low": None,
                "minute_high": None,
                "abs_low": None,
                "abs_high": None,
                "exact": False,
            })
            continue
        lo, hi = -lb, ub
        events.append({
            "event": name,
            "located": True,
            "minute_low": lo,
            "minute_high": hi,
            "abs_low": _minute_to_text(lo),
            "abs_high": _minute_to_text(hi),
            "exact": lo == hi,
        })

    # 已定位事件按最早时刻排序在前，未定位事件按名称排序在后
    events.sort(key=lambda e: (not e["located"], e["minute_low"] if e["minute_low"] is not None else 0, e["event"]))
    located_count = sum(1 for e in events if e["located"])

    return {
        "status": "ok",
        "anchors": [
            {"line": a.line, "event": a.event, "time": a.text, "minute": a.minute}
            for a in anchors
        ],
        "events": events,
        "event_count": len(events),
        "located_count": located_count,
        "anchor_count": len(anchors),
        "line_count": len(rows),
    }


# ---------- 互斥说法下的先后查询 ----------

# 先后结论的对外标签
_VERDICT_LABELS = {
    "before": "甲始终先于乙",
    "after": "甲始终后于乙",
    "undetermined": "不确定",
    "no_feasible": "无可行组合",
}


def parse_groups(text: str) -> tuple[list[list[Claim]], list[dict]]:
    """按行解析互斥说法候选组：每行 “区间A | 区间B”，两侧均复用区间行格式与同款校验。

    返回 (候选组列表, 错误列表)；每个候选组为 [A侧说法, B侧说法]。
    空行跳过但行号保留为候选组文本的原始行号；最多 MAX_GROUP_LINES 行。
    """
    errors: list[dict] = []
    groups: list[list[Claim]] = []

    if not text or not text.strip():
        return groups, [{"line": None, "message": "候选组输入为空：请粘贴每行 “区间A | 区间B” 格式的互斥说法（最多 6 行）。"}]

    non_empty = 0
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为候选组文本的原始行号
        non_empty += 1

        # 兼容中文竖线
        sides = [s.strip() for s in line.replace("｜", "|").split("|")]
        if len(sides) != 2:
            errors.append({
                "line": line_no,
                "message": f"候选组第{line_no}行：应为 “区间A | 区间B” 两段互斥说法（以一个 | 分隔），实际得到 {len(sides)} 段。",
            })
            continue

        claims: list[Claim] = []
        for side_label, side_text in zip(("A", "B"), sides):
            # 兼容中文逗号
            parts = [p.strip() for p in side_text.replace("，", ",").split(",")]
            if len(parts) != 4:
                errors.append({
                    "line": line_no,
                    "message": f"候选组第{line_no}行{side_label}侧：应为 4 个字段（事件甲,事件乙,最少分钟,最多分钟），实际得到 {len(parts)} 个。",
                })
                break
            a, b, low_s, high_s = parts
            low, high, field_errors = _validate_interval_fields(a, b, low_s, high_s)
            if field_errors:
                errors.append({
                    "line": line_no,
                    "message": f"候选组第{line_no}行{side_label}侧：" + "；".join(field_errors) + "。",
                })
                break
            claims.append(Claim(line_no, side_label, a, b, low, high))  # type: ignore[arg-type]
        else:
            groups.append(claims)  # 两侧均有效才成组（for 正常结束、未 break）

    if non_empty > MAX_GROUP_LINES:
        errors.append({
            "line": None,
            "message": f"候选组最多 {MAX_GROUP_LINES} 行，实际得到 {non_empty} 行（每行二选一，组合数为 2 的幂，限制行数以保证枚举耗时可控）。",
        })

    return groups, errors


def solve_precedence(text: str, groups_text: str, qa: str, qb: str) -> dict:
    """互斥说法下的先后查询：共同约束 + 每组二选一的全部组合枚举联立。

    共同约束沿用事件区间文本；候选组每行 “区间A | 区间B” 表示两条只能选一条的说法。
    枚举全部 2^N 个组合（N ≤ MAX_GROUP_LINES），每个组合 = 共同约束 + 各组所选一侧，
    复用同一套差分约束 Bellman-Ford 联立：存在负环的组合判为冲突并排除；对其余可行
    组合复用冗余核对同款 _derive_bound 求 t(乙) − t(甲) 的最紧下界/上界（推不出的
    端点为无界）。跨组合合并：下界取各组合最小值、上界取各组合最大值，任一组合对应
    端无界则合并端无界。

    判定：无可行组合 ⇒ 不作先后判断（no_feasible）；合并下界 ≥ 1 分钟 ⇒ 甲始终先于乙
    （before）；合并上界 ≤ −1 分钟 ⇒ 甲始终后于乙（after）；其余 ⇒ 不确定（undetermined）。
    查询的甲、乙必须出现在共同约束中。
    """
    qa, qb = (qa or "").strip(), (qb or "").strip()

    rows, errors = parse_text(text)  # 共同约束复用现有区间校验（含空文本报错）
    groups, group_errors = parse_groups(groups_text)
    errors = errors + group_errors

    # 查询的甲、乙须出现在共同约束中
    if not qa:
        errors.append({"line": None, "message": "查询的事件甲为空：请填写要查询先后关系的事件甲。"})
    if not qb:
        errors.append({"line": None, "message": "查询的事件乙为空：请填写要查询先后关系的事件乙。"})
    if qa and qb and qa == qb:
        errors.append({"line": None, "message": f"查询的事件甲、乙相同（“{qa}”）：请查询两个不同事件的先后关系。"})
    if rows:
        common_names = {r.a for r in rows} | {r.b for r in rows}
        for label, name in (("甲", qa), ("乙", qb)):
            if name and name not in common_names:
                errors.append({
                    "line": None,
                    "message": f"查询的事件{label}“{name}”未出现在共同约束中：先后查询的甲、乙须出现在共同约束中。",
                })
    if errors:
        return {"status": "error", "errors": errors}

    combinations: list[dict] = []
    feasible_count = 0
    merged_low: int | None = None   # 跨组合最小下界（只统计有界端点）
    merged_high: int | None = None  # 跨组合最大上界（只统计有界端点）
    lower_unbounded = False  # 任一可行组合下界无界 ⇒ 合并下界无界
    upper_unbounded = False  # 任一可行组合上界无界 ⇒ 合并上界无界

    for combo_index, picks in enumerate(product(*groups), start=1):
        # 该组合 = 共同约束 + 各组所选一侧，联立（同一套建边与 Bellman-Ford）
        combo_rows = rows + [Row(c.line, c.a, c.b, c.low, c.high) for c in picks]
        names, index, edges = _build_graph(combo_rows)
        _, _, last_relaxed = _relax_all(names, edges)
        pick_desc = [
            {"line": c.line, "side": c.side, "a": c.a, "b": c.b, "low": c.low, "high": c.high}
            for c in picks
        ]
        if last_relaxed is not None:
            combinations.append({
                "index": combo_index,
                "picks": pick_desc,
                "feasible": False,
                "low": None,
                "high": None,
                "lower_bounded": False,
                "upper_bounded": False,
            })
            continue

        ia, ib = index[qa], index[qb]
        # 上界：t(乙) − t(甲) 的最紧上界 = 甲 -> 乙 最短路；下界 = 乙 -> 甲 最短路取负
        high_val, _ = _derive_bound(names, edges, ia, ib)
        low_val, _ = _derive_bound(names, edges, ib, ia)
        low = -low_val if low_val is not None else None
        high = high_val

        feasible_count += 1
        if low is None:
            lower_unbounded = True
        else:
            merged_low = low if merged_low is None else min(merged_low, low)
        if high is None:
            upper_unbounded = True
        else:
            merged_high = high if merged_high is None else max(merged_high, high)
        combinations.append({
            "index": combo_index,
            "picks": pick_desc,
            "feasible": True,
            "low": low,
            "high": high,
            "lower_bounded": low is not None,
            "upper_bounded": high is not None,
        })

    conflict_count = len(combinations) - feasible_count
    if feasible_count == 0:
        # 无可行组合：不作先后判断，合并区间无意义
        verdict = "no_feasible"
        lower_bounded = upper_bounded = False
        merged_low = merged_high = None
    else:
        lower_bounded = not lower_unbounded
        upper_bounded = not upper_unbounded
        if lower_bounded and merged_low is not None and merged_low >= 1:
            verdict = "before"
        elif upper_bounded and merged_high is not None and merged_high <= -1:
            verdict = "after"
        else:
            verdict = "undetermined"

    return {
        "status": "ok",
        "a": qa,
        "b": qb,
        "groups": [
            {
                "line": g[0].line,
                "sides": [
                    {"side": c.side, "a": c.a, "b": c.b, "low": c.low, "high": c.high}
                    for c in g
                ],
            }
            for g in groups
        ],
        "group_count": len(groups),
        "combination_count": len(combinations),
        "feasible_count": feasible_count,
        "conflict_count": conflict_count,
        "lower_bounded": lower_bounded,
        "upper_bounded": upper_bounded,
        "merged_low": merged_low if lower_bounded else None,
        "merged_high": merged_high if upper_bounded else None,
        "verdict": verdict,
        "verdict_label": _VERDICT_LABELS[verdict],
        "combinations": combinations,
        "event_count": len({r.a for r in rows} | {r.b for r in rows}),
        "line_count": len(rows),
    }


# ---------- 最少撤回 ----------

# 撤回搜索允许的最多非空行：枚举 C(n,k) 个子集做 Bellman-Ford，限 10 条保证耗时可控
MAX_WITHDRAWAL_LINES = 10


def find_minimum_withdrawals(text: str) -> dict:
    """最少撤回：按撤回行数递增搜索使剩余约束可行的最少原始行号组合。

    复用 parse_text 的逐行校验（语法错误逐行返回）与同一套差分约束 Bellman-Ford
    （solve_rows/_format_ok）。非空行最多 MAX_WITHDRAWAL_LINES 条，超限明确报错
    （以实际非空行数提示，行号按原始文本计算）。

    空约束集（空文本/只有空行）视为可行，直接返回零撤回方案与空时间线；原文本身
    可行时也返回零撤回方案。否则按 k=1,2,… 枚举 C(n,k) 个撤回组合，找到第一个存在
    可行剩余子集的 k 即停止（撤回数最少），返回该层全部可行组合；每个方案附剩余
    约束的一条规范化可行时间线（最早事件为第 0 分钟），撤回全部行时时间线为空。
    """
    # 空文本/只有空行：空约束集视为可行（parse_text 对空文本会报错，这里单独处理）
    if not text or not text.strip():
        return {
            "status": "ok",
            "minimum": 0,
            "total_lines": 0,
            "checked_combinations": 0,
            "message": "没有任何非空约束：空约束集视为可行，无需撤回任何行（空时间线）。",
            "original_feasible": True,
            "plans": [
                {
                    "index": 1,
                    "withdraw_count": 0,
                    "withdrawn_lines": [],
                    "remaining_count": 0,
                    "timeline": [],
                }
            ],
        }

    # 超限检查以非空行为准（与候选组限制同款口径：空行不计入、行号保留）
    non_empty = sum(1 for raw in text.splitlines() if raw.strip())
    rows, errors = parse_text(text)
    if non_empty > MAX_WITHDRAWAL_LINES:
        errors = errors + [{
            "line": None,
            "message": (
                f"最少撤回最多处理 {MAX_WITHDRAWAL_LINES} 条非空约束，"
                f"实际得到 {non_empty} 条（搜索按撤回行数枚举全部行号组合，"
                "组合数随行数快速增长，限 10 条以保证耗时可控）。"
            ),
        }]
    if errors:
        return {"status": "error", "errors": errors}

    n = len(rows)
    lines = [r.line for r in rows]

    # k=0：先试原文是否已可行（此时方案为零撤回，时间线即原文规范化可行解）
    original = solve_rows(rows)
    checked = 1
    if original["status"] == "ok":
        return {
            "status": "ok",
            "minimum": 0,
            "total_lines": n,
            "checked_combinations": checked,
            "message": "原文区间无冲突，无需撤回任何行；以下为原文的一条可行时间线。",
            "original_feasible": True,
            "plans": [{
                "index": 1,
                "withdraw_count": 0,
                "withdrawn_lines": [],
                "remaining_count": n,
                "timeline": _format_ok(original)["timeline"],
            }],
        }

    # 原文矛盾：按撤回行数 k 递增枚举 C(n,k) 个原始行号组合，第一个有可行方案的 k 最少
    original_conflict = original["conflict"]
    for k in range(1, n + 1):
        plans: list[dict] = []
        for combo in combinations(range(n), k):
            checked += 1
            withdrawn = {lines[i] for i in combo}
            remaining = [r for r in rows if r.line not in withdrawn]
            system = solve_rows(remaining)
            if system["status"] != "ok":
                continue  # 剩余约束仍矛盾：该撤回组合不能消除冲突
            plans.append({
                "withdrawn_lines": sorted(withdrawn),
                "remaining_count": len(remaining),
                "timeline": _format_ok(system)["timeline"],
            })
        if plans:
            # 组合按原始行号升序枚举（combinations 保序），方案直接编号
            for i, p in enumerate(plans, start=1):
                p["index"] = i
                p["withdraw_count"] = k
            if k == n:
                message = (
                    f"原 {n} 条约束互相冲突，最少需要撤回全部 {n} 行；撤回后为空约束集，"
                    "视为可行（空时间线）。"
                )
            else:
                message = (
                    f"原 {n} 条约束互相冲突，最少撤回 {k} 行即可使剩余约束可行；"
                    f"共找到 {len(plans)} 个最少撤回方案，每个方案附剩余约束的一条可行时间线。"
                )
            return {
                "status": "ok",
                "minimum": k,
                "total_lines": n,
                "checked_combinations": checked,
                "message": message,
                "original_feasible": False,
                "conflict": original_conflict,
                "plans": plans,
            }

    # 理论上不可达：撤回全部行后空约束集必可行
    return {"status": "error", "errors": [{"line": None, "message": "搜索失败：未找到任何可行的撤回方案。"}]}


# ---------- 事件别名归并核对 ----------

def parse_aliases(text: str) -> tuple[list[Alias], list[dict]]:
    """按行解析别名：事件名,同一事件的另一名称（两个名称指同一事件）。

    返回 (有效别名, 错误列表)；空行跳过但行号保留为别名文本的原始行号。
    """
    errors: list[dict] = []
    aliases: list[Alias] = []

    if not text or not text.strip():
        return aliases, [{"line": None, "message": "别名输入为空：请粘贴“事件名,同一事件的另一名称”格式的多行文本。"}]

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为别名文本的原始行号

        # 兼容中文逗号
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) != 2:
            errors.append({
                "line": line_no,
                "message": f"别名第{line_no}行：应为 2 个字段（事件名,同一事件的另一名称），实际得到 {len(parts)} 个。",
            })
            continue

        a, b = parts
        row_errors: list[str] = []
        if not a:
            row_errors.append("事件名为空")
        if not b:
            row_errors.append("同一事件的另一名称为空")
        if a and b and a == b:
            row_errors.append(f"两个名称相同（“{a}”）：同一行请填写同一事件的两个不同名称")
        if row_errors:
            errors.append({"line": line_no, "message": f"别名第{line_no}行：" + "；".join(row_errors) + "。"})
            continue

        aliases.append(Alias(line_no, a, b))

    return aliases, errors


class _UnionFind:
    """按传递关系归并名称的并查集：A=B、B=C ⇒ A、B、C 归为同一事件。"""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        if x not in self._parent:
            self._parent[x] = x

    def find(self, x: str) -> str:
        parent = self._parent
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # 路径压缩
            parent[x], x = root, parent[x]
        return root

    def union(self, x: str, y: str) -> None:
        self.add(x)
        self.add(y)
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self._parent[ry] = rx


def solve_aliases(text: str, aliases_text: str) -> dict:
    """事件别名归并核对：按传递关系归并名称后，用归并后的节点联立原区间。

    区间文本复用 parse_text 的现有校验（含空文本报错），别名文本复用同款逐行校验。
    并查集把别名按传递关系归组后，每组取“区间文本中最先出现、否则别名文本中最先出现”
    的名称作统一事件名；区间行两端替换为统一事件名（行号保留为原始行号）后复用
    solve_rows 联立。同组内的区间（两端归并为同一事件）成为自环约束照常参与判定：
    等价于要求 0 落在该行区间内，下界为正或上界为负即构成负环。

    冲突时闭合矛盾链保留原始区间行号，每一步另附该行的原始事件名（row_a/row_b），
    并返回别名组列表（每组统一事件名与原名称）；可解时返回按统一事件归并的时间线
    （每个节点附该组原名称）与逐条核对（含归并后事件对与同组内标记）。
    """
    rows, errors = parse_text(text)  # 区间文本复用现有校验
    aliases, alias_errors = parse_aliases(aliases_text)
    errors = errors + alias_errors
    if errors:
        return {"status": "error", "errors": errors}
    if not rows:
        return {
            "status": "error",
            "errors": [{"line": None, "message": "没有可联立的有效约束行。"}],
        }

    # 名称的“首次出现”顺序：先按区间行、再按别名行，决定组内成员排序与统一事件名
    first_seen: dict[str, int] = {}

    def _see(name: str) -> None:
        if name not in first_seen:
            first_seen[name] = len(first_seen)

    for r in rows:
        _see(r.a)
        _see(r.b)
    for al in aliases:
        _see(al.a)
        _see(al.b)

    uf = _UnionFind()
    for name in first_seen:
        uf.add(name)
    for al in aliases:
        uf.union(al.a, al.b)

    # 组 -> 组内成员（first_seen 按插入序遍历，成员天然按首次出现排序）；
    # 统一事件名 = 组内最先出现的名称（区间中出现过的名称优先，见 _see 的顺序）
    members_by_root: dict[str, list[str]] = {}
    for name in first_seen:
        members_by_root.setdefault(uf.find(name), []).append(name)
    rep_of: dict[str, str] = {}  # 原名称 -> 统一事件名
    groups_by_rep: dict[str, list[str]] = {}  # 统一事件名 -> 组内原名称（含单名组）
    for members in members_by_root.values():
        rep = members[0]
        groups_by_rep[rep] = members
        for m in members:
            rep_of[m] = rep

    # 用归并后的节点联立原区间（行号保留为原始行号；同组内区间成为自环约束照常参与判定）
    merged_rows = [Row(r.line, rep_of[r.a], rep_of[r.b], r.low, r.high) for r in rows]
    system = solve_rows(merged_rows)

    original_names = {r.a for r in rows} | {r.b for r in rows}
    merged_names = {r.a for r in merged_rows} | {r.b for r in merged_rows}
    within_group_lines = [r.line for r in rows if rep_of[r.a] == rep_of[r.b]]

    # 别名组（至少两个名称）：统一事件名、组内原名称、是否出现在区间时间线中
    groups = [
        {
            "representative": rep,
            "members": members,
            "size": len(members),
            "in_timeline": rep in merged_names,
        }
        for rep, members in groups_by_rep.items()
        if len(members) >= 2
    ]
    groups.sort(key=lambda g: first_seen[g["representative"]])

    meta = {
        "groups": groups,
        "alias_count": len(aliases),
        "merged_group_count": len(groups),
        "event_count": len(merged_names),
        "original_event_count": len(original_names),
        "line_count": len(rows),
        "within_group_lines": within_group_lines,
        "within_group_count": len(within_group_lines),
    }

    if system["status"] != "ok":
        # 闭合矛盾链保留原始区间行号；每一步附该行的原始事件名，并带上别名组
        by_line = {r.line: r for r in rows}
        for step in system["conflict"]["steps"]:
            row = by_line.get(step["line"])
            if row is not None:
                step["row_a"] = row.a
                step["row_b"] = row.b
        return {"status": "conflict", "conflict": system["conflict"], **meta}

    names = system["names"]
    minutes = system["minutes"]
    index = system["index"]
    dist = system["dist"]

    timeline = [
        {"event": names[i], "minute": minutes[i], "members": groups_by_rep[names[i]]}
        for i in range(len(names))
    ]
    timeline.sort(key=lambda x: (x["minute"], x["event"]))

    differences = [
        {
            "line": r.line,
            "a": r.a,
            "b": r.b,
            "merged_a": rep_of[r.a],
            "merged_b": rep_of[r.b],
            "low": r.low,
            "high": r.high,
            "actual": dist[index[rep_of[r.b]]] - dist[index[rep_of[r.a]]],
            "same_group": rep_of[r.a] == rep_of[r.b],
        }
        for r in rows
    ]

    return {
        "status": "ok",
        "timeline": timeline,
        "differences": differences,
        **meta,
    }


# ---------- 行程可达性核对 ----------

def _split_two(line_no: int, line: str, prefix: str, field_desc: str, errors: list[dict]) -> list[str] | None:
    """按 2 个字段切分一行（兼容中文逗号）；字段数不对时按原始行号记一条错误。"""
    parts = [p.strip() for p in line.replace("，", ",").split(",")]
    if len(parts) != 2:
        errors.append({
            "line": line_no,
            "message": f"{prefix}第{line_no}行：应为 2 个字段（{field_desc}），实际得到 {len(parts)} 个。",
        })
        return None
    return parts


def parse_places(text: str) -> tuple[list[PlaceRow], list[dict]]:
    """按行解析事件地点：事件,地点。

    返回 (有效行, 错误列表)；空行跳过但行号保留为地点文本的原始行号。
    同一事件重复登记地点（无论地点是否相同）均为错误。
    """
    errors: list[dict] = []
    places: list[PlaceRow] = []

    if not text or not text.strip():
        return places, [{"line": None, "message": "事件地点输入为空：请逐行粘贴“事件,地点”。"}]

    seen_events: dict[str, int] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为地点文本的原始行号

        parts = _split_two(line_no, line, "事件地点", "事件,地点", errors)
        if parts is None:
            continue
        event, place = parts
        if not event or not place:
            empty = "事件名为空" if not event else "地点为空"
            errors.append({"line": line_no, "message": f"事件地点第{line_no}行：{empty}。"})
            continue
        if event in seen_events:
            errors.append({
                "line": line_no,
                "message": (
                    f"事件地点第{line_no}行：事件“{event}”重复登记地点"
                    f"（已在第{seen_events[event]}行登记）；同一事件只能填写一个地点。"
                ),
            })
            continue
        seen_events[event] = line_no
        places.append(PlaceRow(line_no, event, place))

    return places, errors


def parse_routes(text: str) -> tuple[list[RouteRow], list[dict]]:
    """按行解析有向通行路段：起点,终点,分钟（分钟为非负整数，0 表示同一地点瞬间可达）。

    返回 (有效行, 错误列表)；空行跳过但行号保留为路段文本的原始行号。
    同一有向起点→终点重复填写不算错误，求最短时自动取最小值；负通行时间为错误。
    """
    errors: list[dict] = []
    routes: list[RouteRow] = []

    if not text or not text.strip():
        return routes, [{"line": None, "message": "通行路段输入为空：请逐行粘贴“起点,终点,分钟”。"}]

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为路段文本的原始行号

        # 兼容中文逗号
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) != 3:
            errors.append({
                "line": line_no,
                "message": f"通行路段第{line_no}行：应为 3 个字段（起点,终点,分钟），实际得到 {len(parts)} 个。",
            })
            continue

        src, dst, minutes_s = parts
        row_errors: list[str] = []
        if not src:
            row_errors.append("起点为空")
        if not dst:
            row_errors.append("终点为空")
        if not _INT_RE.match(minutes_s):
            row_errors.append(f"通行分钟必须是整数分钟，得到 “{minutes_s}”")
        if row_errors:
            errors.append({"line": line_no, "message": f"通行路段第{line_no}行：" + "；".join(row_errors) + "。"})
            continue

        minutes = int(minutes_s)
        if minutes < 0:
            errors.append({
                "line": line_no,
                "message": f"通行路段第{line_no}行：通行分钟不能为负数（得到 {minutes}）；时间不能倒流，请检查起点、终点顺序或改为非负分钟。",
            })
            continue

        routes.append(RouteRow(line_no, src, dst, minutes))

    return routes, errors


def parse_itinerary(text: str) -> tuple[list[str], list[dict]]:
    """按发生顺序解析行程事件名：每行一个事件；兼容“事件,”之类误填的两字段写法。

    返回 (事件名列表, 错误列表)；空行跳过但行号保留为行程文本的原始行号。
    同一事件在行程中重复出现为错误（发生顺序应是互不相同的事件序列）。
    """
    errors: list[dict] = []
    events: list[str] = []

    if not text or not text.strip():
        return events, [{"line": None, "message": "行程顺序输入为空：请按发生顺序逐行填写事件名（每行一个事件）。"}]

    seen: dict[str, int] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为行程文本的原始行号

        # 兼容误写成“事件,”（或“事件，”）的两字段形式：取首个非空字段
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) > 2 or (len(parts) == 2 and parts[1] != ""):
            errors.append({
                "line": line_no,
                "message": f"行程顺序第{line_no}行：每行只填写一个事件名，实际得到 {len(parts)} 个字段（“{line}”）。",
            })
            continue
        name = parts[0]
        if not name:
            errors.append({"line": line_no, "message": f"行程顺序第{line_no}行：事件名为空。"})
            continue
        if name in seen:
            errors.append({
                "line": line_no,
                "message": (
                    f"行程顺序第{line_no}行：行程事件“{name}”重复出现"
                    f"（已在第{seen[name]}行出现）；发生顺序中的事件必须互不相同。"
                ),
            })
            continue
        seen[name] = line_no
        events.append(name)

    return events, errors


def _route_between(
    routes: list[RouteRow], src: str, dst: str
) -> tuple[int | None, list[dict]]:
    """求地点网络中 src -> dst 的最短通行时间与逐路段路线。

    边权均为非负分钟，使用 Dijkstra；同一起终点的多条有向路段全部保留，
    最短路自动取最小值。等距离的多条路线按“路径节点序列字典序”决胜，
    保证同一份输入得到确定且可复核的最短路线。

    返回 (最短分钟, 路段列表)，无路可达时分钟为 None、路段列表为空。
    每段含路段原始行号、起点、终点与该段分钟。
    """
    if src == dst:
        # 同地点按零分钟处理，不经过任何路段
        return 0, []

    adj: dict[str, list[tuple[str, int, int]]] = {}
    for r in routes:
        adj.setdefault(r.src, []).append((r.dst, r.minutes, r.line))

    # 按“(最短距离, 节点序列字典序)”决胜的 Dijkstra。
    # 普通 Dijkstra 只对每个顶点维护一个距离；为在等距离路线中选节点序列字典序最小者，
    # 堆项携带完整路径 (累计分钟, 路径序列)，并对每个顶点单独维护当前最佳的
    # (距离, 路径)：只有候选严格更优（更短，或等距且序列字典序更小）才入堆。
    # 决胜只看节点名序列（节点序列相同的平行边在还原阶段再按行号取最小），
    # 不保证“直达优先”——同距离时第二节点名字典序更小的路线胜出。
    # 边权非负，顶点第一次被 pop 即为其定稿最优路线。
    heap: list[tuple[int, tuple[str, ...]]] = [(0, (src,))]
    # 每个顶点当前最佳的 (距离, 路径)；邻接边只从仍是该顶点最佳的路径展开，
    # 被更优路线取代的旧路径不再扩展（其下游不可能凭旧前缀变得更优）。
    best: dict[str, tuple[int, tuple[str, ...]]] = {src: (0, (src,))}
    done: set[str] = set()
    while heap:
        d, path = heapq.heappop(heap)
        u = path[-1]
        if u in done:
            continue
        if best.get(u) != (d, path):
            continue  # 已被更优（同距离字典序更小）路线取代的过期堆项
        done.add(u)
        if u == dst:
            break
        # 邻接边按 (终点名, 分钟, 行号) 排序，使路径字典序比较有稳定依据
        for v, w, _line in sorted(adj.get(u, ()), key=lambda e: (e[0], e[1], e[2])):
            cand = d + w
            cand_path = path + (v,)
            cand_key = (cand, cand_path)
            old = best.get(v)
            if old is None or cand < old[0] or (cand == old[0] and cand_path < old[1]):
                best[v] = cand_key
                heapq.heappush(heap, cand_key)

    if dst not in done:
        return None, []

    # 沿定稿路径逐点对反查路段：该段分钟 = 相邻定稿点最佳距离之差；
    # 多行平行边中选分钟等于该差值且行号最小的一条。
    final_path = best[dst][1]
    segs: list[dict] = []
    for u, v in zip(final_path, final_path[1:]):
        w = best[v][0] - best[u][0]
        line = min(line for (vv, ww, line) in adj[u] if vv == v and ww == w)
        segs.append({"line": line, "from": u, "to": v, "minutes": w})
    return best[dst][0], segs

    if dst not in done:
        return None, []

    # 沿定稿路径逐点对反查路段：该段最短分钟 = 相邻定稿点的最短距离增量；
    # 多行平行边中选分钟等于该增量且行号最小的一条（与 Dijkstra 选中的边一致）。
    segs: list[dict] = []
    for u, v in zip(best_path[dst], best_path[dst][1:]):
        w = dist[v] - dist[u]
        matching = sorted(
            (line for (vv, ww, line) in adj[u] if vv == v and ww == w)
        )
        segs.append({"line": matching[0], "from": u, "to": v, "minutes": w})
    return dist[dst], segs


def _travel_step(names: list[str], e: Edge) -> dict:
    """通行下界边的可读步骤：相邻事件段从后一事件指向前一事件，含义为通行耗时下界。"""
    # Edge(b -> a, -d)：b 是段的后一事件、a 是前一事件；bound 为最短通行分钟
    return {
        "from": names[e.u],
        "to": names[e.v],
        "weight": e.w,
        "line": None,  # 通行约束不来自区间文本，行号显式置空
        "kind": "travel",
        "kind_label": "通行下界",
        "bound": e.bound,
        "source": "travel",
        "relation": f"{names[e.u]}−{names[e.v]} ≥ {e.bound}（{names[e.v]}→{names[e.u]} 最短通行）",
        "segment_index": e.label,  # 事件段序号（1 起）放在 label 字段随边传递
    }


def _itinerary_step_builder(segments_by_index: dict[int, dict]):
    """构造同时认识区间/锚点边与通行下界边的矛盾链步骤构建器。"""
    def build(names: list[str], e: Edge) -> dict:
        if e.kind == "travel":
            step = _travel_step(names, e)
            seg = segments_by_index.get(int(e.label))
            if seg is not None:
                step["segment"] = seg["index"]
                step["from_event"] = seg["from_event"]
                step["to_event"] = seg["to_event"]
                step["from_place"] = seg["from_place"]
                step["to_place"] = seg["to_place"]
                step["route"] = seg["route"]
                step["travel_minutes"] = seg["travel_minutes"]
            return step
        return _edge_step(names, e)
    return build


def check_itinerary(text: str, places_text: str, routes_text: str, itinerary_text: str) -> dict:
    """行程可达性核对：时间差区间 × 地点网络最短通行，判断整段行程是否可行。

    输入：
    - text：现有“事件甲,事件乙,最少分钟,最多分钟”区间文本（可留空，表示只核对通行）；
    - places_text：逐行“事件,地点”；
    - routes_text：逐行有向“起点,终点,分钟”（非负分钟，重复路段取最短）；
    - itinerary_text：按发生顺序排列的事件名（每行一个，互不相同）。

    对每对相邻行程事件求地点网络中的最短通行时间（同地点按零分钟），把每个
    “后一事件 − 前一事件 ≥ 最短通行分钟”作为通行下界与原区间联立（同一套差分约束
    Bellman-Ford）。无路可达时指出对应事件段；联立出现负环时给出含原区间行号、
    事件段及其最短路线的矛盾依据；可行时列出各段最短路线、所需分钟和一条满足全部
    约束的时间线。
    """
    # 1) 四类文本各自逐行校验（区间文本允许留空）
    errors: list[dict] = []
    rows: list[Row] = []
    if text and text.strip():
        rows, errors = parse_text(text)
    places, place_errors = parse_places(places_text)
    # 路段文本允许留空（只有一个事件、或相邻事件都在同地点时无需任何路段）
    routes: list[RouteRow] = []
    route_errors: list[dict] = []
    if routes_text and routes_text.strip():
        routes, route_errors = parse_routes(routes_text)
    itinerary, itinerary_errors = parse_itinerary(itinerary_text)
    errors = errors + place_errors + route_errors + itinerary_errors

    place_of = {p.event: p.place for p in places}

    # 2) 行程中的每个事件都必须有地点（区间文本里出现但不在行程中的事件不要求地点）。
    # 与上面的语法/字段错误一并返回，便于用户一次看到全部待修项；地点文本本身非法时
    # 仍尽量基于已成功解析的地点行做缺失检查。
    missing: list[dict] = []
    for idx, name in enumerate(itinerary, start=1):
        if name not in place_of:
            missing.append({
                "segment_position": idx,
                "event": name,
                "message": f"行程第 {idx} 个事件“{name}”缺少事件地点：请在“事件,地点”文本中登记其地点。",
            })
    if missing:
        errors.extend({"line": None, "message": m["message"]} for m in missing)
    if errors:
        result = {"status": "error", "errors": errors}
        if missing:
            result["missing_places"] = missing
        return result

    # 3) 逐相邻事件求地点网络最短通行；同地点零分钟，无路可达单独记录
    segments: list[dict] = []
    unreachable: list[dict] = []
    for i in range(len(itinerary) - 1):
        a, b = itinerary[i], itinerary[i + 1]
        pa, pb = place_of[a], place_of[b]
        idx = i + 1
        if pa == pb:
            shortest, route = 0, []
            same_place = True
        else:
            shortest, route = _route_between(routes, pa, pb)
            same_place = False
        seg = {
            "index": idx,
            "from_event": a,
            "to_event": b,
            "from_place": pa,
            "to_place": pb,
            "same_place": same_place,
            "reachable": shortest is not None,
            "travel_minutes": shortest,
            "route": route,
        }
        segments.append(seg)
        if shortest is None:
            unreachable.append(seg)

    counts = {
        "event_count": len({r.a for r in rows} | {r.b for r in rows} | set(itinerary)),
        "place_count": len({p.place for p in places}),
        "place_line_count": len(places),
        "route_count": len(routes),
        "line_count": len(rows),
        "itinerary_count": len(itinerary),
        "segment_count": len(segments),
    }

    if unreachable:
        # 无路可达：明确指出对应事件段（不做联立，也不产生“可行/冲突”结论）
        return {
            "status": "unreachable",
            "message": (
                f"行程共 {len(segments)} 个相邻事件段，其中 {len(unreachable)} 段在地点通行网络中"
                "无路可达（有向路段按起点→终点单向通行）；已逐段列出，请补充路段或核对地点名称。"
            ),
            "itinerary": itinerary,
            "segments": segments,
            "unreachable_segments": [s["index"] for s in unreachable],
            "unreachable_count": len(unreachable),
            **counts,
        }

    # 4) 原区间先独立联立：区间自身矛盾时直接返回现有矛盾链（与通行无关，不混入通行边）
    if rows:
        interval_system = solve_rows(rows)
        if interval_system["status"] != "ok":
            return {
                "status": "interval_conflict",
                "message": "上方时间差区间自身已互相矛盾（尚未加入通行下界），先返回现有闭合矛盾链；请先消除区间冲突，再核对行程可达性。",
                "conflict": interval_system["conflict"],
                "itinerary": itinerary,
                "segments": segments,
                **counts,
            }

    # 5) 通行下界与原区间联立：每段加边 b -> a，权 -d（即 t(b) − t(a) ≥ d）
    names, index, edges = _build_graph(rows)
    for name in itinerary:
        if name not in index:
            index[name] = len(names)
            names.append(name)
    segments_by_index: dict[int, dict] = {}
    for seg in segments:
        ia, ib = index[seg["from_event"]], index[seg["to_event"]]
        d = seg["travel_minutes"]
        # label 复用为事件段序号（字符串），矛盾链还原时据此附带事件段与最短路线
        edges.append(Edge(ib, ia, -d, -1, "travel", d, "travel", str(seg["index"])))
        segments_by_index[seg["index"]] = seg

    dist, pred, last_relaxed = _relax_all(names, edges)
    if last_relaxed is not None:
        result = _conflict_result(
            names, pred, last_relaxed, len(names),
            step_builder=_itinerary_step_builder(segments_by_index),
        )
        travel_steps = [s for s in result["conflict"]["steps"] if s["kind"] == "travel"]
        return {
            "status": "conflict",
            "message": (
                "把各相邻事件段的最短通行时间作为下界与原区间联立后出现闭合矛盾链："
                "链中含原始区间行与通行下界（标注对应事件段及其最短路线），即按发生顺序"
                "走完该行程所需的通行时间与某些时间差区间互不相容。"
            ),
            "conflict": result["conflict"],
            "travel_step_segments": [s["segment"] for s in travel_steps],
            "itinerary": itinerary,
            "segments": segments,
            **counts,
        }

    # 6) 可行：平移使最早事件为第 0 分钟，给出一条满足全部区间与通行下界的时间线
    base = min(dist)
    minutes = {names[i]: dist[i] - base for i in range(len(names))}
    timeline = [{"event": n, "minute": minutes[n], "place": place_of.get(n)} for n in names]
    timeline.sort(key=lambda x: (x["minute"], x["event"]))

    # 行程视角：按发生顺序的时刻、各段实际间隔（≥ 最短通行）与是否落在原区间内
    ordered = [
        {"position": i + 1, "event": name, "place": place_of[name], "minute": minutes[name]}
        for i, name in enumerate(itinerary)
    ]
    row_pairs: dict[tuple[str, str], list[Row]] = {}
    for r in rows:
        row_pairs.setdefault((r.a, r.b), []).append(r)

    segment_checks: list[dict] = []
    for seg in segments:
        actual = minutes[seg["to_event"]] - minutes[seg["from_event"]]
        direct = row_pairs.get((seg["from_event"], seg["to_event"]), [])
        covering = [
            {
                "line": r.line,
                "a": r.a,
                "b": r.b,
                "low": r.low,
                "high": r.high,
                "satisfied": r.low <= actual <= r.high,
            }
            for r in direct
        ]
        segment_checks.append({
            **seg,
            "actual_minutes": actual,
            "slack_minutes": actual - seg["travel_minutes"],
            "interval_lines": covering,
        })

    # 逐条区间核对（与 /api/solve 同口径，时间线为联立通行下界后的可行解）
    differences = [
        {
            "line": r.line,
            "a": r.a,
            "b": r.b,
            "low": r.low,
            "high": r.high,
            "actual": dist[index[r.b]] - dist[index[r.a]],
        }
        for r in rows
    ]

    return {
        "status": "ok",
        "message": (
            f"行程共 {len(itinerary)} 个事件、{len(segments)} 个相邻事件段：各段最短通行时间作为下界"
            "与原区间联立无矛盾，以下时间线满足全部时间差区间与通行下界（最早事件为第 0 分钟）。"
        ),
        "itinerary": itinerary,
        "segments": segment_checks,
        "timeline": timeline,
        "ordered_itinerary": ordered,
        "differences": differences,
        **counts,
    }


# ---------- 有序事件最大统一间隔 ----------

def parse_order(text: str) -> tuple[list[str], list[dict]]:
    """按希望保持的先后顺序解析事件名：每行一个事件，至少两个、互不相同。

    返回 (事件名列表, 错误列表)；空行跳过但行号保留为顺序文本的原始行号。
    同一事件重复出现为错误（先后顺序应是互不相同的事件序列）。
    """
    errors: list[dict] = []
    events: list[str] = []

    if not text or not text.strip():
        return events, [{"line": None, "message": "事件顺序输入为空：请按希望保持的先后顺序逐行填写事件名（每行一个，至少两个、互不相同）。"}]

    seen: dict[str, int] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue  # 空行不计入校验，但行号保留为顺序文本的原始行号

        # 兼容误写成“事件,”（或“事件，”）的两字段形式：取首个非空字段
        parts = [p.strip() for p in line.replace("，", ",").split(",")]
        if len(parts) > 2 or (len(parts) == 2 and parts[1] != ""):
            errors.append({
                "line": line_no,
                "message": f"事件顺序第{line_no}行：每行只填写一个事件名，实际得到 {len(parts)} 个字段（“{line}”）。",
            })
            continue
        name = parts[0]
        if not name:
            errors.append({"line": line_no, "message": f"事件顺序第{line_no}行：事件名为空。"})
            continue
        if name in seen:
            errors.append({
                "line": line_no,
                "message": (
                    f"事件顺序第{line_no}行：事件“{name}”重复出现"
                    f"（已在第{seen[name]}行出现）；先后顺序中的事件必须互不相同。"
                ),
            })
            continue
        seen[name] = line_no
        events.append(name)

    if not errors and len(events) < 2:
        errors.append({
            "line": None,
            "message": f"事件顺序至少需要两个互不相同的事件，实际得到 {len(events)} 个。",
        })
    return events, errors


def _order_step(names: list[str], e: Edge) -> dict:
    """顺序间隔边的可读步骤：从后一事件指向前一事件，含义为相邻所选事件的统一间隔下界。"""
    # Edge(后一事件 -> 前一事件, -g)：bound 为统一间隔 g，label 复用为相邻对序号（1 起）
    pos = int(e.label)
    return {
        "from": names[e.u],
        "to": names[e.v],
        "weight": e.w,
        "line": None,  # 顺序间隔不来自区间文本，行号显式置空
        "kind": "order",
        "kind_label": "顺序间隔",
        "bound": e.bound,
        "source": "order",
        "position": pos,
        "relation": f"{names[e.u]}−{names[e.v]} ≥ {e.bound}（第 {pos} 对相邻所选事件保持先后）",
    }


def _maxgap_step(names: list[str], e: Edge) -> dict:
    """同时认识区间边与顺序间隔边的矛盾链步骤构建器。"""
    if e.kind == "order":
        return _order_step(names, e)
    return _edge_step(names, e)


def _maxgap_timeline(names: list[str], dist: list[int]) -> list[dict]:
    """把一组可行势差平移到最早事件为第 0 分钟，并按 (分钟, 事件名) 排序。"""
    base = min(dist)
    timeline = [{"event": names[i], "minute": dist[i] - base} for i in range(len(names))]
    timeline.sort(key=lambda x: (x["minute"], x["event"]))
    return timeline


def solve_max_gap(text: str, order_text: str) -> dict:
    """有序事件最大统一间隔：求最大的非负整数 g，使每对相邻所选事件至少相隔 g 分钟。

    区间文本沿用首页事件区间（parse_text 的现有校验，含空文本报错）；顺序文本每行
    一个事件名（至少两个、互不相同、已在区间中出现），表示希望保持的先后顺序。
    对给定的 g，为每对相邻所选事件（前一事件 a、后一事件 b）加一条间隔下界边
    b -> a、权 -g（即 t(b) − t(a) ≥ g），与原区间复用同一套差分约束 Bellman-Ford 联立：

    - 原区间语法错误：沿用 parse_text 的逐行错误；原区间自身矛盾：沿用 solve_rows
      的现有闭合矛盾链（尚未加入间隔边，status 为 interval_conflict）；
    - 原区间可行但 g=0 已不可行：所选先后顺序与原区间不相容，返回含顺序间隔环节的
      闭合矛盾链（status 为 order_conflict）；
    - 没有任何间隔边落在环上（原区间对这些间隔给不出上界）：g 无有限上限，
      返回无上限结论与 g=0 的一条可行时间线（status 为 unbounded）；
    - 否则先指数放大找到不可行的上界、再在整数范围内二分最大的可行 g，返回 g 与
      一条达到该间隔的完整可行时间线（最早事件为第 0 分钟）。
    """
    rows, errors = parse_text(text)  # 区间文本复用现有校验
    order, order_errors = parse_order(order_text)
    errors = errors + order_errors

    # 所选事件须已在区间中出现（区间/顺序文本本身有错时先报那些错，避免噪音）
    if not errors:
        known = {r.a for r in rows} | {r.b for r in rows}
        for pos, name in enumerate(order, start=1):
            if name not in known:
                errors.append({
                    "line": None,
                    "message": f"事件顺序第 {pos} 个事件“{name}”未在区间文本中出现：所选事件须已在区间中出现。",
                })
    if errors:
        return {"status": "error", "errors": errors}

    # 原区间先独立联立：自身矛盾时沿用现有闭合矛盾链（与顺序无关，不混入间隔边）
    system = solve_rows(rows)
    if system["status"] != "ok":
        return {
            "status": "interval_conflict",
            "message": "上方时间差区间自身已互相矛盾（尚未加入顺序间隔约束），先返回现有闭合矛盾链；请先消除区间冲突，再查询最大统一间隔。",
            "conflict": system["conflict"],
            "order": order,
            "order_count": len(order),
            "line_count": len(rows),
        }

    names = system["names"]
    index = system["index"]
    base_edges = system["edges"]
    order_idx = [index[name] for name in order]

    def augmented_edges(g: int) -> list[Edge]:
        # 每对相邻所选事件（前 a、后 b）加间隔下界边 b -> a，权 -g；label 为相邻对序号
        edges = list(base_edges)
        for i in range(len(order_idx) - 1):
            edges.append(Edge(order_idx[i + 1], order_idx[i], -g, -1, "order", g, "order", str(i + 1)))
        return edges

    def feasible(g: int) -> bool:
        _, _, last_relaxed = _relax_all(names, augmented_edges(g))
        return last_relaxed is None

    pair_descs = [
        {"position": i + 1, "from": order[i], "to": order[i + 1]}
        for i in range(len(order) - 1)
    ]
    meta = {
        "order": order,
        "pairs": pair_descs,
        "order_count": len(order),
        "event_count": len(names),
        "line_count": len(rows),
    }

    # g=0：只要求保持先后顺序；不可行即顺序冲突（负环必含至少一条间隔边）
    dist0, pred0, last0 = _relax_all(names, augmented_edges(0))
    if last0 is not None:
        result = _conflict_result(names, pred0, last0, len(names), step_builder=_maxgap_step)
        return {
            "status": "order_conflict",
            "message": (
                "原区间本身可行，但所选的先后顺序连 g=0（只保持先后、不要求间隔）都无法满足："
                "闭合矛盾链中含顺序间隔环节（标注相邻对序号），即原区间已迫使某些后选事件"
                "必须早于其前选事件。"
            ),
            "conflict": result["conflict"],
            **meta,
        }

    # 有界性：某条间隔边 b -> a 落在环上 <=> 图中 a 可达 b（原区间经其他边给出该间隔的
    # 上界）。间隔边只从后选事件指向前选事件，任何含间隔边的环必含区间边；没有任何
    # 间隔边在环上时，任意大的 g 都不会产生负环，g 无有限上限。
    adj: dict[int, list[int]] = {}
    for e in augmented_edges(0):
        adj.setdefault(e.u, []).append(e.v)

    def reaches(src: int, dst: int) -> bool:
        if src == dst:
            return True
        seen = {src}
        stack = [src]
        while stack:
            x = stack.pop()
            for y in adj.get(x, ()):
                if y == dst:
                    return True
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return False

    bounded = any(
        reaches(order_idx[i], order_idx[i + 1])
        for i in range(len(order_idx) - 1)
    )

    def gaps_of(timeline: list[dict]) -> list[dict]:
        minute_of = {t["event"]: t["minute"] for t in timeline}
        return [
            {
                "position": i + 1,
                "from": order[i],
                "to": order[i + 1],
                "actual": minute_of[order[i + 1]] - minute_of[order[i]],
            }
            for i in range(len(order) - 1)
        ]

    def differences_of(dist: list[int]) -> list[dict]:
        return [
            {
                "line": r.line,
                "a": r.a,
                "b": r.b,
                "low": r.low,
                "high": r.high,
                "actual": dist[index[r.b]] - dist[index[r.a]],
            }
            for r in rows
        ]

    if not bounded:
        # 无上限：任意大的 g 都可行；按约定给出 g=0（保持先后顺序）的一条可行时间线
        timeline = _maxgap_timeline(names, dist0)
        return {
            "status": "unbounded",
            "bounded": False,
            "g": None,
            "timeline_g": 0,
            "message": (
                "原区间对所选的相邻事件间隔给不出任何上界：g 没有有限上限（任意大的统一间隔"
                "都可安排）；以下给出 g=0（只保持先后顺序）的一条可行时间线。"
            ),
            "timeline": timeline,
            "gaps": gaps_of(timeline),
            "differences": differences_of(dist0),
            **meta,
        }

    # 二分最大的可行整数 g：先指数放大找到不可行的上界，再在 (可行, 不可行] 间二分
    lo, hi = 0, 1
    while feasible(hi):
        lo = hi
        hi *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if feasible(mid):
            lo = mid
        else:
            hi = mid
    g_max = lo

    dist, _, _ = _relax_all(names, augmented_edges(g_max))
    timeline = _maxgap_timeline(names, dist)
    return {
        "status": "ok",
        "bounded": True,
        "g": g_max,
        "timeline_g": g_max,
        "message": (
            f"最大统一间隔 g = {g_max} 分钟：以下时间线满足全部原区间，且所选顺序每对相邻"
            f"事件至少相隔 {g_max} 分钟；再增大 1 分钟即不可行。"
        ),
        "timeline": timeline,
        "gaps": gaps_of(timeline),
        "differences": differences_of(dist),
        **meta,
    }
