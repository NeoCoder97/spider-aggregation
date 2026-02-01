# MindWeaver

<div align="center">

<img src="docs/logo.svg" alt="MindWeaver Logo" width="50"/>

**汇聚信息，提炼洞察**

*个人知识/研究动态监测工具*

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

自动化抓取、去重、存储和检索 RSS/Atom 订阅源内容的轻量化工具。

</div>

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
4. 配置名称、描述、抓取间隔等
5. 点击 "Create Feed"

### 3. 启动调度器

在 Dashboard 页面：
1. 点击 "Start Scheduler" 按钮启动自动抓取
2. 调度器会根据每个订阅源的间隔自动抓取
3. 点击 "Fetch All Now" 可以立即抓取所有订阅源

### 4. 管理条目

- **Entries** 页面：查看所有抓取的条目
- **Dashboard** 页面：查看统计信息和最近活动
- **Rules** 页面：配置过滤规则

---

## 配置

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `MIND_WEB_HOST` | Web 服务器地址 | `127.0.0.1` |
| `MIND_WEB_PORT` | Web 服务器端口 | `8000` |
| `MIND_WEB_DEBUG` | 调试模式 | `False` |
| `MIND_WEB_SECRET_KEY` | Flask secret key | 自动生成 |
| `MIND_DB_PATH` | 数据库文件路径 | `data/spider_aggregation.db` |

### 配置文件

创建 `config/config.yaml`（可选）：

```yaml
database:
  path: "data/spider_aggregation.db"

web:
  host: "127.0.0.1"
  port: 8000
  debug: false

fetcher:
  timeout_seconds: 30
  max_retries: 3
  max_content_length: 100000

scheduler:
  min_interval_minutes: 15
  timezone: "Asia/Shanghai"
  max_workers: 3

deduplicator:
  strategy: "medium"  # strict, medium, relaxed

content_fetcher:
  enabled: true
  timeout_seconds: 30
  max_content_length: 500000

keyword_extractor:
  enabled: true
  max_keywords: 10

summarizer:
  enabled: true
  method: "extractive"  # extractive or ai
```

---

## Web 界面功能

### Dashboard
- 统计概览（总条目数、订阅源数、过滤规则数）
- 语言分布图表
- 最近活动
- 订阅源健康状态
- 调度器控制（启动/停止/手动抓取）

### Feeds 管理
- 添加/编辑/删除订阅源
- 启用/禁用订阅源
- 手动触发抓取
- 查看抓取状态和错误信息

### Entries 浏览
- 分页浏览所有条目
- 按订阅源过滤
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

### 订阅源管理
- `GET /api/feeds` - 获取订阅源列表
- `POST /api/feeds` - 创建订阅源
- `PUT /api/feeds/<id>` - 更新订阅源
- `DELETE /api/feeds/<id>` - 删除订阅源
- `POST /api/feeds/<id>/toggle` - 启用/禁用
- `POST /api/feeds/<id>/fetch` - 手动抓取

### 条目管理
- `GET /api/entries/<id>` - 获取条目详情
- `DELETE /api/entries/<id>` - 删除条目
- `POST /api/entries/batch/delete` - 批量删除
- `POST /api/entries/batch/fetch-content` - 批量提取内容
- `POST /api/entries/batch/extract-keywords` - 批量提取关键词
- `POST /api/entries/batch/summarize` - 批量生成摘要

### 过滤规则管理
- `GET /api/filter-rules` - 获取规则列表
- `POST /api/filter-rules` - 创建规则
- `PUT /api/filter-rules/<id>` - 更新规则
- `DELETE /api/filter-rules/<id>` - 删除规则
- `POST /api/filter-rules/<id>/toggle` - 启用/禁用

### 调度器管理
- `GET /api/scheduler/status` - 获取调度器状态
- `POST /api/scheduler/start` - 启动调度器
- `POST /api/scheduler/stop` - 停止调度器
- `POST /api/scheduler/fetch-all` - 立即抓取所有

### 系统
- `GET /api/stats` - 获取统计信息
- `GET /api/dashboard/activity` - 获取最近活动
- `GET /api/dashboard/feed-health` - 获取订阅源健康状态
- `POST /api/system/cleanup` - 清理旧条目
- `GET /api/system/export/entries` - 导出条目
- `GET /api/system/export/feeds` - 导出订阅源

---

## 架构

```
┌─────────────┐
│  Web UI     │  Flask + Jinja2
└──────┬──────┘
       │
┌──────▼───────────────────────────┐
│          Core Logic              │
│  ┌────────┐ ┌────────┐ ┌────────┐│
│  │Fetcher │ │ Parser │ │Dedup  ││
│  └────────┘ └────────┘ └────────┘│
│  ┌──────────┐ ┌──────┐ ┌──────┐ │
│  │Scheduler │ │Filter│ │NLP   │ │
│  └──────────┘ └──────┘ └──────┘ │
└──────┬───────────────────────────┘
       │
┌──────▼──────┐
│   Storage   │  SQLite + SQLAlchemy
└─────────────┘
```

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

---

## 开发

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
```

### 代码格式化

```bash
# Black 格式化
uv run black src/ tests/

# Ruff 检查
uv run ruff check src/ tests/
```

---

## 性能

- **抓取速度**：~1-2 秒/订阅源（取决于网络）
- **去重速度**：O(1) 哈希查找
- **存储效率**：每条约 1-5 KB（取决于内容长度）
- **并发支持**：默认 3 个工作线程（可配置）

---

## 常见问题

### 如何更改数据库位置？

设置 `MIND_DB_PATH` 环境变量或在 `config.yaml` 中配置。

### 如何备份和恢复数据？

```bash
# 备份
cp data/spider_aggregation.db data/backup_$(date +%Y%m%d).db

# 恢复
cp data/backup_20260201.db data/spider_aggregation.db
```

或在 Settings 页面使用 "Data Export" 功能。

### 如何启用 AI 摘要？

1. 安装 AI 依赖：`uv sync --all-extras`
2. 在 `config.yaml` 中配置 AI API 密钥
3. 在 Settings 中启用 AI 摘要

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

## 致谢

- [feedparser](https://github.com/kurtmckee/feedparser) - RSS/Atom 解析
- [APScheduler](https://github.com/agronholm/apscheduler) - 任务调度
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Trafilatura](https://github.com/adbar/trafilatura) - 内容提取
- [jieba](https://github.com/fxsjy/jieba) - 中文分词
- [NLTK](https://www.nltk.org/) - 自然语言处理

---

## 路线图

### ✅ MVP (已完成)
- RSS/Atom 抓取
- 内容解析和标准化
- 多层次去重
- 定时任务调度
- Web 管理界面

### ✅ Phase 2 (已完成)
- 完整文章内容提取
- 关键词提取
- 过滤规则引擎
- 批量操作
- AI 摘要（可选）

### 📋 Phase 3 (计划中)
- 全文搜索
- 条目分组和收藏
- 导出功能增强（Markdown、PDF）
- 订阅源分类

### 🚀 Phase 4 (长期)
- 多源采集（网页、API、社交媒体）
- 事件聚类
- 趋势分析
- 智能推荐

---

<div align="center">

Made with ❤️ for personal knowledge management

</div>
