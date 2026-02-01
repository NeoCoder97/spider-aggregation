# Spider Aggregation

<div align="center">

**个人知识/研究动态监测工具**

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
- 🎨 **Rich 终端界面** - 彩色输出和表格展示
- 🛠️ **完整 CLI** - 命令行工具管理订阅源和内容

---

## 安装

### 系统要求

- Python 3.14 或更高版本
- uv（推荐的包管理器）或 pip

### 使用 uv（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/NeoCoder97/spider-aggregation.git
cd spider-aggregation

# 2. 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安装依赖
uv sync

# 4. 验证安装
uv run spider-aggregation --version
```

### 使用 pip

```bash
# 1. 克隆仓库
git clone https://github.com/NeoCoder97/spider-aggregation.git
cd spider-aggregation

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -e .

# 4. 验证安装
spider-aggregation --version
```

---

## 快速开始

### 1. 初始化数据库

```bash
uv run spider-aggregation init
```

输出：
```
Initializing Spider Aggregation database...
✅ Database initialized at: data/spider_aggregation.db
```

### 2. 添加订阅源

```bash
# 自动检测元数据
uv run spider-aggregation add-feed https://blog.cloudflare.com/zh-cn/rss
```

输出：
```
Adding feed: https://blog.cloudflare.com/zh-cn/rss

📡 Fetching feed metadata...
   ✅ Feed title: The Cloudflare Blog

✅ Feed added with ID: 1
   Name: The Cloudflare Blog
   URL: https://blog.cloudflare.com/zh-cn/rss
   Enabled: True
   Interval: 60 minutes
```

### 3. 手动抓取

```bash
uv run spider-aggregation fetch --all
```

输出：
```
Fetching 1 feed(s)...

✅ The Cloudflare Blog: 20 new, 0 skipped (20 total)

✅ Fetch complete!
   Total entries: 20
   New entries: 20
   Skipped (duplicates): 0
```

### 4. 查看条目

```bash
uv run spider-aggregation list-entries --limit 10
```

### 5. 启动自动调度

```bash
uv run spider-aggregation start
```

按 `Ctrl+C` 停止调度器。

---

## 命令参考

### 全局选项

| 选项 | 描述 |
|------|------|
| `--db-path TEXT` | 数据库文件路径 |
| `--verbose`, `-v` | 详细输出 |
| `--help`, `-h` | 帮助信息 |
| `--version` | 版本信息 |

### 命令列表

#### `init` - 初始化数据库

```bash
spider-aggregation init
```

#### `add-feed` - 添加订阅源

```bash
spider-aggregation add-feed URL [OPTIONS]
```

**选项**：
- `--name TEXT`, `-n TEXT` - 订阅源名称（默认：自动检测）
- `--description TEXT`, `-d TEXT` - 订阅源描述
- `--interval INTEGER`, `-i INTEGER` - 抓取间隔（分钟）
- `--enabled/--disabled` - 启用/禁用（默认：启用）

**示例**：
```bash
# 自动检测
spider-aggregation add-feed https://example.com/feed.xml

# 指定名称和间隔
spider-aggregation add-feed https://example.com/feed.xml --name "My Feed" --interval 120
```

#### `list-feeds` - 列出订阅源

```bash
spider-aggregation list-feeds [OPTIONS]
```

**选项**：
- `--verbose`, `-v` - 显示详细信息

**示例**：
```bash
# 基本列表
spider-aggregation list-feeds

# 详细信息
spider-aggregation list-feeds --verbose
```

#### `fetch` - 手动抓取

```bash
spider-aggregation fetch [FEED_ID] [OPTIONS]
```

**选项**：
- `--all`, `-a` - 抓取所有启用的订阅源
- `--force`, `-f` - 强制抓取（忽略间隔）

**示例**：
```bash
# 抓取所有
spider-aggregation fetch --all

# 抓取指定订阅源
spider-aggregation fetch 1
```

#### `start` - 启动调度器

```bash
spider-aggregation start [OPTIONS]
```

**选项**：
- `--workers INTEGER`, `-w INTEGER` - 工作线程数（默认：3）

#### `list-entries` - 列出条目

```bash
spider-aggregation list-entries [OPTIONS]
```

**选项**：
- `--feed-id INTEGER`, `-f INTEGER` - 按订阅源过滤
- `--limit INTEGER`, `-l INTEGER` - 显示数量（默认：20）
- `--offset INTEGER` - 分页偏移
- `--language TEXT` - 按语言过滤（en, zh, ja 等）
- `--search TEXT`, `-s TEXT` - 搜索内容

**示例**：
```bash
# 最近 10 条
spider-aggregation list-entries --limit 10

# 中文条目
spider-aggregation list-entries --language zh

# 搜索
spider-aggregation list-entries --search Python
```

#### `enable-feed` - 启用/禁用订阅源

```bash
spider-aggregation enable-feed FEED_ID [--enable|--disable]
```

#### `delete-feed` - 删除订阅源

```bash
spider-aggregation delete-feed FEED_ID
```

#### `cleanup` - 清理旧条目

```bash
spider-aggregation cleanup [--days INTEGER]
```

**默认清理 30 天前的条目**。

---

## 配置

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `SPIDER_DB_PATH` | 数据库文件路径 | `data/spider_aggregation.db` |

### 配置文件

创建 `config/config.yaml`（可选）：

```yaml
database:
  path: "data/spider_aggregation.db"

fetcher:
  timeout_seconds: 30
  max_retries: 3
  max_content_length: 10000
  user_agent: "Spider-Aggregation/0.1.0"

scheduler:
  min_interval_minutes: 15
  timezone: "UTC"

deduplicator:
  strategy: "medium"  # strict, medium, relaxed
  similarity_threshold: 0.85
```

---

## 架构

```
┌─────────────┐
│     CLI     │  Click + Rich
└──────┬──────┘
       │
┌──────▼──────┐
│  Scheduler  │  APScheduler (定时任务)
└──────┬──────┘
       │
┌──────▼───────────────────────────┐
│          Core Logic              │
│  ┌────────┐ ┌────────┐ ┌────────┐│
│  │Fetcher │ │ Parser │ │Dedup  ││
│  └────────┘ └────────┘ └────────┘│
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

详细架构文档：[docs/architecture.md](docs/architecture.md)

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

开发指南：[docs/development-guide.md](docs/development-guide.md)

---

## 文档

- [架构设计](docs/architecture.md) - 系统架构和模块设计
- [API 参考](docs/api-reference.md) - CLI 和核心 API 文档
- [开发指南](docs/development-guide.md) - 开发环境设置和最佳实践

---

## 性能

- **抓取速度**：~1-2 秒/订阅源（取决于网络）
- **去重速度**：O(1) 哈希查找
- **存储效率**：每条约 1-5 KB（取决于内容长度）
- **并发支持**：默认 3 个工作线程（可配置）

---

## 常见问题

### 如何添加多个订阅源？

```bash
spider-aggregation add-feed https://feed1.com/rss
spider-aggregation add-feed https://feed2.com/atom
spider-aggregation add-feed https://feed3.com/rss
```

### 如何查看抓取日志？

日志文件位于 `data/logs/`：

```bash
# 查看最新日志
tail -f data/logs/spider_$(date +%Y-%m-%d).log
```

### 如何更改数据库位置？

使用 `--db-path` 选项或设置 `SPIDER_DB_PATH` 环境变量：

```bash
spider-aggregation --db-path /custom/path/db.sqlite init
```

### 如何备份和恢复数据？

```bash
# 备份
cp data/spider_aggregation.db data/backup_$(date +%Y%m%d).db

# 恢复
cp data/backup_20260201.db data/spider_aggregation.db
```

---

## 贡献

欢迎贡献！请查看 [开发指南](docs/development-guide.md) 了解详情。

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
- [Click](https://click.palletsprojects.com/) - CLI 框架
- [Rich](https://rich.readthedocs.io/) - 终端美化

---

## 路线图

### ✅ MVP (已完成)
- RSS/Atom 抓取
- 内容解析和标准化
- 多层次去重
- 定时任务调度
- 完整 CLI

### 🔜 Phase 2 (计划中)
- AI 摘要生成
- 关键词提取
- Web UI

### 📋 Phase 3 (未来)
- 用户行为追踪
- 兴趣模型
- 智能推荐

### 🚀 Phase 4 (长期)
- 多源采集（网页、API、社交媒体）
- 事件聚类
- 趋势分析

---

<div align="center">

Made with ❤️ for personal knowledge management

</div>
