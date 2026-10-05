# AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块

> **全部题目、规范、评分、提交见 [题面.pdf](题面.pdf)。** 本 README 只讲怎么把环境跑起来；没在这里出现的规格细节，一律以题面为准。

## 1. 环境要求

- Python 3.8+，仅标准库（不允许第三方运行时依赖）；
- 开发工具只需 `pytest`（测试）与 `autopep8`（风格，CI 会检查）；
- VS Code 打开仓库会推荐安装 `ms-python.autopep8` 插件（`.vscode/extensions.json`），保存即格式化即可过风格检查。

## 2. 快速开始

```bash
# 1. 用 GitHub 的 Use this template 创建你自己的仓库，然后 clone
git clone https://github.com/<你的用户名>/<你的仓库>.git
cd <你的仓库>   # 直接在 main 分支上开发

# 创建虚拟环境

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. 装依赖
python -m pip install pytest autopep8

# 3. 启用 AI 会话归档钩子（课程要求，见下方第 3 节）
python -m pip install 'agent-session-commit[pre-commit]==0.1.3' -i https://pypi.org/simple
agent-session-commit install --pre-commit   # 交互选择你的 AI 助手与会话目录

# 4. 跑测试（刚到手：全部 skip，CI 是绿的）
python -m pytest

# 5. 看演示
python main.py

# 6. 打开 题面.pdf 读题，开始实现 src/main/__init__.py 里的 TODO
```

## 3. AI 会话归档（pre-commit）

本课程允许使用 AI，提交的 commit 需要携带 AI 会话归档作为透明化记录：每次 `git commit` 后，钩子会把新增会话自动 amend 进同一个提交（`.agent-sessions/bundles/`），不产生额外的归档提交。支持 Claude Code、OpenAI Codex CLI、GitHub Copilot CLI、Qoder、ZCode、Trae、Tencent CodeBuddy 等（完整名单见 [AgentLedger](https://github.com/Gentle-Lijie/AgentLedger)）。

- 配置是仓库本地的：每个 clone 运行一次 `agent-session-commit install --pre-commit`，方向键选择 agent、确认其会话目录即可；
- 不想用 TUI 可手动配置：`git config --local agent-session.agent claude`、`git config --local agent-session.source "<会话目录>"`，然后 `python -m pip install 'pre-commit>=3.2.0' && pre-commit install`；
- 归档是普通 Git 内容且会推送到公开仓库——不要在 AI 会话里粘贴令牌等敏感信息；
- 换了 agent 或目录就重跑一次安装命令；卸载：从 `.pre-commit-config.yaml` 移除该条目后重跑 `pre-commit install`。

## 4. 本地开发循环

- **写代码**：全部作业在 `src/main/__init__.py`，按题面各题规范补全每个标有 TODO 的函数；注释里标注了对应的题面主题，推荐顺序 Q1 → Q6。
- **跑测试**：`python -m pytest` —— 可见测试是规格书的一部分，未实现的函数自动 skip，实现一个、对应测试亮一个。本地全绿 ≠ 满分（见题面）。
- **看演示**：`python main.py`（等价于 `PYTHONPATH=src python -m main`），随实现进度逐段点亮，不进测试。
- **Q6 自测**：`python tools/run_seeds.py --q6`（200 张固定地图统计），单 seed 渲染 `python tools/run_seeds.py --q6 --seed <N> --render`，Bonus 模式 `python tools/run_seeds.py --bonus`。

## 5. 仓库结构（哪些能改）

| 路径 | 说明 | 能否修改 |
|---|---|---|
| `src/main/__init__.py` | 你的全部作业（TODO 所在） | ✅ |
| `README.md` | 仅末尾两个"你来写"小节 | ✅ |
| `题面.pdf` | 题面（唯一规格说明） | ❌ 勿改 |
| `src/main/legacy_patrol.py` | Q7 模块（与主体同步发布，修复其缺陷） | Q7 时 ✅ |
| `.pre-commit-config.yaml` | AI 会话归档钩子配置 | ❌ 勿改 |
| `src/tests/`、`tools/`、`.github/`、`conftest.py`、`pytest.ini`、`main.py` | 测试与基础设施 | ❌ 勿改 |

CI 只允许修改 `src/main/**`、`README.md` 与 `.agent-sessions/**`（AI 会话归档）——其余文件改了直接红；autopep8 `--diff` 非空即败。提交方式（push、问卷、commit 粒度）见题面"提交与验收"一节。

## Q7 修复分析（你来写）

`src/main/legacy_patrol.py` 共 6 处缺陷，全部以各函数 docstring 契约为基准定位与修复：

1. **`total_route_meters`：单位混淆。** `segment_length_cm` 返回厘米，累加后未除以 100 就当"米"返回，结果放大 100 倍。定位：可见测试期望 `[(0,0),(3,0),(3,4)]` 得到 7，实得 700，对照 docstring"单位：米"。
2. **`calibrate`：无正样本时崩溃。** `first_positive` 没有正数时返回 `None`，随后 `s - baseline` 抛 `TypeError`，与契约"样本为空或没有正样本时漂移为 0"矛盾。修复：`baseline is None` 时直接返回 0。定位：`test_calibrate_no_positive`。
3. **`log`：可变默认参数。** `history=[]` 在函数定义时只创建一次，多次调用共享同一个列表，违反"不显式传入时每次从空历史开始"。修复：默认 `None`，函数体内新建列表。定位：`test_log_default_history_independent` 中连续调用结果互相污染。
4. **`summarize_events`：边界漏统计。** 契约是"id **不超过** max_id"，代码写成 `e["id"] < max_id`，恰等于 max_id 的事件被漏掉，应为 `<=`。定位：`test_summarize_includes_max_id`。
5. **`run_legacy_sim`：死循环。** 循环变量 `round_` 从不自增，`while round_ < rounds` 恒真——这就是题目背景里"有的调用甚至卡死"的来源。定位：直接读循环体，发现没有任何语句修改 `round_`。
6. **`run_legacy_sim`：终止条件写反。** 契约是"任一轮结束后体力 <= 20 时立即终止"，代码写成 `if stamina > 20: break`，方向恰好相反：体力充足反而第一轮就退出。它与第 5 处互相遮蔽——死循环不修，根本观察不到这条；这也正是 git log 里那次标注 fix、实际改错方向的提交。定位：修复死循环后用 `test_sim_basic_run` / `test_sim_stops_at_threshold` 对拍 trace。

## 设计说明（你来写）

- **Q6 巡逻策略分三层**：主导航用 Q4 贪心（每步只看四邻域，开销最小）；贪心失速（四邻域没有严格减距方向）时切入沿墙模式，左右手规则贴墙绕行，记录入墙时的曼哈顿距离，距离重新可缩短即切回贪心；沿墙超过 `宽+高` 步未脱困则换手，两圈后强制退出，再次入墙换另一只手，避免在同一死角里用同一只手反复绕圈。最后一层是全局看门狗：若连续 `（宽+高）/2` 步没有刷新"离目标最近距离"，判定陷入循环，切换到以 enemy 为源预计算的 BFS 距离场逐步逼近——地图由生成器保证连通，因此该兜底保证必达。200 张固定地图自测：成功率 100%，平均碰撞 0，步数/BFS 比约 1.13。
- **`report_to_json`**：`json.dumps(stats, sort_keys=True)`，键序固定，输出确定性。
- **Q5 决策机**：严格按 R1–R7 顺序短路求值，首条命中即返回；契约外输入（空帧历史、帧长超 6、非法 state、缺字段）抛 `ValueError`，字段存在但取值非法则防御式规范化（非法敌距视为未知、非法机型按步兵处理），不抛异常。
- **Q2 日志解析**：JSON 行优先于传感器行判定；两种解析器各自独立返回 `None` 表示脏行，主循环只负责累计，保证全程不抛异常；带 id 的 JSON 行用集合按 id 去重（不可哈希的 id 视为脏行）。

