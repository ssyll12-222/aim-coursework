# aim-py-cw
# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from collections import deque
from enum import Enum
# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]
# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """血量百分比，返回 0-100 的 int。"""
    try:
        ratio = int(round(100.0 * hp / max_hp))
    except (TypeError, ZeroDivisionError):
        return 0
    return max(0, min(100, ratio))


def status_report(name, robot_type, hp, max_hp, battery):
    """一行自检报告字符串：名称|机型|HP|电量|档位。"""
    battery = int(battery)
    if battery >= 50:
        level = "OK"
    elif battery >= 20:
        level = "WARNING"
    else:
        level = "LOW"
    return "{name:<10}|{rtype:^10}|HP {hp:>3}%|BAT {bat:>3}%|{lvl}".format(
        name=name, rtype=robot_type, hp=hp_ratio(hp, max_hp),
        bat=battery, lvl=level)
# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
_ARMOR_KEYS = ("front", "left", "right")
_SENSOR_KEYS = {"F": "front", "L": "left", "R": "right"}


def _parse_sensor_line(line):
    """解析 "F:32,L:5,R:12" 形式的传感器行；非法返回 None。"""
    hits = {}
    for seg in line.split(","):
        seg = seg.strip()
        if ":" not in seg:
            return None
        key, _, value = seg.partition(":")
        key = key.strip()
        value = value.strip()
        if key not in _SENSOR_KEYS or not value.isdigit():
            return None
        damage = int(value)
        if damage <= 0:
            return None
        hits[_SENSOR_KEYS[key]] = hits.get(_SENSOR_KEYS[key], 0) + damage
    return hits or None


def _parse_json_line(line):
    """解析 JSON 伤害行；非法返回 None。合法返回 (armor, damage, id|_NO_ID)。"""
    try:
        obj = json.loads(line)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    armor = obj.get("armor")
    damage = obj.get("damage")
    if armor not in _ARMOR_KEYS:
        return None
    if not isinstance(damage, int) or isinstance(damage, bool) or damage <= 0:
        return None
    return armor, damage, obj.get("id", _NO_ID)


class _NoId:
    pass


_NO_ID = _NoId()


def analyze_damage_log(lines):
    """解析混合格式伤害日志，返回固定契约的统计 dict。"""
    total = 0
    events = 0
    by_armor = {"front": 0, "left": 0, "right": 0}
    seen_ids = set()
    for line in lines:
        if not isinstance(line, str):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = _parse_json_line(stripped)
        if parsed is not None:
            armor, damage, event_id = parsed
            if event_id is not _NO_ID:
                try:
                    if event_id in seen_ids:
                        continue
                    seen_ids.add(event_id)
                except TypeError:
                    continue
            by_armor[armor] += damage
            total += damage
            events += 1
            continue
        hits = _parse_sensor_line(stripped)
        if hits is not None:
            for armor, damage in hits.items():
                by_armor[armor] += damage
                total += damage
            events += 1
    most_hit = None
    if events:
        most_hit = max(_ARMOR_KEYS, key=lambda a: by_armor[a])
    return {"total": total,
            "by_armor": by_armor,
            "most_hit": most_hit,
            "avg": round(total / events, 2) if events else 0.0}
# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """位置 setter：只接受长度为 2 的 tuple/list，元素规范化后以 tuple 存储。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 需要长度为 2 的 tuple/list")
        self._pos = (int(value[0]), int(value[1]))

    def move_forward(self):
        """朝当前 facing 前进一格，返回执行后的位置。

        前方被障碍或边界挡住：位置与朝向不变，collision_count 加 1；
        成功前进消耗 1 单位电量；电量耗尽后底盘断电，不再位移。
        """
        if self._fuel <= 0:
            return self._pos
        dx, dy = self._facing.delta
        nx, ny = self._pos[0] + dx, self._pos[1] + dy
        if self.is_blocked(nx, ny):
            self._collision_count += 1
            return self._pos
        self._pos = (nx, ny)
        self._fuel -= 1
        return self._pos

    def turn_left(self):
        """原地左转 90°，返回新的 Facing（不耗电）。"""
        left_of = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
                   Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
        self._facing = left_of[self._facing]
        return self._facing

    def turn_right(self):
        """原地右转 90°，返回新的 Facing（不耗电）。"""
        right_of = {Facing.UP: Facing.RIGHT, Facing.RIGHT: Facing.DOWN,
                    Facing.DOWN: Facing.LEFT, Facing.LEFT: Facing.UP}
        self._facing = right_of[self._facing]
        return self._facing
# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """返回下一步应朝向的 Facing。

    候选方向：相邻格不是障碍、且移动到该格后到目标的曼哈顿距离严格减小；
    多候选时先走与目标坐标差较大的轴；无候选时返回 current_facing。
    本函数不感知地图边界。
    """
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    dist = abs(dx) + abs(dy)
    candidates = []
    if dx != 0:
        candidates.append((abs(dx), 0,
                           Facing.RIGHT if dx > 0 else Facing.LEFT))
    if dy != 0:
        candidates.append((abs(dy), 1,
                           Facing.UP if dy > 0 else Facing.DOWN))
    # 坐标差较大的轴优先；平局时 x 轴优先。
    candidates.sort(key=lambda item: (-item[0], item[1]))
    for _, _, facing in candidates:
        d = facing.delta
        nxt = (pos[0] + d[0], pos[1] + d[1])
        if nxt in obstacles:
            continue
        if abs(nxt[0] - target[0]) + abs(nxt[1] - target[1]) < dist:
            return facing
    return current_facing
# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


_RETREAT_HP_PCT = 30    # R1：血量百分比不高于此值必须撤退
_SAFE_HP_PCT = 80       # R2：撤退中恢复到此值以上视为安全
_ENGAGE_DIST = 3        # R4/R6：敌距不超过此值开火


def _normalize_sensor(sensor):
    """校验 sensor 契约并规范化字段；契约外输入 raise ValueError。"""
    if not isinstance(sensor, dict):
        raise ValueError("sensor 必须是 dict")
    missing = {"enemy_frames", "enemy_dist",
               "robot_type", "max_hp"} - set(sensor)
    if missing:
        raise ValueError("sensor 缺少字段: {}".format(sorted(missing)))
    frames = sensor["enemy_frames"]
    if not isinstance(frames, (tuple, list)) or not 1 <= len(frames) <= 6:
        raise ValueError("enemy_frames 必须是长度 1-6 的 tuple/list")
    frames = [bool(f) for f in frames]
    dist = sensor["enemy_dist"]
    if not isinstance(dist, int) or isinstance(dist, bool) or dist < 0:
        dist = None
    robot_type = sensor["robot_type"]
    if robot_type not in ("INFANTRY", "HERO"):
        robot_type = "INFANTRY"
    return frames, dist, robot_type


def _engage_action(dist, robot_type):
    """R4/R6 共用：交火中的动作选择。"""
    if dist is not None and dist <= _ENGAGE_DIST:
        return "SHOOT"
    return "MOVE_RIGHT" if robot_type == "HERO" else "MOVE_LEFT"


def decide(sensor, state, hp, heat):
    """纯函数决策：按 R1-R7 顺序求值，首条命中即返回 (action, new_state)。"""
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")
    frames, dist, robot_type = _normalize_sensor(sensor)
    max_hp = sensor["max_hp"]
    hp_pct = hp_ratio(hp, max_hp)
    visible = frames[-1]

    # R1（保命优先）
    if hp_pct <= _RETREAT_HP_PCT:
        return ("RETREAT", SentryState.RETREAT)
    # R2（撤退保持）
    if state is SentryState.RETREAT:
        if hp_pct >= _SAFE_HP_PCT:
            return ("RETURN", SentryState.RETURN)
        return ("RETREAT", SentryState.RETREAT)
    # R3（返航单帧）
    if state is SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)
    if state is SentryState.ENGAGE:
        if visible:
            # R4（交火决策）
            return (_engage_action(dist, robot_type), SentryState.ENGAGE)
        # R5（交火保持）：统计末尾连续丢失帧数
        lost = 0
        for seen in reversed(frames):
            if seen:
                break
            lost += 1
        if lost <= 1:
            return ("HOLD_FIRE", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)
    # PATROL / SUSPECT
    if visible:
        # R6（敌情确认）：末两位均为真才转入交火
        if len(frames) >= 2 and frames[-2]:
            return (_engage_action(dist, robot_type), SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)
    # R7（默认行为）
    if state is SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)
# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def _border_ring(width, height):
    """地图外一圈虚拟障碍，让贪心/沿墙都不越界。"""
    ring = set()
    for x in range(-1, width + 1):
        ring.add((x, -1))
        ring.add((x, height))
    for y in range(-1, height + 1):
        ring.add((-1, y))
        ring.add((width, y))
    return ring


def run_patrol(grid, max_steps=500):
    """sense → decide → act 主循环：贪心导航 + 沿墙脱困 + BFS 兜底。

    终止：抵达 enemy_pos / 步数用尽 / 电量耗尽。
    脱困分两层：
    1. 贪心无候选时切入沿墙模式（左右手规则），距离重新可缩短时切回贪心；
       沿墙超过一圈未脱困则换手，两圈后强制退出，再次入墙时换另一只手；
    2. 全局看门狗：长时间没有刷新"离目标最近距离"说明陷入循环，
       此后按 BFS 距离场（对 enemy 的一次反向 BFS）逐步逼近，保证连通图必达。
    """
    enemy = grid.enemy_pos
    blocked_cells = set(grid.obstacles) | _border_ring(grid.width,
                                                       grid.height)
    left_of = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
               Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
    right_of = {v: k for k, v in left_of.items()}
    limit = grid.width + grid.height

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def blocked(cell):
        return cell in blocked_cells

    def cell_from(pos, facing):
        d = facing.delta
        return (pos[0] + d[0], pos[1] + d[1])

    # 以 enemy 为源做一次反向 BFS，得到每个格到 enemy 的真实最短路长度。
    dist_field = {enemy: 0}
    queue = deque([enemy])
    while queue:
        cx, cy = queue.popleft()
        for nxt in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if blocked(nxt) or nxt in dist_field:
                continue
            dist_field[nxt] = dist_field[(cx, cy)] + 1
            queue.append(nxt)

    def greedy_dir(pos):
        direction = next_step_toward(pos, enemy, blocked_cells, grid.facing)
        nxt = cell_from(pos, direction)
        if blocked(nxt):
            return None
        if manhattan(nxt, enemy) >= manhattan(pos, enemy):
            return None
        return direction

    def bfs_dir(pos):
        best_dir, best_len = None, None
        for f in (Facing.UP, Facing.DOWN, Facing.LEFT, Facing.RIGHT):
            nxt = cell_from(pos, f)
            length = dist_field.get(nxt)
            if length is None:
                continue
            if best_len is None or length < best_len:
                best_dir, best_len = f, length
        return best_dir

    def align(target):
        rights = {Facing.UP: 0, Facing.RIGHT: 1,
                  Facing.DOWN: 2, Facing.LEFT: 3}
        diff = (rights[target] - rights[grid.facing]) % 4
        if diff == 3:
            grid.turn_left()
        else:
            for _ in range(diff):
                grid.turn_right()

    visited = set()
    steps = 0
    wall = False
    hand = "L"
    wall_steps = 0
    entry = 0
    best = manhattan(grid.current_pos, enemy)
    last_progress = 0
    bfs_mode = False
    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos
        visited.add(pos)
        dist_now = manhattan(pos, enemy)
        if dist_now < best:
            best = dist_now
            last_progress = steps
        if not bfs_mode and steps - last_progress > limit // 2:
            bfs_mode = True
            wall = False
        if bfs_mode:
            direction = bfs_dir(pos)
            if direction is None:
                break  # 目标不可达（正常不会发生：生成器保证连通）
            align(direction)
        elif not wall:
            direction = greedy_dir(pos)
            if direction is None:
                wall = True
                wall_steps = 0
                entry = dist_now
            else:
                align(direction)
        if wall:
            facing = grid.facing
            side = left_of[facing] if hand == "L" else right_of[facing]
            opposite = right_of[facing] if hand == "L" else left_of[facing]
            if not blocked(cell_from(pos, side)):
                align(side)
            elif blocked(cell_from(pos, facing)):
                if not blocked(cell_from(pos, opposite)):
                    align(opposite)
                else:
                    grid.turn_right()
                    grid.turn_right()
        grid.move_forward()
        steps += 1
        if wall:
            wall_steps += 1
            if wall_steps > 2 * limit:
                wall = False
                hand = "R" if hand == "L" else "L"  # 下次入墙换手
            elif wall_steps > limit:
                hand = "R" if hand == "L" else "L"
                wall_steps = 0
            elif (greedy_dir(grid.current_pos) is not None
                    and manhattan(grid.current_pos, enemy) < entry):
                wall = False
    visited.add(grid.current_pos)
    found = grid.found_enemy
    return {"steps": steps,
            "collisions": grid.collision_count,
            "visited_count": len(visited),
            "found_enemy": found,
            "success": found}


def report_to_json(stats):
    """把 stats 序列化为确定性的 JSON 字符串（键排序）。"""
    return json.dumps(stats, sort_keys=True)
# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    raise NotImplementedError("Bonus bfs_path_length")
# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
