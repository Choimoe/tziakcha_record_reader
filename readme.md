# 雀渣牌谱统计 tziakcha_record_reader

本项目用于抓取并解析 tziakcha 平台的对局数据，生成便于分析与统计的本地数据与报表。核心功能包括：
- 单条对局记录下载与解析（`main.py`）
- 历史列表抓取（需要 Cookie）（`history.py`）
- 根据历史列表筛选对局（`select_session.py`）
- 将“场次”转为“具体对局记录ID列表”（`session.py`）
- 批量下载并解析所有记录（`batch_process.py`）
- 生成统计 CSV（可选，`generate_stats.py`）

环境要求：Python 3.9+

```bash
pip install requests
```

## 快速开始

### 1）抓取历史列表（需要登录 Cookie）

1. 登录 https://tziakcha.net/history/，抓取浏览器 Cookie。
2. 将 Cookie 赋值给环境变量 `TZI_HISTORY_COOKIE`（只需包含服务端需要的 Cookie 串）。

```bash
export TZI_HISTORY_COOKIE='__p=[你的Cookie]'
python history.py
```

运行成功后生成 `record_lists.json`，包含历史场次列表。

### 2）筛选你关心的场次

`select_session.py` 默认筛选标题中包含“竹”的场次：

```bash
python select_session.py
```

生成 `selected.json`：形如 `[{"id": "<场次id>", "title": "..."}, ...]`

若要自定义规则，直接修改 `select_session.py` 中的匹配条件（例如按时间、关键字、人数等）。

### 3）将场次展开为具体对局记录ID

`session.py` 会把每个场次展开为多条对局记录的小 id，并写入 `all_record.json`：

```bash
python session.py
```

生成：
- `all_record.json`：`["PgTyUuSQ", "...", ...]`（小 id 列表）

### 4）批量下载并解析所有记录

```bash
python batch_process.py
```

行为：
- 若 `data/origin/<id>.json` 不存在则下载 `/record/?id=<id>` 的原始响应并保存到 `data/origin/`。
- 调用 `parser.py` 解析脚本数据，保存到 `data/record/<id>.json`。
- 同时在控制台输出对局过程与结果（和牌信息、花数校验等）。

### 5）单条记录调试

```bash
python main.py <record_id>
```

行为：
- 若本地无 `data/origin/<record_id>.json` 则自动下载并保存。
- 解析并打印过程分析，便于逐条定位问题（吃/碰/杠/补花/和牌）。

### 6）生成统计报表（可选）

```bash
python generate_stats.py
```

输出：
- `win_stats.csv`（UTF‑8）
- `win_stats_bom.csv`（UTF‑8‑BOM，Excel 友好）

字段包含：
- 和牌者、基础番、花牌数、总番、手牌+副露、和牌张、所属局等。