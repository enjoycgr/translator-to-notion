# 翻译代理系统实现计划

## 项目概述
基于 Claude Agent SDK 创建一个翻译代理系统，支持文章翻译和 URL 内容抓取翻译，翻译结果同步到 Notion。

## 技术决策总结

通过深度访谈确定的关键技术决策：

| 维度 | 决策 |
|------|------|
| 翻译方向 | 固定英译中 |
| 专业领域 | 预设模板：技术/编程、商务/金融、学术研究 |
| 长文处理 | 自动语义分段翻译 |
| 网页抓取 | 仅静态页面（requests + BeautifulSoup） |
| Notion存储 | 普通页面（非Database） |
| 双语展示 | 段落交替格式 |
| 断点续传 | 支持，内存缓存 |
| Notion同步 | 先输出译文，用户手动决定同步 |
| 重复内容 | 总是创建新页面 |
| Access Key | 仅配置文件管理 |
| 速率限制 | 不限制 |
| 部署方式 | Docker化 |
| 历史记录 | 不保存 |
| UI框架 | Tailwind CSS |
| API重试 | 条件性重试（网络错误/速率限制） |
| Notion元信息 | 原文链接 + 翻译领域 |

## 技术栈
- **Agent**: Claude Agent SDK (Python)
- **后端**: Flask
- **前端**: React (Vite + TypeScript + Tailwind CSS)
- **API鉴权**: Access Key (配置文件存储)
- **第三方**: Notion API (notion-client)
- **部署**: Docker

---

## 目录结构

```
D:\python\claude-agent\
├── config/                          # 配置文件目录
│   ├── __init__.py
│   ├── settings.py                  # 配置加载器
│   └── config.yaml                  # 主配置文件
├── backend/                         # Flask 后端
│   ├── __init__.py
│   ├── app.py                       # Flask 应用入口
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── translate.py             # 翻译接口（含流式、断点续传）
│   │   ├── notion.py                # Notion 同步接口
│   │   └── health.py                # 健康检查
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py                  # Access Key 验证
│   ├── services/
│   │   ├── __init__.py
│   │   ├── translation_service.py   # 翻译服务
│   │   ├── chunking_service.py      # 语义分段服务
│   │   └── cache_service.py         # 断点续传缓存
│   └── schemas/
│       ├── __init__.py
│       └── translate_schema.py      # 数据模型
├── agent/                           # Claude Agent 核心
│   ├── __init__.py
│   ├── translator_agent.py          # 翻译 Agent 主逻辑
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_fetcher.py           # 网页内容获取（仅静态）
│   │   └── notion_publisher.py      # Notion 发布（段落交替格式）
│   └── prompts/
│       ├── __init__.py
│       ├── translation_prompts.py   # 基础提示词模板
│       └── domain_prompts.py        # 领域专用提示词
├── frontend/                        # React 前端
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── components/
│   │   │   ├── TranslateForm.tsx
│   │   │   ├── DomainSelector.tsx   # 领域选择器
│   │   │   ├── ResultDisplay.tsx    # 双语段落交替展示
│   │   │   ├── NotionSyncButton.tsx # Notion 同步按钮
│   │   │   └── LoadingSpinner.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── main.py                          # 项目启动入口
```

---

## API 接口定义

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | 否 |
| POST | `/api/translate` | 同步翻译 | X-Access-Key |
| POST | `/api/translate/stream` | 流式翻译 (SSE) | X-Access-Key |
| GET | `/api/translate/resume/{task_id}` | 断点续传查询 | X-Access-Key |
| POST | `/api/notion/sync` | Notion 同步 | X-Access-Key |

### 翻译接口请求/响应格式

```json
// POST /api/translate
// Request
{
  "content": "文章内容 (与 url 二选一)",
  "url": "文章 URL (与 content 二选一)",
  "title": "文章标题 (可选)",
  "domain": "tech | business | academic"
}

// Response 200
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "original_content": "原文",
    "translated_content": "翻译结果（段落交替双语格式）",
    "notion_page_url": null,
    "cost_usd": 0.05
  }
}
```

### Notion 同步接口

```json
// POST /api/notion/sync
// Request
{
  "task_id": "uuid",
  "title": "文章标题"
}

// Response 200
{
  "success": true,
  "data": {
    "notion_page_url": "https://notion.so/xxx"
  }
}
```

### 断点续传接口

```json
// GET /api/translate/resume/{task_id}
// Response
{
  "success": true,
  "data": {
    "status": "in_progress | completed | failed",
    "progress": 75,
    "partial_result": "已翻译内容..."
  }
}
```

---

## 实现步骤

### 阶段一：项目初始化
- [ ] 创建目录结构和 `__init__.py` 文件
- [ ] 创建 `requirements.txt`（含 tiktoken 用于 token 计算）
- [ ] 创建 `.gitignore` 和 `.env.example`
- [ ] 实现 `config/settings.py` 配置加载器（含领域模板配置）
- [ ] 创建 `config/config.yaml` 配置模板

### 阶段二：Agent 核心开发
- [ ] 实现 `agent/tools/web_fetcher.py` - URL 内容获取（仅静态）
- [ ] 实现 `agent/tools/notion_publisher.py` - Notion 发布（段落交替格式）
- [ ] 实现 `agent/prompts/translation_prompts.py` - 基础提示词
- [ ] 实现 `agent/prompts/domain_prompts.py` - 领域专用提示词
- [ ] 实现 `agent/translator_agent.py` - 核心翻译 Agent

### 阶段三：Flask 后端开发
- [ ] 实现 `backend/middleware/auth.py` - Access Key 验证
- [ ] 实现 `backend/schemas/translate_schema.py` - 数据模型
- [ ] 实现 `backend/services/chunking_service.py` - 语义分段
- [ ] 实现 `backend/services/cache_service.py` - 断点续传缓存
- [ ] 实现 `backend/services/translation_service.py` - 服务层
- [ ] 实现 `backend/routes/health.py` - 健康检查
- [ ] 实现 `backend/routes/translate.py` - 翻译路由（含断点续传）
- [ ] 实现 `backend/routes/notion.py` - Notion 同步路由
- [ ] 实现 `backend/app.py` - Flask 应用入口

### 阶段四：React 前端开发
- [ ] 使用 Vite 初始化 React 项目 + Tailwind CSS
- [ ] 实现 `frontend/src/types/index.ts` - 类型定义
- [ ] 实现 `frontend/src/services/api.ts` - API 服务
- [ ] 实现 `frontend/src/components/DomainSelector.tsx` - 领域选择
- [ ] 实现 `frontend/src/components/TranslateForm.tsx`
- [ ] 实现 `frontend/src/components/ResultDisplay.tsx`（双语段落交替）
- [ ] 实现 `frontend/src/components/NotionSyncButton.tsx`
- [ ] 实现 `frontend/src/components/LoadingSpinner.tsx`
- [ ] 实现 `frontend/src/App.tsx` - 应用入口
- [ ] 实现样式文件（Tailwind）

### 阶段五：Docker 化
- [ ] 创建 `Dockerfile`
- [ ] 创建 `docker-compose.yml`
- [ ] 创建 `.dockerignore`

### 阶段六：集成测试
- [ ] 创建 `main.py` 启动入口
- [ ] 端到端测试

---

## 关键文件说明

### 1. `D:\python\claude-agent\agent\translator_agent.py`
翻译 Agent 核心，包含：
- Claude SDK 调用逻辑
- 自定义工具注册 (MCP Server)
- 翻译任务执行流程
- 长文分段处理协调

### 2. `D:\python\claude-agent\agent\tools\notion_publisher.py`
Notion 发布工具：
- Markdown → Notion Blocks 转换
- 段落交替双语格式构建
- 元信息（原文链接、翻译领域）添加
- 页面创建 API 调用

### 3. `D:\python\claude-agent\backend\services\chunking_service.py`
语义分段服务：
- 按段落/标题智能分割
- Token 计数（使用 tiktoken）
- 段落重叠保持上下文连贯

### 4. `D:\python\claude-agent\backend\services\cache_service.py`
断点续传缓存：
- 内存缓存 + TTL 过期
- 任务状态管理
- 翻译进度追踪

### 5. `D:\python\claude-agent\backend\routes\translate.py`
Flask 翻译路由：
- 同步翻译接口
- 流式翻译 (SSE) 接口
- 断点续传查询
- 请求验证

### 6. `D:\python\claude-agent\config\settings.py`
配置管理：
- YAML 配置加载
- 环境变量覆盖
- 类型安全的配置类
- 领域模板配置

### 7. `D:\python\claude-agent\frontend\src\services\api.ts`
前端 API 层：
- 翻译请求封装
- SSE 流式处理
- Access Key 管理
- 断点续传支持

---

## 依赖清单

### Python (requirements.txt)
```
claude-agent-sdk>=0.1.0
flask>=3.0.0
flask-cors>=4.0.0
aiohttp>=3.9.0
notion-client>=2.0.0
beautifulsoup4>=4.12.0
html2text>=2024.2.0
pyyaml>=6.0.0
python-dotenv>=1.0.0
tiktoken>=0.5.0
requests>=2.31.0
```

### Node.js (package.json)
```
react: ^18.2.0
react-dom: ^18.2.0
typescript: ^5.3.0
vite: ^5.0.0
tailwindcss: ^3.4.0
@tailwindcss/typography: ^0.5.0
```

---

## 配置文件模板 (config.yaml)
```yaml
translation:
  # 翻译方向（固定）
  source_language: "en"
  target_language: "zh-CN"

  # 预设领域模板
  domains:
    tech:
      name: "技术/编程"
      prompt_modifier: "请使用专业的技术术语，保留代码块和技术名词原文"
    business:
      name: "商务/金融"
      prompt_modifier: "请使用正式的商务用语，准确翻译金融术语"
    academic:
      name: "学术研究"
      prompt_modifier: "请保持学术严谨性，准确翻译专业术语和引用格式"

  # 长文分段
  chunking:
    strategy: "semantic"
    max_chunk_tokens: 8000
    overlap_sentences: 2

  # 重试策略
  retry:
    max_attempts: 3
    retry_on:
      - "network_error"
      - "rate_limit"
    backoff_multiplier: 2
    initial_delay_ms: 1000

cache:
  # 断点续传缓存
  type: "memory"
  ttl_minutes: 30
  max_entries: 100

notion:
  api_key: "secret_xxx"
  parent_page_id: "xxx"
  # 页面元信息
  metadata:
    include_source_url: true
    include_domain: true
    include_translate_time: false
    include_cost: false

auth:
  access_keys:
    - "ak_your_secret_key_1"

agent:
  model: "claude-sonnet-4-20250514"
  max_turns: 10
  timeout: 300

server:
  host: "0.0.0.0"
  port: 5000
  debug: false
```

---

## 核心代码示例

### TranslatorAgent 核心逻辑
```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server
)

class TranslatorAgent:
    def __init__(self, config: AppConfig):
        self.config = config
        self._setup_tools()

    def _setup_tools(self):
        @tool("publish_to_notion", "发布到 Notion", {"title": str, "content": str})
        async def notion_tool(args):
            # Notion 发布逻辑
            pass

        @tool("fetch_article", "获取文章内容", {"url": str})
        async def fetch_tool(args):
            # URL 内容获取逻辑
            pass

        self.mcp_server = create_sdk_mcp_server(
            name="translator-tools",
            version="1.0.0",
            tools=[notion_tool, fetch_tool]
        )

    async def translate(self, content=None, url=None, title=None, domain="tech"):
        options = ClaudeAgentOptions(
            mcp_servers={"tools": self.mcp_server},
            allowed_tools=["mcp__tools__fetch_article", "mcp__tools__publish_to_notion"]
        )

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                # 处理响应
                pass
```

### 语义分段服务
```python
# backend/services/chunking_service.py
import tiktoken
from typing import List

class ChunkingService:
    def __init__(self, max_tokens: int = 8000, overlap_sentences: int = 2):
        self.max_tokens = max_tokens
        self.overlap_sentences = overlap_sentences
        self.encoder = tiktoken.encoding_for_model("gpt-4")

    def split_by_semantic(self, text: str) -> List[str]:
        """按语义边界（段落/标题）分割文本"""
        paragraphs = self._split_paragraphs(text)
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(self.encoder.encode(para))
            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = current_chunk[-self.overlap_sentences:]
                current_tokens = sum(len(self.encoder.encode(p)) for p in current_chunk)
            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """按段落和标题分割"""
        import re
        return [p.strip() for p in re.split(r'\n\s*\n|(?=^#{1,6}\s)', text, flags=re.MULTILINE) if p.strip()]
```

### 断点续传缓存服务
```python
# backend/services/cache_service.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import threading
import uuid

@dataclass
class TranslationTask:
    task_id: str
    original_content: str
    chunks: List[str]
    translated_chunks: List[str] = field(default_factory=list)
    current_chunk: int = 0
    status: str = "in_progress"
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

class CacheService:
    def __init__(self, ttl_minutes: int = 30, max_entries: int = 100):
        self._cache: Dict[str, TranslationTask] = {}
        self._lock = threading.Lock()
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_entries = max_entries

    def create_task(self, original_content: str, chunks: List[str]) -> str:
        task_id = str(uuid.uuid4())
        task = TranslationTask(
            task_id=task_id,
            original_content=original_content,
            chunks=chunks
        )
        with self._lock:
            self._cleanup_expired()
            self._cache[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[TranslationTask]:
        with self._lock:
            return self._cache.get(task_id)

    def update_progress(self, task_id: str, translated_chunk: str) -> None:
        with self._lock:
            task = self._cache.get(task_id)
            if task:
                task.translated_chunks.append(translated_chunk)
                task.current_chunk += 1
                if task.current_chunk >= len(task.chunks):
                    task.status = "completed"

    def get_progress(self, task_id: str) -> dict:
        task = self.get_task(task_id)
        if not task:
            return {"status": "not_found"}
        return {
            "status": task.status,
            "progress": int((task.current_chunk / len(task.chunks)) * 100),
            "partial_result": "\n\n".join(task.translated_chunks)
        }

    def _cleanup_expired(self) -> None:
        now = datetime.now()
        expired = [k for k, v in self._cache.items() if now - v.created_at > self._ttl]
        for k in expired:
            del self._cache[k]
```

### 领域提示词
```python
# agent/prompts/domain_prompts.py

DOMAIN_PROMPTS = {
    "tech": {
        "name": "技术/编程",
        "system_modifier": """
你是一位专业的技术文档翻译专家。翻译时请：
1. 保留代码块、API 名称、函数名等技术术语原文
2. 对于常见技术名词（如 Container, Microservice）可以在首次出现时标注原文
3. 保持代码示例的格式和缩进
4. 使用准确的中文技术术语（如 "容器" 而非 "箱子"）
"""
    },
    "business": {
        "name": "商务/金融",
        "system_modifier": """
你是一位专业的商务文档翻译专家。翻译时请：
1. 使用正式、专业的商务用语
2. 准确翻译金融术语（如 ROI, EBITDA 等保留缩写并在首次标注中文）
3. 保持数据、图表说明的准确性
4. 注意商务礼仪用语的文化适配
"""
    },
    "academic": {
        "name": "学术研究",
        "system_modifier": """
你是一位专业的学术论文翻译专家。翻译时请：
1. 保持学术论文的严谨性和客观性
2. 准确翻译专业术语，首次出现时可标注原文
3. 保留引用格式（如 APA、MLA）
4. 保持摘要、方法论、结论等部分的学术写作风格
"""
    }
}

def get_domain_prompt(domain: str) -> str:
    return DOMAIN_PROMPTS.get(domain, {}).get("system_modifier", "")
```

### Notion 发布（段落交替格式）
```python
# agent/tools/notion_publisher.py
from notion_client import Client
from typing import List, Dict, Any

class NotionPublisher:
    def __init__(self, api_key: str, parent_page_id: str):
        self.client = Client(auth=api_key)
        self.parent_page_id = parent_page_id

    def publish(
        self,
        title: str,
        original_paragraphs: List[str],
        translated_paragraphs: List[str],
        source_url: str = None,
        domain: str = None
    ) -> str:
        """发布双语对照文章（段落交替格式）"""
        blocks = self._build_interleaved_blocks(original_paragraphs, translated_paragraphs)

        # 添加元信息
        metadata_blocks = []
        if source_url:
            metadata_blocks.append(self._create_text_block(f"原文链接: {source_url}"))
        if domain:
            metadata_blocks.append(self._create_text_block(f"翻译领域: {domain}"))
        if metadata_blocks:
            metadata_blocks.append(self._create_divider())

        page = self.client.pages.create(
            parent={"page_id": self.parent_page_id},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=metadata_blocks + blocks
        )
        return page["url"]

    def _build_interleaved_blocks(
        self,
        original: List[str],
        translated: List[str]
    ) -> List[Dict[str, Any]]:
        """构建段落交替的 Notion blocks"""
        blocks = []
        for orig, trans in zip(original, translated):
            # 原文段落（灰色引用块）
            blocks.append({
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": orig}}],
                    "color": "gray"
                }
            })
            # 译文段落
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": trans}}]
                }
            })
            # 空行分隔
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": []}})
        return blocks

    def _create_text_block(self, text: str) -> Dict[str, Any]:
        return {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}
        }

    def _create_divider(self) -> Dict[str, Any]:
        return {"type": "divider", "divider": {}}
```

### Access Key 验证中间件
```python
from functools import wraps
from flask import request, current_app, abort

def require_access_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_key = request.headers.get('X-Access-Key')
        if not access_key:
            abort(401, description="Missing Access Key")

        config = current_app.config['APP_CONFIG']
        if access_key not in config.auth.access_keys:
            abort(401, description="Invalid Access Key")

        return f(*args, **kwargs)
    return decorated
```

---

## Docker 配置

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 Node.js 用于前端构建
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 前端构建
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# 后端代码
COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  translator:
    build: .
    ports:
      - "5000:5000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config:/app/config:ro
    restart: unless-stopped
```

### .dockerignore
```
__pycache__
*.pyc
*.pyo
.git
.gitignore
.env
*.md
.vscode
.idea
node_modules
frontend/node_modules
```
