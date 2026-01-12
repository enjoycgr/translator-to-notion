# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Translation Agent System - 基于 Claude Agent SDK 的 AI 翻译平台，支持英译中流式翻译、后台任务管理和 Notion 同步。

**技术栈**：Python 3.13+ / Flask 3.1 / Claude Agent SDK / React 18 / TypeScript / Vite / Tailwind CSS

## 常用命令

### 后端开发

```bash
# 安装依赖
uv sync --frozen

# 启动开发服务器
uv run python main.py

# 验证配置
uv run python main.py --check

# 指定端口和主机
uv run python main.py --host 0.0.0.0 --port 5000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev      # 开发服务器 (localhost:5173)
npm run build    # 生产构建
npm run lint     # ESLint 检查
```

### Docker 部署

```bash
docker-compose up -d --build    # 构建并启动
docker-compose logs -f          # 查看日志
docker-compose down             # 停止服务
```

## 架构设计

### 分层结构

```
agent/                  # AI Agent 核心
├── prompts/           # 翻译提示词模板 (tech/business/academic)
├── tools/             # MCP 工具 (web_fetcher, notion_tool)
└── sdk_translator_agent.py

backend/               # Flask 后端
├── routes/            # API 路由 (translate, notion, tasks, health)
├── services/          # 业务逻辑 (translation, task_manager, cache, chunking)
├── middleware/        # 认证中间件
└── schemas/           # 数据验证

frontend/src/          # React SPA
├── pages/             # 页面组件 (Home, TaskList, TaskDetail)
├── components/        # UI 组件
└── services/          # API 服务层

config/                # 配置管理 (YAML + 环境变量)
```

### 核心设计模式

1. **流式翻译**：SSE (Server-Sent Events) 实时输出
2. **Agent 模式**：Claude SDK + MCP 工具自主执行
3. **后台任务**：单线程队列 + JSON 持久化 + 断点续传
4. **语义分段**：长文本自动分段翻译

### 关键服务

| 服务 | 文件 | 职责 |
|------|------|------|
| TranslationService | `backend/services/translation_service.py` | 翻译业务逻辑 |
| BackgroundTaskManager | `backend/services/task_manager.py` | 后台任务队列 |
| SDKTranslatorAgent | `agent/sdk_translator_agent.py` | Claude Agent 封装 |
| CacheService | `backend/services/cache_service.py` | 缓存与进度追踪 |

## API 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/health` | 否 | 健康检查 |
| POST | `/api/translate/stream` | 是 | 流式翻译 (SSE) |
| POST | `/api/translate/agent` | 是 | Agent 模式翻译 |
| POST | `/api/notion/sync` | 是 | 同步到 Notion |
| GET/DELETE | `/api/tasks/{task_id}` | 是 | 任务管理 |

**认证方式**：Header `X-Access-Key`

## 配置说明

### 必需环境变量

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 可选环境变量

```bash
NOTION_API_KEY=secret_xxxxx      # Notion 集成
NOTION_PARENT_PAGE_ID=xxxxx
ACCESS_KEYS=ak_key1,ak_key2      # API 认证密钥
AGENT_MODEL=claude-opus-4-5-20251101
AGENT_TIMEOUT=300
```

### 配置文件

`config/config.yaml` 支持：translation (领域/分段)、cache (TTL)、notion、auth、agent、server

## 开发注意事项

1. **翻译方向固定**：仅支持英译中
2. **领域选择**：tech (技术) / business (商务) / academic (学术)
3. **长文处理**：自动语义分段，支持断点续传
4. **Notion 输出**：双语段落交替格式
5. **Agent 超时**：配置于 `config/config.yaml` 的 `agent.timeout`

## 依赖版本

- Python: 3.13.9+
- claude-agent-sdk: >=0.1.18
- Flask: >=3.1.2
- React: ^18.2.0
- Node.js: 使用 Vite 5.x
