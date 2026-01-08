# Translation Agent System 部署文档

## 目录

- [系统概述](#系统概述)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [部署方式](#部署方式)
  - [Docker 部署（推荐）](#docker-部署推荐)
  - [手动部署](#手动部署)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [运维指南](#运维指南)
- [故障排查](#故障排查)

---

## 系统概述

Translation Agent System 是一个基于 Claude Agent SDK 的智能翻译系统，支持：

- **英译中翻译**：高质量的英文到中文翻译
- **URL 内容抓取**：自动获取网页内容进行翻译
- **Notion 集成**：翻译结果可直接同步到 Notion
- **多领域支持**：技术文档、商务文档、学术论文等专业领域
- **流式输出**：实时显示翻译进度
- **断点续传**：支持长文本翻译的进度恢复

### 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.13.9+ + Flask 3.1 + Claude Agent SDK |
| 前端 | React 18 + TypeScript + Vite 5 + Tailwind CSS 3 |
| AI 引擎 | Claude API (claude-opus-4-5-20251101) |
| 包管理 | UV (Python) + npm (Node.js) |
| 容器化 | Docker + Docker Compose |

---

## 系统要求

### 硬件要求

| 环境 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| 最低配置 | 1 核 | 512MB | 1GB |
| 推荐配置 | 2 核 | 2GB | 5GB |

### 软件要求

**Docker 部署：**
- Docker 20.10+
- Docker Compose 2.0+

**手动部署：**
- Python 3.13.9+
- UV 包管理器（推荐）或 pip
- Node.js 20+ (仅构建前端需要)

### 外部服务

| 服务 | 必需性 | 用途 |
|------|--------|------|
| Anthropic API | **必需** | Claude AI 翻译引擎 |
| Notion API | 可选 | 翻译结果同步到 Notion |

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd claude-agent
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要配置
```

**必填配置：**
```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**可选配置：**
```env
# 自定义 API 端点（代理或私有部署）
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Notion 集成
NOTION_API_KEY=secret_xxxxx
NOTION_PARENT_PAGE_ID=xxxxx

# API 访问密钥
ACCESS_KEYS=ak_your_secret_key

# Agent 配置
AGENT_MODEL=claude-opus-4-5-20251101
AGENT_TIMEOUT=300
```

### 3. 启动服务

```bash
# Docker 一键启动
docker-compose up -d --build

# 检查服务状态
docker-compose ps
```

### 4. 验证部署

```bash
# 健康检查
curl http://localhost:5000/api/health
```

---

## 部署方式

### Docker 部署（推荐）

#### 生产环境部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f translator

# 停止服务
docker-compose down
```

#### 自定义镜像标签

```bash
# 构建带标签的镜像
docker build -t translation-agent:v1.0.0 .

# 推送到私有仓库
docker tag translation-agent:v1.0.0 your-registry.com/translation-agent:v1.0.0
docker push your-registry.com/translation-agent:v1.0.0
```

#### 调试模式

```bash
# 启用调试模式
DEBUG=true docker-compose up
```

### 手动部署

#### 1. 安装 UV 包管理器

**macOS / Linux：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows：**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. 安装 Python 依赖

```bash
# 使用 UV 安装（推荐）
uv sync --frozen

# 或使用 pip（备选）
pip install -e .
```

#### 3. 构建前端（可选）

如果需要修改前端代码：

```bash
cd frontend
npm install
npm run build
cd ..
```

#### 4. 启动服务

```bash
# 验证配置
uv run python main.py --check

# 启动服务
uv run python main.py --host 0.0.0.0 --port 5000

# 或直接运行（如果已激活虚拟环境）
python main.py --host 0.0.0.0 --port 5000
```

#### 5. 使用 systemd 管理服务（Linux）

创建服务文件 `/etc/systemd/system/translation-agent.service`：

```ini
[Unit]
Description=Translation Agent System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/translation-agent
EnvironmentFile=/opt/translation-agent/.env
ExecStart=/opt/translation-agent/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable translation-agent
sudo systemctl start translation-agent
```

---

## 配置说明

### 环境变量

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `ANTHROPIC_API_KEY` | 是 | - | Claude API 密钥 |
| `ANTHROPIC_BASE_URL` | 否 | `https://api.anthropic.com` | API 端点（代理或私有部署） |
| `NOTION_API_KEY` | 否 | - | Notion 集成令牌 |
| `NOTION_PARENT_PAGE_ID` | 否 | - | Notion 父页面 ID |
| `ACCESS_KEYS` | 否 | `ak_default_key` | API 访问密钥（逗号分隔） |
| `SERVER_HOST` | 否 | `0.0.0.0` | 服务监听地址 |
| `SERVER_PORT` | 否 | `5000` | 服务监听端口 |
| `DEBUG` | 否 | `false` | 调试模式 |
| `AGENT_MODEL` | 否 | `claude-opus-4-5-20251101` | Claude 模型 |
| `AGENT_TIMEOUT` | 否 | `300` | 代理超时时间（秒） |

### 配置文件

核心配置位于 `config/config.yaml`：

```yaml
# 翻译配置
translation:
  source_language: "en"
  target_language: "zh-CN"

  # 长文本分块策略
  chunking:
    strategy: "semantic"
    max_chunk_tokens: 8000
    overlap_sentences: 2

# 缓存配置（断点续传）
cache:
  type: "memory"
  ttl_minutes: 30
  max_entries: 100

# Agent 配置
agent:
  model: "claude-opus-4-5-20251101"
  max_turns: 10
  timeout: 300
```

### 领域配置

系统支持以下预设领域：

| 领域 | 标识 | 适用场景 |
|------|------|----------|
| 技术 | `tech` | 技术文档、编程教程 |
| 商务 | `business` | 商务报告、金融文档 |
| 学术 | `academic` | 学术论文、研究报告 |

---

## API 接口

### 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/translate` | 同步翻译 |
| POST | `/api/translate/stream` | 流式翻译（SSE） |
| GET | `/api/translate/resume/<id>` | 恢复/查询进度 |
| POST | `/api/notion/sync` | 同步到 Notion |

### 认证方式

所有 API 请求（除健康检查外）需要在 Header 中携带访问密钥：

```http
X-Access-Key: ak_your_secret_key
```

### 接口示例

#### 翻译请求

```bash
curl -X POST http://localhost:5000/api/translate \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: ak_your_secret_key" \
  -d '{
    "text": "Hello, world!",
    "domain": "tech"
  }'
```

#### URL 翻译

```bash
curl -X POST http://localhost:5000/api/translate \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: ak_your_secret_key" \
  -d '{
    "url": "https://example.com/article",
    "domain": "tech"
  }'
```

#### 流式翻译

```bash
curl -X POST http://localhost:5000/api/translate/stream \
  -H "Content-Type: application/json" \
  -H "X-Access-Key: ak_your_secret_key" \
  -H "Accept: text/event-stream" \
  -d '{
    "text": "Your long text here...",
    "domain": "tech"
  }'
```

---

## 运维指南

### 日志管理

#### Docker 环境

```bash
# 查看实时日志
docker-compose logs -f translator

# 查看最近 100 行日志
docker-compose logs --tail=100 translator
```

#### 日志级别

通过 `DEBUG` 环境变量控制：
- `DEBUG=false`：仅输出 INFO 级别以上
- `DEBUG=true`：输出 DEBUG 级别以上

### 资源限制

Docker Compose 默认配置：

| 资源 | 限制 | 预留 |
|------|------|------|
| CPU | 2 核 | 0.5 核 |
| 内存 | 2GB | 512MB |

修改 `docker-compose.yml` 中的 `deploy.resources` 调整。

### 健康检查

容器内置健康检查：
- **间隔**：30 秒
- **超时**：10 秒
- **重试**：3 次
- **启动宽限期**：5 秒

```bash
# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' translation-agent
```

### 备份策略

重要数据：
- `.env` - 环境变量配置
- `config/config.yaml` - 应用配置

```bash
# 备份配置
tar -czvf config-backup-$(date +%Y%m%d).tar.gz .env config/
```

---

## 故障排查

### 常见问题

#### 1. 容器启动失败

```bash
# 检查日志
docker-compose logs translator

# 常见原因：
# - ANTHROPIC_API_KEY 未设置或无效
# - 端口 5000 被占用
# - 配置文件格式错误
```

#### 2. API 返回 401 Unauthorized

```bash
# 检查 ACCESS_KEYS 配置
# 确保请求 Header 中包含正确的 X-Access-Key
```

#### 3. 翻译超时

```bash
# 调整 AGENT_TIMEOUT 环境变量
# 或在 config.yaml 中修改 agent.timeout
# 对于长文本，建议使用流式翻译接口
```

#### 4. Notion 同步失败

```bash
# 检查 NOTION_API_KEY 是否正确
# 确认 NOTION_PARENT_PAGE_ID 存在且有权限
# Notion 集成需要在页面上授权
```

#### 5. UV 安装问题

```bash
# 重新安装 UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 验证安装
uv --version

# 清理并重新安装依赖
rm -rf .venv
uv sync --frozen
```

### 性能优化

1. **增加缓存 TTL**：减少重复翻译请求
2. **调整分块大小**：根据内容类型优化 `max_chunk_tokens`
3. **使用更快的模型**：根据需求选择合适的 Claude 模型
4. **启用日志轮转**：防止日志文件过大

### 获取帮助

```bash
# 验证配置
uv run python main.py --check

# 查看命令行帮助
uv run python main.py --help
```

---

## 版本信息

- **版本**：1.0.0
- **更新日期**：2026-01-08
- **Python 版本**：3.13.9+
- **维护者**：Translation Agent Team
