<div align="center">

<img src="docs/logo.svg" alt="MindWeaver Logo" width="64"/>

# MindWeaver

*汇聚信息，提炼洞察*

**个人知识/研究动态监测工具**

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.4.0-orange.svg)](https://github.com/NeoCoder97/mind-weaver)

</div>

---

自动化抓取、去重、存储和检索 RSS/Atom 订阅源内容的轻量化工具。

---

## 特性

- 🚀 **自动化抓取** - 定时抓取 RSS/Atom 订阅源
- 🔄 **智能去重** - 基于链接/标题/内容的多层次去重
- 📊 **结构化存储** - SQLite 数据库持久化
- 🌐 **多语言支持** - 自动检测中文、英文、日文等内容
- ⏱️ **阅读时间估算** - 自动计算文章阅读时长
- 🌐 **Web 管理界面** - 可视化管理和控制
- 📝 **内容提取** - 自动抓取完整文章内容
- 🏷️ **关键词提取** - 自动提取关键词标签
- 📋 **过滤规则** - 基于关键词/正则/标签/语言的过滤
- 🤖 **AI 摘要** - 可选的 AI 摘要生成
- 📁 **分类管理** - 订阅源分类组织和个性化设置
- ⚙️ **个性化设置** - 每个订阅源独立配置（条目限制、仅获取最新等）

---

## 安装

### 系统要求

- Python 3.14 或更高版本
- uv（推荐的包管理器）或 pip

### 使用 uv（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/NeoCoder97/mind-weaver.git
cd mind-weaver

# 2. 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安装依赖
uv sync

# 4. 启动应用
uv run mind-weaver
```

### 使用 pip

```bash
# 1. 克隆仓库
git clone https://github.com/NeoCoder97/mind-weaver.git
cd mind-weaver

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -e .

# 4. 启动应用
mind-weaver
```

### 启用 AI 摘要（可选）

```bash
uv sync --all-extras
# 或
pip install -e ".[ai]"
```

---

## 快速开始

### 1. 启动 Web 应用

```bash
uv run mind-weaver
```

或指定 host 和 port：

```bash
# 设置环境变量
export MIND_WEB_HOST=0.0.0.0
export MIND_WEB_PORT=8000

# 启动应用
uv run mind-weaver
```

启动后访问：http://127.0.0.1:8000

### 2. 添加订阅源

在 Web 界面中：
1. 点击 "Feeds" 标签
2. 点击 "+ Add Feed" 按钮
3. 输入订阅源 URL（会自动检测元数据）
4. 配置名称、描述、抓取间隔、分类等
5. 可选：设置条目限制、仅获取最新内容
6. 点击 "Create Feed"

### 3. 管理分类

在 Web 界面中：
1. 点击 "Categories" 标签
2. 点击 "+ 添加分类" 创建新分类
3. 可设置颜色和图标自定义分类外观
4. 在添加/编辑订阅源时指定分类
5. 分类可启用/禁用，禁用后该分类下所有订阅源暂停抓取

### 4. 启动调度器

在 Dashboard 页面：
1. 点击 "Start Scheduler" 按钮启动自动抓取
2. 调度器会根据每个订阅源的间隔自动抓取
3. 点击 "Fetch All Now" 可以立即抓取所有订阅源

### 5. 管理条目

- **Entries** 页面：查看所有抓取的条目
- **Dashboard** 页面：查看统计信息和最近活动
- **Rules** 页面：配置过滤规则

---

## 配置

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| **Web 配置** | | |
| `MIND_WEB_HOST` | Web 服务器地址 | `127.0.0.1` |
| `MIND_WEB_PORT` | Web 服务器端口 | `8000` |
| `MIND_WEB_DEBUG` | 调试模式 | `False` |
| `MIND_WEB_SECRET_KEY` | Flask secret key | 自动生成 |
| **数据库配置** | | |
| `MIND_DB_TYPE` | 数据库类型 (sqlite/postgresql/mysql) | `sqlite` |
| `MIND_DB_PATH` | SQLite 数据库文件路径 | `data/spider_aggregation.db` |
| `MIND_DB_HOST` | 数据库主机（PostgreSQL/MySQL） | `localhost` |
| `MIND_DB_PORT` | 数据库端口 | `5432` / `3306` |
| `MIND_DB_NAME` | 数据库名称 | `spider_aggregation` |
| `MIND_DB_USER` | 数据库用户名 | - |
| `MIND_DB_PASSWORD` | 数据库密码 | - |
| **调度器配置** | | |
| `MIND_SCHEDULER_TIMEZONE` | 时区 | `Asia/Shanghai` |
| `MIND_SCHEDULER_MAX_WORKERS` | 最大工作线程数 | `3` |
| `MIND_SCHEDULER_MIN_INTERVAL` | 最小抓取间隔（分钟） | `15` |
| **抓取器配置** | | |
| `MIND_FETCHER_TIMEOUT` | 请求超时（秒） | `30` |
| `MIND_FETCHER_MAX_RETRIES` | 最大重试次数 | `3` |
| `MIND_FETCHER_MAX_CONTENT_LENGTH` | 最大内容长度 | `100000` |
| **去重配置** | | |
| `MIND_DEDUPE_STRATEGY` | 去重策略 (strict/medium/relaxed) | `medium` |
| **内容提取配置** | | |
| `MIND_CONTENT_FETCHER_ENABLED` | 启用内容提取 | `true` |
| `MIND_CONTENT_FETCHER_MAX_LENGTH` | 最大提取长度 | `500000` |
| **关键词提取配置** | | |
| `MIND_KEYWORD_EXTRACTOR_ENABLED` | 启用关键词提取 | `true` |
| `MIND_KEYWORD_MAX` | 最大关键词数量 | `10` |
| **摘要配置** | | |
| `MIND_SUMMARIZER_ENABLED` | 启用摘要生成 | `true` |
| `MIND_SUMMARIZER_METHOD` | 摘要方法 (extractive/ai) | `extractive` |
| `MIND_SUMMARIZER_MAX_LENGTH` | 最大摘要长度 | `10000` |
| **日志配置** | | |
| `MIND_LOG_LEVEL` | 日志级别 | `INFO` |
| `MIND_LOG_PATH` | 日志文件路径 | `logs/mind-weaver.log` |

### 配置文件

创建 `config/config.yaml`（可选）：

```yaml
# 数据库配置
database:
  type: sqlite  # sqlite, postgresql, mysql
  path: "data/spider_aggregation.db"
  # PostgreSQL/MySQL 示例:
  # host: "localhost"
  # port: 5432
  # name: "spider_aggregation"
  # user: "your_user"
  # password: "your_password"

# Web 配置
web:
  host: "127.0.0.1"
  port: 8000
  debug: false
  secret_key: "your-secret-key-here"

# 抓取器配置
fetcher:
  timeout_seconds: 30
  max_retries: 3
  max_content_length: 100000
  user_agent: "MindWeaver/0.4.0"

# 调度器配置
scheduler:
  min_interval_minutes: 15
  timezone: "Asia/Shanghai"
  max_workers: 3

# 去重配置
deduplicator:
  strategy: "medium"  # strict, medium, relaxed

# 内容提取配置
content_fetcher:
  enabled: true
  timeout_seconds: 30
  max_content_length: 500000

# 关键词提取配置
keyword_extractor:
  enabled: true
  max_keywords: 10

# 摘要配置
summarizer:
  enabled: true
  method: "extractive"  # extractive or ai
  max_length: 10000

# 过滤配置
filter:
  enabled: true

# 日志配置
logging:
  level: "INFO"
  path: "logs/mind-weaver.log"
  rotation: "10 MB"
```

### 多数据库配置示例

**PostgreSQL:**
```bash
export MIND_DB_TYPE=postgresql
export MIND_DB_HOST=localhost
export MIND_DB_PORT=5432
export MIND_DB_NAME=mindweaver
export MIND_DB_USER=postgres
export MIND_DB_PASSWORD=your_password
```

**MySQL:**
```bash
export MIND_DB_TYPE=mysql
export MIND_DB_HOST=localhost
export MIND_DB_PORT=3306
export MIND_DB_NAME=mindweaver
export MIND_DB_USER=root
export MIND_DB_PASSWORD=your_password
```

---

## Web 界面功能

### Dashboard
- 统计概览（总条目数、订阅源数、分类数、过滤规则数）
- 语言分布图表
- 最近活动
- 订阅源健康状态
- 调度器控制（启动/停止/手动抓取）

### Feeds 管理
- 添加/编辑/删除订阅源
- 启用/禁用订阅源
- 手动触发抓取
- 查看抓取状态和错误信息
- 分类管理
- 个性化设置（条目限制、仅获取最新）

### Categories 管理
- 创建/编辑/删除分类
- 自定义颜色和图标
- 启用/禁用分类
- 查看分类下的订阅源统计
- 分类级别的批量管理

### Entries 浏览
- 分页浏览所有条目
- 按订阅源/分类过滤
- 搜索功能
- 批量操作（删除、提取内容、关键词、摘要）

### Filter Rules
- 创建过滤规则（关键词/正则/标签/语言）
- 设置匹配类型（include/exclude）
- 优先级控制
- 启用/禁用规则

### Settings
- 数据清理（删除旧条目）
- 数据导出（JSON 格式）
- 系统信息

---

## API 端点

### 订阅源管理 (`/api/feeds`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/feeds` | 获取订阅源列表（支持分页、搜索、分类过滤） |
| POST | `/api/feeds` | 创建订阅源 |
| GET | `/api/feeds/<id>` | 获取订阅源详情 |
| PUT | `/api/feeds/<id>` | 更新订阅源 |
| DELETE | `/api/feeds/<id>` | 删除订阅源 |
| POST | `/api/feeds/<id>/toggle` | 启用/禁用 |
| POST | `/api/feeds/<id>/fetch` | 手动抓取 |

### 分类管理 (`/api/categories`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/categories` | 获取分类列表 |
| POST | `/api/categories` | 创建分类 |
| GET | `/api/categories/<id>` | 获取分类详情 |
| PUT | `/api/categories/<id>` | 更新分类 |
| DELETE | `/api/categories/<id>` | 删除分类 |
| POST | `/api/categories/<id>/toggle` | 启用/禁用 |
| GET | `/api/categories/<id>/feeds` | 获取分类下的订阅源 |

### 条目管理 (`/api/entries`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/entries` | 获取条目列表（支持分页、搜索、过滤） |
| GET | `/api/entries/<id>` | 获取条目详情 |
| DELETE | `/api/entries/<id>` | 删除条目 |
| POST | `/api/entries/batch/delete` | 批量删除 |
| POST | `/api/entries/batch/fetch-content` | 批量提取内容 |
| POST | `/api/entries/batch/extract-keywords` | 批量提取关键词 |
| POST | `/api/entries/batch/summarize` | 批量生成摘要 |

### 过滤规则管理 (`/api/filter-rules`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/filter-rules` | 获取规则列表 |
| POST | `/api/filter-rules` | 创建规则 |
| GET | `/api/filter-rules/<id>` | 获取规则详情 |
| PUT | `/api/filter-rules/<id>` | 更新规则 |
| DELETE | `/api/filter-rules/<id>` | 删除规则 |
| POST | `/api/filter-rules/<id>/toggle` | 启用/禁用 |

### 调度器管理 (`/api/scheduler`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/scheduler/status` | 获取调度器状态 |
| POST | `/api/scheduler/start` | 启动调度器 |
| POST | `/api/scheduler/stop` | 停止调度器 |
| POST | `/api/scheduler/fetch-all` | 立即抓取所有 |

### 系统接口 (`/api/system`)
| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/stats` | 获取统计信息 |
| GET | `/api/dashboard/activity` | 获取最近活动 |
| GET | `/api/dashboard/feed-health` | 获取订阅源健康状态 |
| POST | `/api/system/cleanup` | 清理旧条目 |
| GET | `/api/system/export/entries` | 导出条目 (JSON) |
| GET | `/api/system/export/feeds` | 导出订阅源 (JSON) |

### Blueprint 架构

Web 层采用 Blueprint 模块化架构：

```
web/
├── app.py              # Flask 应用工厂
├── blueprints/
│   ├── base.py         # CRUDBlueprint 基类
│   ├── feeds.py        # FeedBlueprint
│   ├── categories.py   # CategoryBlueprint
│   ├── entries.py      # EntryBlueprint
│   ├── filter_rules.py # FilterRuleBlueprint
│   ├── scheduler.py    # SchedulerBlueprint
│   └── system.py       # SystemBlueprint
├── templates/          # Jinja2 模板
└── static/             # CSS/JS 静态资源
```

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI Layer                         │
│            Flask + Jinja2 + Blueprint                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │Dashboard │ │  Feeds   │ │Categories│ │ Entries  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Service Layer (Facade)                │
│                  services.py (统一入口)                   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                    Core Logic Layer                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Fetcher  │ │  Parser  │ │Dedup'or  │ │Scheduler │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ContentFetcher│ │ FilterEngine │ │     NLP      │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                      (KeywordExtractor, Summarizer)      │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  Repository Layer                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │FeedRepository│ │EntryRepository││CategoryRepo  │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│  ┌──────────────┐ ┌──────────────┐                     │
│  │FilterRuleRepo│ │BaseRepository│                     │
│  └──────────────┘ └──────────────┘                     │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                Storage Layer (Multi-DB)                 │
│         SQLite │ PostgreSQL │ MySQL + SQLAlchemy        │
└─────────────────────────────────────────────────────────┘
```

### 设计模式

| 模式 | 应用场景 |
|------|----------|
| **Facade 模式** | Service Layer 提供统一入口 |
| **Repository 模式** | 数据访问层抽象 |
| **Factory 模式** | 组件创建 (factories.py) |
| **Strategy 模式** | 去重策略 (strict/medium/relaxed) |
| **Blueprint 模式** | Flask 路由模块化 |
| **Mixin 模式** | 代码复用 (Repository/Model mixins) |

### 核心模块

| 模块 | 功能 |
|------|------|
| `Fetcher` | RSS/Atom 抓取，支持 ETag/Last-Modified |
| `Parser` | 内容解析和标准化，支持多语言检测 |
| `Deduplicator` | 多策略去重（link/title/content hash） |
| `Scheduler` | 定时任务调度，支持并发 |
| `ContentFetcher` | 完整文章内容提取（Trafilatura） |
| `FilterEngine` | 规则过滤（关键词/正则/标签/语言） |
| `KeywordExtractor` | 关键词提取（NLTK/jieba） |
| `Summarizer` | 摘要生成（抽取式/AI） |
| `Service Facade` | 统一服务入口，模块边界管理 |

### 数据层

| 模块 | 功能 |
|------|------|
| `BaseRepository` | 通用 CRUD 基类 |
| `FeedRepository` | 订阅源 CRUD，分类关联 |
| `EntryRepository` | 条目 CRUD，搜索、过滤、分页 |
| `CategoryRepository` | 分类 CRUD，订阅源管理 |
| `FilterRuleRepository` | 过滤规则 CRUD，优先级查询 |

### 数据库支持

项目支持多种数据库，可通过环境变量 `MIND_DB_TYPE` 切换：

| 数据库 | 驱动 | 连接字符串示例 |
|--------|------|----------------|
| SQLite | 内置 | `sqlite:///data/spider_aggregation.db` |
| PostgreSQL | psycopg2-binary | `postgresql://user:pass@localhost/dbname` |
| MySQL | pymysql | `mysql+pymysql://user:pass@localhost/dbname` |

---

## 开发

### 项目结构

```
spider-aggregation/
├── config/                      # 配置文件目录
│   ├── config.yaml             # 主配置文件
│   ├── feeds.example.yaml      # 订阅源配置示例
│   └── filters.example.yaml    # 过滤规则配置示例
├── data/                       # 运行时数据目录
│   └── spider_aggregation.db   # SQLite 数据库文件
├── docs/                       # 文档目录
├── logs/                       # 日志目录
├── migrations/                 # Alembic 数据库迁移
├── plans/                      # 项目计划文档
├── scripts/                    # 实用脚本
├── src/spider_aggregation/     # 源代码
│   ├── __main__.py            # 程序入口
│   ├── config.py              # 配置管理
│   ├── core/                  # 核心业务逻辑
│   │   ├── fetcher.py         # RSS/Atom 抓取
│   │   ├── parser.py          # 内容解析
│   │   ├── deduplicator.py    # 去重逻辑
│   │   ├── scheduler.py       # 任务调度
│   │   ├── content_fetcher.py # 内容提取
│   │   ├── filter_engine.py   # 过滤引擎
│   │   ├── keyword_extractor.py # 关键词提取
│   │   ├── summarizer.py      # 摘要生成
│   │   ├── services.py        # Service Facade
│   │   └── factories.py       # 工厂函数
│   ├── models/                # 数据模型
│   │   ├── base.py            # ORM 基类
│   │   ├── feed.py            # Feed 模型
│   │   ├── entry.py           # Entry 模型
│   │   ├── category.py        # Category 模型
│   │   └── filter_rule.py     # FilterRule 模型
│   ├── storage/               # 数据访问层
│   │   ├── database.py        # 数据库管理
│   │   ├── dialects/          # 数据库方言
│   │   │   ├── base.py        # 方言基类
│   │   │   ├── sqlite.py      # SQLite 实现
│   │   │   ├── postgresql.py  # PostgreSQL 实现
│   │   │   └── mysql.py       # MySQL 实现
│   │   └── repositories/      # Repository 实现
│   │       ├── base.py        # Repository 基类
│   │       ├── feed_repo.py   # Feed Repository
│   │       ├── entry_repo.py  # Entry Repository
│   │       ├── category_repo.py # Category Repository
│   │       └── filter_rule_repo.py # FilterRule Repository
│   └── web/                   # Web 层
│       ├── app.py             # Flask 应用
│       ├── blueprints/        # Blueprint 模块
│       │   ├── base.py        # Blueprint 基类
│       │   ├── feeds.py       # Feed Blueprint
│       │   ├── categories.py  # Category Blueprint
│       │   ├── entries.py     # Entry Blueprint
│       │   ├── filter_rules.py # FilterRule Blueprint
│       │   ├── scheduler.py   # Scheduler Blueprint
│       │   └── system.py      # System Blueprint
│       ├── templates/         # Jinja2 模板
│       └── static/            # 静态资源
├── tests/                     # 测试
│   ├── unit/                  # 单元测试
│   └── integration/           # 集成测试
├── pyproject.toml             # 项目配置
├── alembic.ini                # Alembic 配置
└── README.md                  # 项目文档
```

### 运行测试

```bash
# 所有测试
uv run pytest

# 单元测试
uv run pytest tests/unit/

# 集成测试
uv run pytest tests/integration/

# 覆盖率报告
uv run pytest --cov=src/spider_aggregation --cov-report=html

# 慢速测试标记
uv run pytest -m slow

# 排除慢速测试
uv run pytest -m "not slow"
```

### 代码质量

```bash
# Black 格式化
uv run black src/ tests/

# Ruff 检查
uv run ruff check src/ tests/

# Ruff 自动修复
uv run ruff check --fix src/ tests/

# 类型检查（需要安装 mypy）
uv run mypy src/spider_aggregation/
```

### 实用脚本

```bash
# 数据库初始化
python scripts/init_db.py

# 添加示例订阅源
python scripts/seed_feeds.py

# 添加示例过滤规则
python scripts/seed_filter_rules.py

# 测试真实订阅源
python scripts/test_real_feed.py

# 数据库迁移脚本
python scripts/migrate_phase2.py       # Phase 2 功能迁移
python scripts/migrate_categories.py   # 分类功能迁移
python scripts/migrate_feed_settings.py  # 订阅源设置迁移

# 部署脚本
./scripts/deploy.sh
```

### Alembic 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

---

## 性能

- **抓取速度**：~1-2 秒/订阅源（取决于网络）
- **去重速度**：O(1) 哈希查找
- **存储效率**：每条约 1-5 KB（取决于内容长度）
- **并发支持**：默认 3 个工作线程（可配置）
- **数据库**：SQLite 支持千级订阅源/百万级条目

---

## 常见问题

### 如何更改数据库位置？

**SQLite:**
```bash
export MIND_DB_PATH=/path/to/your/database.db
```

**PostgreSQL/MySQL:**
```bash
export MIND_DB_TYPE=postgresql
export MIND_DB_HOST=localhost
export MIND_DB_NAME=mindweaver
# ... 其他配置
```

或在 `config.yaml` 中配置。

### 如何备份和恢复数据？

**SQLite:**
```bash
# 备份
cp data/spider_aggregation.db data/backup_$(date +%Y%m%d).db

# 恢复
cp data/backup_20260201.db data/spider_aggregation.db
```

**PostgreSQL/MySQL:**
```bash
# PostgreSQL 备份
pg_dump -U user -d mindweaver > backup.sql

# PostgreSQL 恢复
psql -U user -d mindweaver < backup.sql

# MySQL 备份
mysqldump -u user -p mindweaver > backup.sql

# MySQL 恢复
mysql -u user -p mindweaver < backup.sql
```

或在 Settings 页面使用 "Data Export" 功能（JSON 格式导出）。

### 如何使用 Alembic 进行数据库迁移？

```bash
# 创建新迁移
alembic revision --autogenerate -m "add new feature"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history
```

### 如何启用 AI 摘要？

1. 安装 AI 依赖：`uv sync --all-extras`
2. 在 `config.yaml` 中配置 AI API 密钥：
   ```yaml
   summarizer:
     enabled: true
     method: "ai"  # 或 "extractive"
     ai_provider: "anthropic"  # 或 "openai"
     anthropic_api_key: "your-api-key"
   ```
3. 重启应用

### 如何按主题组织订阅源？

使用 Categories 功能：
1. 在 "Categories" 页面创建分类（如 "技术"、"新闻"、"博客"）
2. 为每个分类设置颜色和图标
3. 在添加/编辑订阅源时指定分类
4. 禁用整个分类可以暂停该分类下所有订阅源

### 从 SQLite 切换到 PostgreSQL/MySQL？

1. 备份现有数据（JSON 导出或数据库备份）
2. 设置新的数据库环境变量
3. 运行 Alembic 迁移创建表结构：`alembic upgrade head`
4. 使用导入脚本或手动迁移数据

### 如何调试调度器问题？

```bash
# 查看日志
tail -f logs/mind-weaver.log

# 检查调度器状态
curl http://localhost:8000/api/scheduler/status

# 手动触发抓取测试
python scripts/test_real_feed.py
```

---

## 贡献

欢迎贡献！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 技术栈

### 核心依赖

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **语言** | Python | 3.14+ | 开发语言 |
| **Web 框架** | Flask | 3.0+ | Web 服务 |
| **模板引擎** | Jinja2 | 3.1+ | HTML 模板 |
| **ORM** | SQLAlchemy | 2.0+ | 数据库抽象 |
| **数据库迁移** | Alembic | 1.18+ | 数据库版本管理 |
| **任务调度** | APScheduler | 3.10+ | 定时任务 |
| **Feed 解析** | feedparser | 6.0+ | RSS/Atom 解析 |
| **HTTP 客户端** | httpx | 0.27+ | 异步 HTTP 请求 |
| **内容提取** | Trafilatura | 1.6+ | 网页内容提取 |
| **NLP** | NLTK | 3.8+ | 英文关键词提取 |
| **中文分词** | jieba | 0.42+ | 中文关键词提取 |
| **数据验证** | Pydantic | 2.6+ | 配置/数据验证 |
| **日志** | Loguru | 0.7+ | 日志管理 |

### 可选依赖

| 技术 | 用途 |
|------|------|
| psycopg2-binary | PostgreSQL 支持 |
| pymysql | MySQL 支持 |
| anthropic | AI 摘要（Claude API） |
| openai | AI 摘要（OpenAI API） |

### 开发依赖

| 技术 | 用途 |
|------|------|
| pytest | 测试框架 |
| pytest-cov | 覆盖率测试 |
| pytest-asyncio | 异步测试支持 |
| black | 代码格式化 |
| ruff | 代码检查 |
| mypy | 类型检查 |

## 致谢

- [feedparser](https://github.com/kurtmckee/feedparser) - RSS/Atom 解析
- [APScheduler](https://github.com/agronholm/apscheduler) - 任务调度
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Alembic](https://alembic.sqlalchemy.org/) - 数据库迁移
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Trafilatura](https://github.com/adbar/trafilatura) - 内容提取
- [jieba](https://github.com/fxsjy/jieba) - 中文分词
- [NLTK](https://www.nltk.org/) - 自然语言处理
- [httpx](https://www.python-httpx.org/) - 异步 HTTP 客户端
- [Pydantic](https://docs.pydantic.dev/) - 数据验证
- [Loguru](https://github.com/Delgan/loguru) - 日志管理

---

## 路线图

### ✅ Phase 1 - MVP（已完成）
- RSS/Atom 抓取
- 内容解析和标准化
- 多层次去重
- 定时任务调度
- Web 管理界面

### ✅ Phase 2 - 内容增强（已完成）
- 完整文章内容提取
- 关键词提取
- 过滤规则引擎
- 批量操作
- AI 摘要（可选）

### ✅ Phase 3 - 组织管理（已完成）
- 订阅源分类管理
- 分类 CRUD 操作
- 颜色和图标自定义
- 分类级别统计
- 个性化订阅源设置（条目限制、仅获取最新）

### ✅ Phase 4 - 架构优化（已完成）
- Facade 模式实现（Service Layer）
- 多数据库支持（SQLite/PostgreSQL/MySQL）
- Repository 模式强化（BaseRepository）
- Blueprint 模块化架构
- 数据库迁移工具（Alembic）
- 代码结构优化与重构

### 📋 Phase 5 - 智能推荐（计划中）
- 用户行为追踪
- 兴趣模型构建
- 智能推荐引擎
- 个性化信息流

### 🚀 Phase 6 - 高级功能（长期）
- 全文搜索（Elasticsearch/Whoosh）
- 多源采集（社交媒体、API、网页监控）
- 事件聚类与热点发现
- 趋势分析与预测
- 知识图谱
- 自动化报告生成
- API 认证与多用户支持
- 移动端适配

---

<div align="center">

Made with ❤️ for personal knowledge management

</div>
