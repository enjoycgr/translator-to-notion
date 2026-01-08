# 翻译 Agent 系统重构计划：迁移到 Claude Agent SDK

## 概述

将现有使用 `anthropic` SDK 的翻译系统重构为使用 `claude-agent-sdk`，实现：
- `@tool` 装饰器定义工具
- `ClaudeSDKClient` 管理 Agent 会话
- MCP 服务器承载自定义工具
- 保持 SSE 流式输出

---

## 迁移范围

| 变更类型 | 文件 | 说明 |
|----------|------|------|
| **新增** | `agent/sdk_translator_agent.py` | 基于 SDK 的 Agent 核心 |
| **新增** | `agent/tools/web_fetcher_tool.py` | @tool 格式网页抓取 |
| **新增** | `agent/tools/notion_tool.py` | @tool 格式 Notion 发布 |
| **新增** | `agent/tools/tools_server.py` | MCP 服务器定义 |
| **新增** | `backend/services/sdk_translation_service.py` | SDK 服务层 |
| **重写** | `backend/routes/translate.py` | 使用新服务层 |
| **修改** | `config/settings.py` | 添加 SDK 配置 |
| **修改** | `requirements.txt` | 添加 claude-agent-sdk |
| **保留** | `backend/services/chunking_service.py` | 分块逻辑复用 |
| **保留** | `backend/services/cache_service.py` | 缓存逻辑复用 |

---

## 执行步骤

### 阶段 1：环境准备

```bash
pip install claude-agent-sdk
```

更新 `requirements.txt`：
```
claude-agent-sdk>=0.1.0
```

### 阶段 2：工具层重构

#### 2.1 创建 `D:\python\claude-agent\agent\tools\web_fetcher_tool.py`

```python
from claude_agent_sdk import tool

@tool("web_fetch", "Fetch article content from URL", {"url": str})
async def web_fetch_tool(args: dict) -> dict:
    """将现有 WebFetcher 逻辑包装为 @tool 格式"""
    # 复用现有 HTML 抓取和 Markdown 转换逻辑
    return {"content": [{"type": "text", "text": result}]}
```

#### 2.2 创建 `D:\python\claude-agent\agent\tools\notion_tool.py`

```python
from claude_agent_sdk import tool

@tool("notion_publish", "Publish translation to Notion", {"title": str, "content": str})
async def notion_publish_tool(args: dict) -> dict:
    """将现有 NotionPublisher 逻辑包装为 @tool 格式"""
    return {"content": [{"type": "text", "text": f"Published: {page_url}"}]}
```

#### 2.3 创建 `D:\python\claude-agent\agent\tools\tools_server.py`

```python
from claude_agent_sdk import create_sdk_mcp_server
from .web_fetcher_tool import web_fetch_tool
from .notion_tool import notion_publish_tool

def create_translation_tools_server():
    return create_sdk_mcp_server(
        name="translation-tools",
        version="1.0.0",
        tools=[web_fetch_tool, notion_publish_tool],
    )
```

### 阶段 3：Agent 层重构

#### 3.1 创建 `D:\python\claude-agent\agent\sdk_translator_agent.py`

核心设计：

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

class SDKTranslatorAgent:
    def __init__(self, config):
        self._tools_server = create_translation_tools_server()

    def _create_agent_options(self, system_prompt, include_tools=True):
        options = ClaudeAgentOptions(
            model=self.model,
            system_prompt=system_prompt,
            max_tokens=8192,
        )
        if include_tools:
            options.mcp_servers = {"translation-tools": self._tools_server}
            options.allowed_tools = get_all_tool_names()
        return options

    async def translate_stream(self, content=None, url=None, domain="tech"):
        """使用 ClaudeSDKClient 流式翻译"""
        options = self._create_agent_options(system_prompt, include_tools=bool(url))

        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            async for message in client.receive_response():
                yield self._convert_to_stream_event(message)
```

### 阶段 4：服务层重构

#### 4.1 创建 `D:\python\claude-agent\backend\services\sdk_translation_service.py`

关键功能：
- 协调 SDKTranslatorAgent 和 ChunkingService
- 将 SDK 异步流转换为 SSE 事件
- 集成缓存服务支持断点续传

```python
class SDKTranslationService:
    async def translate_stream_sse(self, content=None, url=None, domain="tech"):
        """生成 SSE 格式事件流"""
        if self.chunking.needs_chunking(content):
            async for event in self._stream_chunked_translation(...)
        else:
            async for event in self._stream_simple_translation(...)
```

### 阶段 5：API 层更新

#### 5.1 重写 `D:\python\claude-agent\backend\routes\translate.py`

关键变更：
- 使用 `SDKTranslationService` 替代现有服务
- 异步流到 SSE 的桥接

```python
@translate_bp.route('/api/translate/stream', methods=['POST'])
def translate_stream():
    service = get_sdk_translation_service()

    def generate():
        loop = asyncio.new_event_loop()
        async_gen = service.translate_stream_sse(...)
        # 将异步流转换为同步 SSE 输出
        while True:
            sse_string = loop.run_until_complete(async_gen.__anext__())
            yield sse_string

    return Response(generate(), mimetype='text/event-stream')
```

### 阶段 6：配置更新

#### 6.1 修改 `D:\python\claude-agent\config\settings.py`

```python
@dataclass
class AgentConfig:
    model: str = "claude-sonnet-4-20250514"
    use_sdk: bool = True  # 新增：SDK 模式开关
    sdk_options: dict = field(default_factory=lambda: {
        "max_tokens": 8192,
        "temperature": 0.7,
    })
```

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| MCP 服务器承载工具 | SDK 推荐方式，工具隔离易维护 |
| 保留 ChunkingService | 成熟的分块逻辑，无需重写 |
| Flask + asyncio.run_until_complete | 保持现有框架，兼容 Flask 2.x |
| 保留原代码作为后备 | 可通过配置切换，降低风险 |

---

## 文件依赖关系

```
requirements.txt (添加 claude-agent-sdk)
       ↓
agent/tools/web_fetcher_tool.py  ←  复用现有 HTML 解析逻辑
agent/tools/notion_tool.py       ←  复用现有 Notion API 调用
agent/tools/tools_server.py      ←  整合上述工具
       ↓
agent/sdk_translator_agent.py    ←  使用 tools_server
       ↓
backend/services/sdk_translation_service.py  ←  使用 agent + chunking + cache
       ↓
backend/routes/translate.py      ←  使用 service
```

---

## Claude Agent SDK 核心用法参考

### 基本查询模式

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async for message in query(
    prompt="Your task here",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Glob"],
        permission_mode="acceptEdits"
    )
):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if hasattr(block, "text"):
                print(block.text)
            elif hasattr(block, "name"):
                print(f"Tool: {block.name}")
    elif isinstance(message, ResultMessage):
        print(f"Done: {message.subtype}")
```

### 自定义工具定义

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("calculate", "Perform mathematical calculations", {"expression": str})
async def calculate(args: dict) -> dict:
    result = eval(args["expression"], {"__builtins__": {}})
    return {
        "content": [{"type": "text", "text": f"Result: {result}"}]
    }

@tool("get_time", "Get current time", {})
async def get_time(args: dict) -> dict:
    from datetime import datetime
    return {
        "content": [{"type": "text", "text": datetime.now().isoformat()}]
    }

# 创建 MCP 服务器
my_server = create_sdk_mcp_server(
    name="utilities",
    version="1.0.0",
    tools=[calculate, get_time]
)

# 配置 Agent
options = ClaudeAgentOptions(
    mcp_servers={"utils": my_server},
    allowed_tools=["mcp__utils__calculate", "mcp__utils__get_time"]
)
```

### 客户端会话模式

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient(options=options) as client:
    await client.query("What's 123 * 456?")

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
```

---

## 测试计划

1. **工具测试**：独立测试 `web_fetch_tool` 和 `notion_publish_tool`
2. **Agent 测试**：测试 `SDKTranslatorAgent.translate_stream`
3. **服务测试**：测试 `SDKTranslationService.translate_stream_sse`
4. **API 测试**：测试 `/api/translate/stream` SSE 输出
5. **端到端**：完整翻译流程 + Notion 发布

---

## 风险缓解

| 风险 | 措施 |
|------|------|
| SDK API 不稳定 | 封装调用，便于适配 |
| 性能回归 | 保留原实现可切换 |
| 流式中断 | 增加心跳机制 |

---

## 预估工作量

| 阶段 | 文件数 |
|------|--------|
| 工具层 | 3 个新文件 |
| Agent 层 | 1 个新文件 |
| 服务层 | 1 个新文件 |
| API 层 | 1 个重写 |
| 配置 | 2 个修改 |
