# 翻译代理系统执行计划

## 项目信息
- **项目名称**: 翻译代理系统 (Translation Agent)
- **技术栈**: Claude Agent SDK + Flask + React (Vite/TypeScript/Tailwind) + Notion API + Docker
- **预计工期**: 10-12 天
- **当前状态**: 0% (未开始)
- **最后更新**: 2026-01-06

## 状态说明
⬜ 未开始 | 🔄 进行中 | ✅ 已完成 | ⚠️ 阻塞中 | ❌ 已取消

## 项目里程碑
- [ ] Phase 1: 项目初始化 (⬜)
- [ ] Phase 2: Agent 核心开发 (⬜)
- [ ] Phase 3: Flask 后端开发 (⬜)
- [ ] Phase 4: React 前端开发 (⬜)
- [ ] Phase 5: Docker 化 (⬜)
- [ ] Phase 6: 集成测试 (⬜)

---

## Phase 1: 项目初始化 (预计 1 天)

**整体状态**: ⬜ 未开始
**依赖项**: 无
**阶段目标**: 搭建项目基础结构，配置开发环境，建立配置管理机制

### 1.1 创建目录结构

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 0.5 小时

**任务描述**:
创建项目的完整目录结构，包括所有模块目录和 `__init__.py` 文件。

**实现要点**:
- [ ] 创建 `config/` 目录及 `__init__.py`
- [ ] 创建 `backend/` 目录结构 (routes, middleware, services, schemas)
- [ ] 创建 `agent/` 目录结构 (tools, prompts)
- [ ] 创建 `frontend/` 基础目录
- [ ] 所有 Python 包添加 `__init__.py`

**验收标准**:
- ✅ 目录结构与 plan.md 中定义一致
- ✅ 所有 Python 目录包含 `__init__.py`
- ✅ 可以正常导入各模块

**技术参考**:
- 参考文件: plan.md 第 39-106 行目录结构

**依赖项**:
- 无

**潜在风险**:
- ⚠️ 无明显风险

---

### 1.2 创建 requirements.txt

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 0.5 小时

**任务描述**:
创建 Python 依赖清单文件，包含所有后端和 Agent 所需的库。

**实现要点**:
- [ ] 添加 claude-agent-sdk
- [ ] 添加 Flask 相关依赖 (flask, flask-cors)
- [ ] 添加 Notion 客户端 (notion-client)
- [ ] 添加网页抓取依赖 (beautifulsoup4, html2text, requests)
- [ ] 添加工具库 (pyyaml, python-dotenv, tiktoken, aiohttp)

**验收标准**:
- ✅ `pip install -r requirements.txt` 成功执行
- ✅ 所有依赖版本明确指定
- ✅ 无版本冲突

**技术参考**:
- 参考文件: plan.md 第 284-297 行依赖清单

**依赖项**:
- 任务 1.1 完成

**潜在风险**:
- ⚠️ claude-agent-sdk 版本可能需要确认最新稳定版

---

### 1.3 创建环境配置文件

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 0.5 小时

**任务描述**:
创建 `.gitignore` 和 `.env.example` 文件，确保敏感信息不会被提交。

**实现要点**:
- [ ] 创建 `.gitignore`，排除 `__pycache__`、`.env`、`node_modules` 等
- [ ] 创建 `.env.example`，包含必要的环境变量模板
- [ ] 添加 ANTHROPIC_API_KEY 占位符
- [ ] 添加 NOTION_API_KEY 占位符

**验收标准**:
- ✅ `.gitignore` 覆盖所有敏感和临时文件
- ✅ `.env.example` 包含所有必要的环境变量说明
- ✅ 可以通过复制 `.env.example` 快速创建 `.env`

**依赖项**:
- 任务 1.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 1.4 实现配置加载器 (settings.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 2 小时

**任务描述**:
实现类型安全的配置加载器，支持 YAML 配置文件和环境变量覆盖。

**实现要点**:
- [ ] 使用 dataclass 定义配置类型
- [ ] 实现 YAML 配置文件加载
- [ ] 支持环境变量覆盖机制
- [ ] 定义翻译配置 (domains, chunking, retry)
- [ ] 定义缓存配置 (type, ttl, max_entries)
- [ ] 定义 Notion 配置 (api_key, parent_page_id, metadata)
- [ ] 定义认证配置 (access_keys)
- [ ] 定义 Agent 配置 (model, max_turns, timeout)
- [ ] 定义服务器配置 (host, port, debug)

**验收标准**:
- ✅ 配置类有完整的类型注解
- ✅ 可以从 YAML 文件加载配置
- ✅ 环境变量可以覆盖配置文件的值
- ✅ 配置缺失时有明确的错误提示

**技术参考**:
- 参考文件: plan.md 第 266-272 行配置管理说明
- 参考代码: plan.md 第 311-374 行配置模板

**依赖项**:
- 任务 1.1, 1.2 完成

**潜在风险**:
- ⚠️ 配置结构可能需要根据实际开发调整

---

### 1.5 创建配置模板 (config.yaml)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
创建主配置文件模板，包含所有可配置项的默认值。

**实现要点**:
- [ ] 定义翻译方向配置 (source: en, target: zh-CN)
- [ ] 定义领域模板 (tech, business, academic)
- [ ] 定义分段策略 (semantic, max_chunk_tokens: 8000)
- [ ] 定义重试策略 (max_attempts, retry_on, backoff)
- [ ] 定义缓存配置 (memory, ttl: 30min)
- [ ] 定义 Notion 配置 (占位符)
- [ ] 定义认证配置 (示例 access_key)
- [ ] 定义 Agent 配置 (model, timeout)
- [ ] 定义服务器配置 (host, port)

**验收标准**:
- ✅ 配置文件格式正确，可被 settings.py 正确加载
- ✅ 所有配置项有合理的默认值
- ✅ 敏感信息使用占位符

**技术参考**:
- 参考代码: plan.md 第 311-374 行完整配置模板

**依赖项**:
- 任务 1.4 完成

**潜在风险**:
- ⚠️ 无明显风险

---

## Phase 2: Agent 核心开发 (预计 2-3 天)

**整体状态**: ⬜ 未开始
**依赖项**: Phase 1 完成
**阶段目标**: 实现翻译 Agent 核心逻辑，包括工具定义和提示词模板

### 2.1 实现网页内容获取工具 (web_fetcher.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 3 小时

**任务描述**:
实现静态网页内容获取工具，使用 requests + BeautifulSoup 抓取并提取文章内容。

**实现要点**:
- [ ] 使用 requests 获取网页 HTML
- [ ] 使用 BeautifulSoup 解析 HTML
- [ ] 实现文章主体内容提取逻辑
- [ ] 使用 html2text 转换为 Markdown
- [ ] 处理常见的文章结构 (article, main, content 等)
- [ ] 提取文章标题
- [ ] 处理请求异常和超时

**验收标准**:
- ✅ 可以成功抓取常见博客/新闻网站内容
- ✅ 正确提取文章标题和正文
- ✅ 输出格式为清晰的 Markdown
- ✅ 异常情况有明确的错误信息

**技术参考**:
- 参考文件: plan.md 第 71 行工具定义

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 不同网站结构差异大，可能需要多种提取策略
- ⚠️ 部分网站可能有反爬虫机制

---

### 2.2 实现基础翻译提示词 (translation_prompts.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 2 小时

**任务描述**:
定义翻译 Agent 的基础提示词模板，确保翻译质量和一致性。

**实现要点**:
- [ ] 定义系统提示词 (角色、能力、约束)
- [ ] 定义翻译任务提示词模板
- [ ] 定义段落交替输出格式说明
- [ ] 支持变量替换 (原文内容、领域等)
- [ ] 定义翻译质量要求

**验收标准**:
- ✅ 提示词清晰表达翻译要求
- ✅ 支持动态参数注入
- ✅ 翻译结果格式符合段落交替要求

**技术参考**:
- 参考文件: plan.md 第 75-76 行提示词模块

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 提示词可能需要多次迭代优化

---

### 2.3 实现领域专用提示词 (domain_prompts.py)

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 2 小时

**任务描述**:
实现三个预设领域的专用提示词：技术/编程、商务/金融、学术研究。

**实现要点**:
- [ ] 定义 DOMAIN_PROMPTS 字典结构
- [ ] 实现 tech 领域提示词 (保留代码块、技术术语)
- [ ] 实现 business 领域提示词 (正式商务用语、金融术语)
- [ ] 实现 academic 领域提示词 (学术严谨性、引用格式)
- [ ] 实现 get_domain_prompt(domain) 函数

**验收标准**:
- ✅ 三个领域提示词定义完整
- ✅ get_domain_prompt 函数正确返回对应提示词
- ✅ 未知领域返回空字符串

**技术参考**:
- 参考代码: plan.md 第 533-571 行领域提示词示例

**依赖项**:
- 任务 2.2 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 2.4 实现 Notion 发布工具 (notion_publisher.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 4 小时

**任务描述**:
实现 Notion 页面发布工具，支持段落交替双语格式和元信息添加。

**实现要点**:
- [ ] 初始化 Notion Client
- [ ] 实现 publish() 主方法
- [ ] 实现 _build_interleaved_blocks() 构建段落交替格式
- [ ] 原文使用灰色引用块 (quote)
- [ ] 译文使用普通段落
- [ ] 实现元信息添加 (原文链接、翻译领域)
- [ ] 实现辅助方法 (_create_text_block, _create_divider)
- [ ] 处理 Notion API 异常

**验收标准**:
- ✅ 可以成功创建 Notion 页面
- ✅ 页面格式为段落交替 (原文引用 + 译文段落)
- ✅ 元信息正确显示在页面顶部
- ✅ 返回正确的页面 URL

**技术参考**:
- 参考代码: plan.md 第 573-646 行 NotionPublisher 示例
- 参考文件: plan.md 第 240-246 行工具说明

**依赖项**:
- Phase 1 完成
- 需要有效的 Notion API Key 和 Parent Page ID 进行测试

**潜在风险**:
- ⚠️ Notion API 有请求限制，需要考虑大文章分批创建
- ⚠️ Block 内容长度有限制 (2000 字符)

---

### 2.5 实现翻译 Agent 主逻辑 (translator_agent.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 6 小时

**任务描述**:
实现翻译 Agent 核心类，整合工具注册、提示词模板和翻译执行流程。

**实现要点**:
- [ ] 定义 TranslatorAgent 类
- [ ] 实现 __init__ 初始化配置
- [ ] 实现 _setup_tools() 工具注册
- [ ] 注册 publish_to_notion 工具
- [ ] 注册 fetch_article 工具
- [ ] 创建 MCP Server
- [ ] 实现 translate() 主方法
- [ ] 支持 content 或 url 输入
- [ ] 支持 domain 领域选择
- [ ] 实现 Claude SDK 调用逻辑
- [ ] 实现流式响应处理
- [ ] 实现长文分段翻译协调

**验收标准**:
- ✅ Agent 可以正确初始化并注册工具
- ✅ 可以翻译直接输入的文本内容
- ✅ 可以通过 URL 获取并翻译内容
- ✅ 翻译结果符合段落交替格式
- ✅ 支持三个预设领域

**技术参考**:
- 参考代码: plan.md 第 380-422 行 TranslatorAgent 示例
- 参考文件: plan.md 第 233-239 行 Agent 说明

**依赖项**:
- 任务 2.1, 2.2, 2.3, 2.4 完成

**潜在风险**:
- ⚠️ Claude Agent SDK API 可能与示例代码有差异，需参考最新文档
- ⚠️ 长文分段需要与 chunking_service 协调

---

## Phase 3: Flask 后端开发 (预计 3 天)

**整体状态**: ⬜ 未开始
**依赖项**: Phase 2 完成
**阶段目标**: 实现完整的 Flask API 后端，包括认证、翻译、断点续传和 Notion 同步

### 3.1 实现 Access Key 验证中间件 (auth.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
实现基于 Access Key 的 API 认证中间件。

**实现要点**:
- [ ] 创建 require_access_key 装饰器
- [ ] 从请求头 X-Access-Key 获取密钥
- [ ] 验证密钥是否在配置的 access_keys 列表中
- [ ] 缺失密钥返回 401 + "Missing Access Key"
- [ ] 无效密钥返回 401 + "Invalid Access Key"

**验收标准**:
- ✅ 有效密钥可以通过验证
- ✅ 无效/缺失密钥返回 401 错误
- ✅ 错误信息清晰明确

**技术参考**:
- 参考代码: plan.md 第 649-666 行中间件示例

**依赖项**:
- Phase 1 配置加载器完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 3.2 实现数据模型 (translate_schema.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1.5 小时

**任务描述**:
定义翻译相关的请求/响应数据模型。

**实现要点**:
- [ ] 定义 TranslateRequest 模型 (content, url, title, domain)
- [ ] 定义 TranslateResponse 模型 (task_id, original_content, translated_content, cost_usd)
- [ ] 定义 NotionSyncRequest 模型 (task_id, title)
- [ ] 定义 NotionSyncResponse 模型 (notion_page_url)
- [ ] 定义 ResumeResponse 模型 (status, progress, partial_result)
- [ ] 实现请求验证逻辑 (content 和 url 二选一)

**验收标准**:
- ✅ 所有模型有完整的类型注解
- ✅ 请求验证逻辑正确
- ✅ 可以序列化为 JSON

**技术参考**:
- 参考文件: plan.md 第 120-177 行 API 格式定义

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 3.3 实现语义分段服务 (chunking_service.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 3 小时

**任务描述**:
实现基于语义边界的文本分段服务，支持长文翻译。

**实现要点**:
- [ ] 使用 tiktoken 进行 token 计数
- [ ] 实现 split_by_semantic() 按语义分割
- [ ] 按段落和标题边界分割
- [ ] 控制每个 chunk 不超过 max_tokens (默认 8000)
- [ ] 实现段落重叠保持上下文连贯 (overlap_sentences: 2)
- [ ] 实现 _split_paragraphs() 辅助方法

**验收标准**:
- ✅ 正确按段落/标题分割文本
- ✅ 每个 chunk 的 token 数不超过限制
- ✅ 相邻 chunk 有重叠保持连贯性
- ✅ 不会在段落中间断开

**技术参考**:
- 参考代码: plan.md 第 424-461 行 ChunkingService 示例
- 参考文件: plan.md 第 247-252 行服务说明

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 某些特殊格式文本可能导致分割不理想
- ⚠️ tiktoken 模型编码可能需要与 Claude 匹配

---

### 3.4 实现断点续传缓存服务 (cache_service.py)

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 3 小时

**任务描述**:
实现内存缓存服务，支持翻译任务的断点续传。

**实现要点**:
- [ ] 定义 TranslationTask 数据类
- [ ] 实现 CacheService 类
- [ ] 使用 threading.Lock 保证线程安全
- [ ] 实现 create_task() 创建任务
- [ ] 实现 get_task() 获取任务
- [ ] 实现 update_progress() 更新进度
- [ ] 实现 get_progress() 获取进度信息
- [ ] 实现 _cleanup_expired() 清理过期任务
- [ ] 支持 TTL 过期 (默认 30 分钟)
- [ ] 支持最大条目限制 (默认 100)

**验收标准**:
- ✅ 可以创建和获取翻译任务
- ✅ 进度更新正确
- ✅ 过期任务自动清理
- ✅ 线程安全

**技术参考**:
- 参考代码: plan.md 第 463-530 行 CacheService 示例
- 参考文件: plan.md 第 253-258 行服务说明

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 内存缓存在服务重启后丢失

---

### 3.5 实现翻译服务层 (translation_service.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 4 小时

**任务描述**:
实现翻译服务层，协调 Agent、分段和缓存服务。

**实现要点**:
- [ ] 初始化 TranslatorAgent, ChunkingService, CacheService
- [ ] 实现 translate() 同步翻译方法
- [ ] 实现 translate_stream() 流式翻译方法
- [ ] 实现长文自动分段处理
- [ ] 实现翻译进度追踪
- [ ] 实现条件性重试 (网络错误/速率限制)
- [ ] 计算翻译成本 (token 数 * 单价)
- [ ] 实现 resume_translate() 断点续传

**验收标准**:
- ✅ 短文直接翻译成功
- ✅ 长文自动分段翻译
- ✅ 流式翻译正确返回
- ✅ 断点续传功能正常
- ✅ 网络错误时自动重试

**技术参考**:
- 参考文件: plan.md 第 60-62 行服务层说明

**依赖项**:
- 任务 3.3, 3.4 完成
- Phase 2 Agent 开发完成

**潜在风险**:
- ⚠️ 流式翻译与分段翻译的协调可能复杂

---

### 3.6 实现健康检查路由 (health.py)

**状态**: ⬜ 未开始
**优先级**: 低
**预计时间**: 0.5 小时

**任务描述**:
实现简单的健康检查 API 端点。

**实现要点**:
- [ ] 创建 health_bp Blueprint
- [ ] 实现 GET /api/health 端点
- [ ] 返回服务状态和版本信息
- [ ] 可选：检查 Claude API 连接状态

**验收标准**:
- ✅ GET /api/health 返回 200 和状态信息
- ✅ 不需要认证

**技术参考**:
- 参考文件: plan.md 第 114 行 API 定义

**依赖项**:
- Phase 1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 3.7 实现翻译路由 (translate.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 4 小时

**任务描述**:
实现翻译相关的 API 端点，包括同步翻译、流式翻译和断点续传。

**实现要点**:
- [ ] 创建 translate_bp Blueprint
- [ ] 实现 POST /api/translate 同步翻译
- [ ] 实现 POST /api/translate/stream 流式翻译 (SSE)
- [ ] 实现 GET /api/translate/resume/{task_id} 断点续传查询
- [ ] 应用 require_access_key 装饰器
- [ ] 实现请求验证 (content/url 二选一)
- [ ] 实现 SSE 响应格式
- [ ] 错误处理和响应格式化

**验收标准**:
- ✅ 同步翻译接口正确返回翻译结果
- ✅ 流式翻译接口正确返回 SSE 流
- ✅ 断点续传查询返回正确的进度信息
- ✅ 所有端点需要有效的 Access Key

**技术参考**:
- 参考文件: plan.md 第 115-177 行 API 格式定义
- 参考文件: plan.md 第 259-265 行路由说明

**依赖项**:
- 任务 3.1, 3.2, 3.5 完成

**潜在风险**:
- ⚠️ SSE 流式响应需要正确设置响应头

---

### 3.8 实现 Notion 同步路由 (notion.py)

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 2 小时

**任务描述**:
实现 Notion 同步 API 端点。

**实现要点**:
- [ ] 创建 notion_bp Blueprint
- [ ] 实现 POST /api/notion/sync 端点
- [ ] 从缓存获取翻译任务结果
- [ ] 调用 NotionPublisher 发布页面
- [ ] 应用 require_access_key 装饰器
- [ ] 处理任务不存在的情况
- [ ] 返回 Notion 页面 URL

**验收标准**:
- ✅ 可以将翻译结果同步到 Notion
- ✅ 返回正确的 Notion 页面 URL
- ✅ 任务不存在时返回适当错误

**技术参考**:
- 参考文件: plan.md 第 118, 146-162 行 API 定义

**依赖项**:
- 任务 3.1, 3.4 完成
- 任务 2.4 Notion Publisher 完成

**潜在风险**:
- ⚠️ 需要确保缓存中的翻译结果格式正确

---

### 3.9 实现 Flask 应用入口 (app.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 2 小时

**任务描述**:
实现 Flask 应用主入口，注册所有蓝图和中间件。

**实现要点**:
- [ ] 创建 Flask 应用实例
- [ ] 加载配置到 app.config
- [ ] 配置 CORS
- [ ] 注册 health_bp 蓝图
- [ ] 注册 translate_bp 蓝图
- [ ] 注册 notion_bp 蓝图
- [ ] 配置全局错误处理
- [ ] 初始化服务实例

**验收标准**:
- ✅ Flask 应用可以正常启动
- ✅ 所有路由正确注册
- ✅ CORS 配置正确
- ✅ 全局错误返回统一格式

**技术参考**:
- 参考文件: plan.md 第 49 行应用入口

**依赖项**:
- 任务 3.6, 3.7, 3.8 完成

**潜在风险**:
- ⚠️ 无明显风险

---

## Phase 4: React 前端开发 (预计 2-3 天)

**整体状态**: ⬜ 未开始
**依赖项**: Phase 3 基本完成 (API 可用)
**阶段目标**: 实现完整的前端界面，包括翻译表单、结果展示和 Notion 同步

### 4.1 初始化 React 项目

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
使用 Vite 初始化 React 项目，配置 TypeScript 和 Tailwind CSS。

**实现要点**:
- [ ] 使用 `npm create vite@latest frontend -- --template react-ts` 创建项目
- [ ] 安装 Tailwind CSS 和相关依赖
- [ ] 配置 tailwind.config.js
- [ ] 安装 @tailwindcss/typography 插件
- [ ] 配置 vite.config.ts (代理后端 API)
- [ ] 清理默认文件

**验收标准**:
- ✅ `npm run dev` 成功启动开发服务器
- ✅ Tailwind CSS 样式生效
- ✅ TypeScript 编译无错误

**技术参考**:
- 参考文件: plan.md 第 299-308 行前端依赖

**依赖项**:
- 无

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.2 实现类型定义 (types/index.ts)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
定义前端使用的 TypeScript 类型。

**实现要点**:
- [ ] 定义 TranslateRequest 类型
- [ ] 定义 TranslateResponse 类型
- [ ] 定义 NotionSyncRequest 类型
- [ ] 定义 NotionSyncResponse 类型
- [ ] 定义 ResumeResponse 类型
- [ ] 定义 Domain 枚举 ('tech' | 'business' | 'academic')
- [ ] 定义 TranslationStatus 枚举

**验收标准**:
- ✅ 类型定义与后端 API 格式一致
- ✅ TypeScript 编译无错误

**技术参考**:
- 参考文件: plan.md 第 120-177 行 API 格式定义

**依赖项**:
- 任务 4.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.3 实现 API 服务层 (services/api.ts)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 3 小时

**任务描述**:
实现前端 API 调用层，封装所有后端接口调用。

**实现要点**:
- [ ] 配置 API 基础 URL
- [ ] 实现 Access Key 请求头注入
- [ ] 实现 translate() 同步翻译请求
- [ ] 实现 translateStream() SSE 流式请求
- [ ] 实现 resumeTranslate() 断点续传查询
- [ ] 实现 syncToNotion() Notion 同步请求
- [ ] 实现 healthCheck() 健康检查
- [ ] 统一错误处理

**验收标准**:
- ✅ 所有 API 调用正确发送请求
- ✅ Access Key 正确附加到请求头
- ✅ SSE 流正确解析和处理
- ✅ 错误响应正确处理

**技术参考**:
- 参考文件: plan.md 第 273-279 行 API 层说明

**依赖项**:
- 任务 4.2 完成

**潜在风险**:
- ⚠️ SSE 流处理需要特殊的 EventSource 或 fetch 处理

---

### 4.4 实现领域选择器组件 (DomainSelector.tsx)

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 1 小时

**任务描述**:
实现翻译领域选择组件。

**实现要点**:
- [ ] 定义组件 Props (value, onChange)
- [ ] 展示三个领域选项 (技术/编程、商务/金融、学术研究)
- [ ] 使用 Tailwind 样式美化
- [ ] 支持键盘导航

**验收标准**:
- ✅ 正确显示三个领域选项
- ✅ 选择状态正确切换
- ✅ 样式美观

**技术参考**:
- 参考文件: plan.md 第 85 行组件定义

**依赖项**:
- 任务 4.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.5 实现翻译表单组件 (TranslateForm.tsx)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 3 小时

**任务描述**:
实现主翻译表单组件，支持文本输入或 URL 输入。

**实现要点**:
- [ ] 实现输入模式切换 (文本/URL)
- [ ] 文本模式：多行文本输入框
- [ ] URL 模式：URL 输入框
- [ ] 集成 DomainSelector 组件
- [ ] 可选标题输入
- [ ] 表单验证 (content/url 必填)
- [ ] 提交按钮和加载状态
- [ ] 使用 Tailwind 样式

**验收标准**:
- ✅ 可以切换输入模式
- ✅ 表单验证正确
- ✅ 提交时调用正确的 API
- ✅ 加载状态正确显示

**技术参考**:
- 参考文件: plan.md 第 84 行组件定义

**依赖项**:
- 任务 4.3, 4.4 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.6 实现结果展示组件 (ResultDisplay.tsx)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 3 小时

**任务描述**:
实现翻译结果展示组件，支持双语段落交替格式。

**实现要点**:
- [ ] 解析翻译结果 (原文/译文段落)
- [ ] 段落交替展示 (原文灰色背景，译文正常)
- [ ] 支持 Markdown 渲染
- [ ] 使用 @tailwindcss/typography 样式
- [ ] 复制全文功能
- [ ] 进度显示 (流式翻译时)

**验收标准**:
- ✅ 原文和译文段落交替显示
- ✅ 视觉区分明显
- ✅ Markdown 正确渲染
- ✅ 复制功能正常

**技术参考**:
- 参考文件: plan.md 第 86 行组件定义

**依赖项**:
- 任务 4.1 完成

**潜在风险**:
- ⚠️ Markdown 渲染库选择 (可能需要 react-markdown)

---

### 4.7 实现 Notion 同步按钮组件 (NotionSyncButton.tsx)

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 1.5 小时

**任务描述**:
实现 Notion 同步按钮组件。

**实现要点**:
- [ ] 定义组件 Props (taskId, title, disabled)
- [ ] 实现点击同步逻辑
- [ ] 加载状态显示
- [ ] 成功后显示 Notion 页面链接
- [ ] 错误处理和提示

**验收标准**:
- ✅ 点击后正确调用同步 API
- ✅ 加载状态正确显示
- ✅ 成功后可以点击链接跳转到 Notion

**技术参考**:
- 参考文件: plan.md 第 87 行组件定义

**依赖项**:
- 任务 4.3 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.8 实现加载动画组件 (LoadingSpinner.tsx)

**状态**: ⬜ 未开始
**优先级**: 低
**预计时间**: 0.5 小时

**任务描述**:
实现通用加载动画组件。

**实现要点**:
- [ ] 使用 Tailwind 动画
- [ ] 支持不同尺寸
- [ ] 可选加载文本

**验收标准**:
- ✅ 动画流畅
- ✅ 尺寸可配置

**依赖项**:
- 任务 4.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 4.9 实现应用入口 (App.tsx)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 2 小时

**任务描述**:
实现应用主入口组件，整合所有子组件。

**实现要点**:
- [ ] 布局设计 (header, main, footer)
- [ ] Access Key 配置入口
- [ ] 集成 TranslateForm
- [ ] 集成 ResultDisplay
- [ ] 集成 NotionSyncButton
- [ ] 状态管理 (翻译结果、任务ID等)
- [ ] 响应式设计

**验收标准**:
- ✅ 完整的翻译工作流可用
- ✅ 界面美观，响应式
- ✅ 状态正确管理

**技术参考**:
- 参考文件: plan.md 第 83 行入口文件

**依赖项**:
- 任务 4.4-4.8 完成

**潜在风险**:
- ⚠️ 状态管理可能需要 useReducer 或其他方案

---

### 4.10 实现全局样式 (styles/globals.css)

**状态**: ⬜ 未开始
**优先级**: 低
**预计时间**: 1 小时

**任务描述**:
配置 Tailwind 基础样式和自定义样式。

**实现要点**:
- [ ] 引入 Tailwind 指令
- [ ] 自定义颜色变量
- [ ] 自定义字体
- [ ] 响应式断点调整
- [ ] 暗色模式支持 (可选)

**验收标准**:
- ✅ Tailwind 样式正确生效
- ✅ 整体风格统一

**依赖项**:
- 任务 4.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

## Phase 5: Docker 化 (预计 1 天)

**整体状态**: ⬜ 未开始
**依赖项**: Phase 3, Phase 4 完成
**阶段目标**: 完成项目的容器化部署配置

### 5.1 创建 Dockerfile

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 2 小时

**任务描述**:
创建多阶段 Dockerfile，同时构建前端和后端。

**实现要点**:
- [ ] 基于 python:3.11-slim 镜像
- [ ] 安装 Node.js 用于前端构建
- [ ] 安装 Python 依赖
- [ ] 构建前端静态文件
- [ ] 复制后端代码
- [ ] 配置启动命令
- [ ] 优化镜像大小

**验收标准**:
- ✅ `docker build` 成功构建
- ✅ 镜像大小合理 (<1GB)
- ✅ 容器可以正常启动

**技术参考**:
- 参考代码: plan.md 第 672-701 行 Dockerfile 示例

**依赖项**:
- Phase 3, Phase 4 完成

**潜在风险**:
- ⚠️ Node.js 安装可能导致镜像较大

---

### 5.2 创建 docker-compose.yml

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
创建 Docker Compose 配置文件。

**实现要点**:
- [ ] 定义 translator 服务
- [ ] 配置端口映射 (5000:5000)
- [ ] 配置环境变量 (ANTHROPIC_API_KEY)
- [ ] 配置配置文件挂载
- [ ] 设置重启策略

**验收标准**:
- ✅ `docker-compose up` 成功启动
- ✅ 服务可以正常访问

**技术参考**:
- 参考代码: plan.md 第 703-717 行 docker-compose 示例

**依赖项**:
- 任务 5.1 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 5.3 创建 .dockerignore

**状态**: ⬜ 未开始
**优先级**: 低
**预计时间**: 0.5 小时

**任务描述**:
创建 Docker 构建忽略文件。

**实现要点**:
- [ ] 排除 __pycache__
- [ ] 排除 .git
- [ ] 排除 .env
- [ ] 排除 node_modules
- [ ] 排除文档文件

**验收标准**:
- ✅ 构建上下文不包含不必要的文件
- ✅ 构建速度优化

**技术参考**:
- 参考代码: plan.md 第 719-732 行 .dockerignore 示例

**依赖项**:
- 无

**潜在风险**:
- ⚠️ 无明显风险

---

## Phase 6: 集成测试 (预计 1 天)

**整体状态**: ⬜ 未开始
**依赖项**: Phase 1-5 完成
**阶段目标**: 完成项目入口文件并进行端到端测试

### 6.1 创建项目启动入口 (main.py)

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 1 小时

**任务描述**:
创建项目主启动入口文件。

**实现要点**:
- [ ] 加载环境变量
- [ ] 加载配置文件
- [ ] 初始化 Flask 应用
- [ ] 配置静态文件服务 (前端构建产物)
- [ ] 启动服务器

**验收标准**:
- ✅ `python main.py` 成功启动服务
- ✅ API 和前端都可以访问

**技术参考**:
- 参考文件: plan.md 第 105 行入口文件

**依赖项**:
- Phase 3, Phase 4 完成

**潜在风险**:
- ⚠️ 无明显风险

---

### 6.2 端到端功能测试

**状态**: ⬜ 未开始
**优先级**: 高
**预计时间**: 4 小时

**任务描述**:
执行完整的端到端功能测试。

**实现要点**:
- [ ] 测试健康检查接口
- [ ] 测试 Access Key 认证
- [ ] 测试文本翻译功能
- [ ] 测试 URL 抓取翻译
- [ ] 测试三个领域翻译效果
- [ ] 测试长文分段翻译
- [ ] 测试流式翻译
- [ ] 测试断点续传
- [ ] 测试 Notion 同步
- [ ] 测试前端完整流程

**验收标准**:
- ✅ 所有核心功能正常工作
- ✅ 错误场景正确处理
- ✅ 性能在可接受范围内

**依赖项**:
- 任务 6.1 完成
- 需要有效的 API Key 进行测试

**潜在风险**:
- ⚠️ 可能发现需要修复的 Bug

---

### 6.3 Docker 部署测试

**状态**: ⬜ 未开始
**优先级**: 中
**预计时间**: 2 小时

**任务描述**:
测试 Docker 容器化部署。

**实现要点**:
- [ ] 构建 Docker 镜像
- [ ] 使用 docker-compose 启动
- [ ] 测试所有功能在容器中正常工作
- [ ] 测试配置文件挂载
- [ ] 测试环境变量注入

**验收标准**:
- ✅ Docker 容器成功启动
- ✅ 所有功能在容器中正常工作
- ✅ 配置可以通过挂载更新

**依赖项**:
- Phase 5 完成
- 任务 6.2 完成

**潜在风险**:
- ⚠️ 容器网络配置可能需要调整

---

## 技术工具清单

### 开发工具
- [ ] Python 3.11+ - 后端运行时
- [ ] Node.js 20+ - 前端构建
- [ ] Docker & Docker Compose - 容器化部署
- [ ] Git - 版本控制

### Python 依赖库
- [ ] claude-agent-sdk >= 0.1.0 - Claude Agent 核心
- [ ] flask >= 3.0.0 - Web 框架
- [ ] flask-cors >= 4.0.0 - CORS 支持
- [ ] aiohttp >= 3.9.0 - 异步 HTTP
- [ ] notion-client >= 2.0.0 - Notion API
- [ ] beautifulsoup4 >= 4.12.0 - HTML 解析
- [ ] html2text >= 2024.2.0 - HTML 转 Markdown
- [ ] pyyaml >= 6.0.0 - YAML 配置
- [ ] python-dotenv >= 1.0.0 - 环境变量
- [ ] tiktoken >= 0.5.0 - Token 计数
- [ ] requests >= 2.31.0 - HTTP 请求

### Node.js 依赖库
- [ ] react ^18.2.0 - UI 框架
- [ ] react-dom ^18.2.0 - React DOM
- [ ] typescript ^5.3.0 - 类型支持
- [ ] vite ^5.0.0 - 构建工具
- [ ] tailwindcss ^3.4.0 - CSS 框架
- [ ] @tailwindcss/typography ^0.5.0 - 排版插件

### 配置文件
- [ ] config/config.yaml - 主配置文件
- [ ] .env - 环境变量 (不提交)
- [ ] .env.example - 环境变量模板
- [ ] tailwind.config.js - Tailwind 配置
- [ ] vite.config.ts - Vite 配置
- [ ] tsconfig.json - TypeScript 配置

---

## 参考内容

### 官方文档
- [Claude Agent SDK 文档](https://docs.anthropic.com) - Agent 开发参考
- [Notion API 文档](https://developers.notion.com) - Notion 集成
- [Flask 文档](https://flask.palletsprojects.com) - 后端开发
- [React 文档](https://react.dev) - 前端开发
- [Tailwind CSS 文档](https://tailwindcss.com) - 样式开发

### 技术规范
- 参考 plan.md 第 110-177 行 API 接口定义
- 参考 plan.md 第 311-374 行配置文件格式

### 代码示例
- TranslatorAgent: plan.md 第 380-422 行
- ChunkingService: plan.md 第 424-461 行
- CacheService: plan.md 第 463-530 行
- DomainPrompts: plan.md 第 533-571 行
- NotionPublisher: plan.md 第 573-646 行
- AuthMiddleware: plan.md 第 649-666 行
- Dockerfile: plan.md 第 672-701 行

---

## 注意事项

### 开发规范
- ⚠️ 所有 Python 代码遵循 PEP 8 规范
- ⚠️ TypeScript 代码启用严格模式
- ⚠️ API 响应统一使用 JSON 格式
- ⚠️ 敏感信息不得硬编码

### 常见陷阱
- ❌ Notion API Block 内容超过 2000 字符会报错：需要分割长段落
- ❌ tiktoken 使用 gpt-4 编码可能与 Claude token 计数有差异：可接受的近似
- ❌ SSE 流需要正确设置 Content-Type: text/event-stream
- ❌ CORS 配置不当会导致前端请求失败

### 最佳实践
- ✅ 使用 dataclass 定义配置和数据模型
- ✅ 使用 Blueprint 组织 Flask 路由
- ✅ 使用 TypeScript 类型确保前后端数据一致
- ✅ 使用 Tailwind 实现响应式设计

### 性能优化
- 🚀 长文翻译使用分段处理避免超时
- 🚀 使用流式翻译提升用户体验
- 🚀 缓存服务避免重复翻译
- 🚀 Docker 多阶段构建减小镜像体积

### 测试要求
- 🧪 API 接口手动测试覆盖所有端点
- 🧪 翻译功能测试三个领域
- 🧪 Notion 同步测试页面格式
- 🧪 Docker 部署测试完整流程

---

## 进度追踪

### 总体进度
- 总任务数: 32
- 已完成: 0 (0%)
- 进行中: 0
- 未开始: 32
- 阻塞中: 0

### 本周计划
- [ ] Phase 1: 项目初始化 (1.1 - 1.5)
- [ ] Phase 2: Agent 核心开发开始 (2.1 - 2.2)

### 本周完成
- (暂无)

### 遇到的问题
(暂无)

### 下周计划
- [ ] 完成 Phase 2: Agent 核心开发
- [ ] 开始 Phase 3: Flask 后端开发
