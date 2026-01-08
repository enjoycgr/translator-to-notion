# 后台翻译功能 执行计划

## 项目信息
- **项目名称**: 后台翻译功能实施
- **技术栈**: Python Flask + React TypeScript + Docker
- **预计工期**: 5-7 天
- **当前状态**: ✅ 100% 完成
- **最后更新**: 2026-01-08
- **源文档**: [background-translation-plan.md](./background-translation-plan.md)

## 状态说明
⬜ 未开始 | 🔄 进行中 | ✅ 已完成 | ⚠️ 阻塞中 | ❌ 已取消

## 项目里程碑
- [x] Phase 1: 后端基础设施 (✅ 已完成)
- [x] Phase 2: API 路由 (✅ 已完成)
- [x] Phase 3: 前端改造 (✅ 已完成)
- [x] Phase 4: Docker 配置 (✅ 已完成)

---

## Phase 1: 后端基础设施

**整体状态**: ✅ 已完成
**依赖项**: 无
**阶段目标**: 搭建后台任务处理的核心服务，包括任务管理器、持久化服务和缓存扩展

### 1.1 创建数据目录

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 0.5 小时

**任务描述**:
创建数据存储目录结构，用于持久化任务数据和翻译结果

**实现要点**:
- [x] 创建 `data/` 目录
- [x] 创建 `data/results/` 子目录
- [x] 添加 `.gitkeep` 文件

**验收标准**:
- ✅ `data/` 目录存在
- ✅ `data/results/` 目录存在
- ✅ `.gitkeep` 文件已添加，目录可被 git 跟踪

---

### 1.2 创建 BackgroundTaskManager

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 4 小时
**文件**: `backend/services/task_manager.py`

**任务描述**:
创建后台任务管理器，负责维护任务队列、单工作线程串行处理任务、与 CacheService 协作更新状态

**实现要点**:
- [x] 定义配置常量 `MAX_RETRY_COUNT = 3`、`CHUNK_TIMEOUT_SECONDS = 300`
- [x] 实现 `_task_queue: queue.Queue` 任务队列（线程安全）
- [x] 实现单工作线程 `_worker: threading.Thread`
- [x] 实现 `submit_task(task) -> str` 提交任务方法
- [x] 实现 `retry_task(task_id) -> bool` 手动重试方法
- [x] 实现 `cancel_task(task_id) -> bool` 取消排队任务方法
- [x] 实现 `shutdown()` 优雅关闭方法
- [x] 实现 `_worker_loop()` 工作线程主循环
- [x] 实现 `_execute_task(task)` 执行单个任务
- [x] 实现 `_execute_chunk_with_retry(chunk, task_id)` 带重试的 chunk 执行
- [x] 实现 `_get_retry_delay(retry_count)` 指数退避算法（1s, 2s, 4s）

**验收标准**:
- ✅ 任务提交后返回 task_id
- ✅ 工作线程串行执行任务
- ✅ chunk 失败时自动重试最多 3 次
- ✅ 重试使用指数退避策略
- ✅ 重试耗尽后标记任务为 `failed`
- ✅ 支持优雅关闭，等待当前任务完成

**技术参考**:
- 重试间隔: `2 ** retry_count` (0→1s, 1→2s, 2→4s)
- chunk 超时: 5 分钟
- 参考 plan.md 第 1.2 节

**依赖项**:
- 依赖 1.1 数据目录创建完成
- 依赖 CacheService 已存在

---

### 1.3 创建 TaskPersistenceService

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 3 小时
**文件**: `backend/services/task_persistence.py`

**任务描述**:
创建任务持久化服务，负责定时快照、状态变更持久化、服务启动恢复和过期任务清理

**实现要点**:
- [x] 实现每 30 秒快照到 `data/tasks.json`
- [x] 实现任务状态变更时立即持久化
- [x] 实现启动时从文件恢复未完成任务
- [x] 实现 `pending` 任务恢复：保持 pending，重新加入队列
- [x] 实现 `in_progress` 任务恢复：重置为 pending，重新排队
- [x] 实现过期任务清理（7 天以上的 completed/failed 任务）
- [x] 实现服务启动时清理过期任务
- [x] 实现翻译结果写入独立文件 `data/results/{task_id}.txt`

**数据结构**:
```json
{
  "version": 1,
  "last_updated": "ISO时间",
  "tasks": {
    "task-id": {
      "task_id": "...",
      "status": "pending|in_progress|completed|failed",
      "progress": 0-100,
      "original_content": "...",
      "total_chunks": 10,
      "completed_chunks": 5,
      "error_message": null,
      "created_at": "ISO时间",
      "updated_at": "ISO时间",
      "result_file": "results/{task_id}.txt"
    }
  }
}
```

**验收标准**:
- ✅ 每 30 秒自动保存快照
- ✅ 状态变更时立即持久化
- ✅ 服务重启后能恢复未完成任务
- ✅ in_progress 任务重启后重置为 pending
- ✅ 7 天以上的已完成/失败任务被清理
- ✅ 翻译结果存储在独立文件中

**依赖项**:
- 依赖 1.1 数据目录创建完成

---

### 1.4 扩展 CacheService

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 2 小时
**文件**: `backend/services/cache_service.py`

**任务描述**:
扩展现有的 CacheService，添加批量查询、恢复和文件操作方法

**实现要点**:
- [x] 添加 `get_all_tasks()` 方法用于持久化
- [x] 添加 `restore_tasks(tasks_dict)` 方法用于恢复
- [x] 添加 `get_task_metadata(task_id)` 方法（不含结果）
- [x] 添加 `get_tasks_list(offset, limit)` 方法用于分页列表
- [x] 添加 `set_task_status(task_id, status)` 方法
- [x] 添加 `delete_task(task_id)` 方法
- [x] 添加 `get_stats()` 方法用于统计

**验收标准**:
- ✅ `get_all_tasks()` 返回所有任务的字典
- ✅ `restore_tasks()` 能从字典恢复任务到内存
- ✅ `get_task_metadata()` 返回任务元数据（不含翻译结果）
- ✅ `get_tasks_list()` 支持分页和筛选
- ✅ `set_task_status()` 能更新任务状态
- ✅ `delete_task()` 能删除任务
- ✅ `get_stats()` 返回任务统计信息

**依赖项**:
- 依赖 1.1 数据目录创建完成

---

## Phase 2: API 路由

**整体状态**: ✅ 已完成
**依赖项**: Phase 1 核心服务完成
**阶段目标**: 创建任务管理的 RESTful API 接口

### 2.1 创建任务管理路由

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 3 小时
**文件**: `backend/routes/tasks.py`

**任务描述**:
创建 6 个 API 接口用于任务管理

**实现要点**:

**接口 1: POST `/api/translate/background`**
- [x] 接收翻译请求参数（content, source_lang, target_lang, domain）
- [x] 调用 BackgroundTaskManager.submit_task()
- [x] 返回 task_id、status、created_at

**接口 2: GET `/api/tasks`**
- [x] 支持分页参数 offset、limit
- [x] 返回任务列表、total、has_more
- [x] 支持无限滚动

**接口 3: GET `/api/tasks/{task_id}`**
- [x] 返回任务详情
- [x] completed 状态时从文件读取翻译结果
- [x] 包含 progress、error_message 等字段

**接口 4: DELETE `/api/tasks/{task_id}`**
- [x] 删除任务及其结果文件
- [x] 返回 success 状态

**接口 5: POST `/api/tasks/{task_id}/retry`**
- [x] 调用 BackgroundTaskManager.retry_task()
- [x] 返回 success 和新的 status

**接口 6: GET `/api/tasks/stats`**
- [x] 返回任务统计信息（总数、各状态数量、队列大小）

**验收标准**:
- ✅ 所有接口返回正确的 JSON 格式
- ✅ 分页查询正常工作
- ✅ 任务详情包含完整信息
- ✅ 删除操作同时清理结果文件
- ✅ 重试操作将失败任务重新加入队列
- ✅ 统计接口返回准确数据

**技术参考**:
- 参考 plan.md 第 2.1 节的 API 规格

**依赖项**:
- 依赖 1.2 BackgroundTaskManager 完成
- 依赖 1.3 TaskPersistenceService 完成
- 依赖 1.4 CacheService 扩展完成

---

### 2.2 修改应用入口

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 1.5 小时
**文件**: `backend/app.py`

**任务描述**:
修改 Flask 应用入口，集成后台任务服务

**实现要点**:
- [x] 导入并注册 `tasks_bp` 蓝图
- [x] 应用启动时初始化 `TaskPersistenceService` 并恢复任务
- [x] 应用启动时初始化 `BackgroundTaskManager`
- [x] 添加 `DELETE` 到 CORS 允许方法
- [x] 实现 `init_background_services()` 服务初始化函数
- [x] 实现 `shutdown_background_services()` 服务关闭函数
- [x] 启动时执行过期任务清理

**验收标准**:
- ✅ tasks_bp 蓝图正确注册
- ✅ 服务启动时自动恢复未完成任务
- ✅ BackgroundTaskManager 在启动时初始化
- ✅ CORS 支持 DELETE 方法
- ✅ 过期任务清理正常执行

**依赖项**:
- 依赖 2.1 任务路由创建完成

---

## Phase 3: 前端改造

**整体状态**: ✅ 已完成
**依赖项**: Phase 2 API 完成
**阶段目标**: 改造前端界面，支持后台任务管理和手动刷新

### 3.1 前端路由方案

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 0.5 小时

**任务描述**:
实现前端页面导航（采用状态管理方式替代 react-router-dom）

**实现要点**:
- [x] 使用 React useState 管理页面状态
- [x] 实现 PageState 类型定义页面类型
- [x] 实现页面切换导航函数

**验收标准**:
- ✅ 页面切换流畅
- ✅ 无需额外安装依赖
- ✅ 支持 home、stream、tasks、task-detail 四种页面

---

### 3.2 添加类型定义

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 1 小时
**文件**: `frontend/src/types/index.ts`

**任务描述**:
添加任务相关的 TypeScript 类型定义

**实现要点**:
- [x] 定义 `TaskStatus` 类型
- [x] 定义 `TaskListItem` 接口（轻量列表项）
- [x] 定义 `TaskListResponse` 接口（分页响应）
- [x] 定义 `TaskDetail` 接口（完整详情）
- [x] 定义 `BackgroundTaskRequest` 接口
- [x] 定义 `BackgroundTaskResponse` 接口
- [x] 定义 `TaskStatsResponse` 接口

**验收标准**:
- ✅ 类型定义完整且正确
- ✅ 无 TypeScript 编译错误

---

### 3.3 扩展 API 服务

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 1.5 小时
**文件**: `frontend/src/services/api.ts`

**任务描述**:
添加任务管理相关的 API 调用函数

**实现要点**:
- [x] `submitBackgroundTask()` - 提交后台任务
- [x] `getTaskList(offset, limit)` - 获取任务列表
- [x] `getTaskDetail(taskId)` - 获取任务详情
- [x] `deleteTask(taskId)` - 删除任务
- [x] `retryTask(taskId)` - 重试失败任务

**验收标准**:
- ✅ 所有 API 函数实现完整
- ✅ 返回类型正确
- ✅ 错误处理完善

---

### 3.4 改造首页

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 3 小时
**文件**: `frontend/src/pages/HomePage.tsx`

**任务描述**:
将首页改为上下结构，上方翻译表单，下方最近任务列表

**实现要点**:
- [x] 保留现有翻译表单功能
- [x] 表单提交后调用 `submitBackgroundTask()`
- [x] 添加最近任务列表（显示 10 条）
- [x] 提交后自动刷新任务列表
- [x] 任务项可点击跳转详情页
- [x] 添加"查看全部任务"链接
- [x] 活跃任务时自动每5秒刷新

**验收标准**:
- ✅ 翻译表单正常工作
- ✅ 提交后显示成功提示并刷新列表
- ✅ 最近任务列表显示正确
- ✅ 点击任务能跳转到详情页
- ✅ "查看全部任务"链接正常工作

**依赖项**:
- 依赖 3.2 类型定义完成
- 依赖 3.3 API 服务扩展完成

---

### 3.5 创建任务列表页

**状态**: ✅ 已完成
**优先级**: 中
**预计时间**: 3 小时
**文件**: `frontend/src/pages/TaskListPage.tsx`

**任务描述**:
创建独立的任务列表页面，支持无限滚动和任务管理

**实现要点**:
- [x] 创建页面组件
- [x] 实现任务列表展示
- [x] 实现无限滚动加载（使用 offset/limit）
- [x] 显示任务状态标识
- [x] 点击任务进入详情页
- [x] 支持删除任务（带确认对话框）
- [x] 添加手动刷新按钮

**验收标准**:
- ✅ 任务列表正确显示
- ✅ 无限滚动正常工作
- ✅ 删除前显示确认对话框
- ✅ 删除后列表自动更新
- ✅ 状态标识清晰可辨

**依赖项**:
- 依赖 3.2 类型定义完成
- 依赖 3.3 API 服务扩展完成

---

### 3.6 创建任务详情页

**状态**: ✅ 已完成
**优先级**: 中
**预计时间**: 3 小时
**文件**: `frontend/src/pages/TaskDetailPage.tsx`

**任务描述**:
创建任务详情页面，展示任务信息、进度和结果

**实现要点**:
- [x] 创建页面组件
- [x] 显示任务基本信息（ID、状态、创建时间等）
- [x] 显示简单进度条（百分比）
- [x] completed 状态显示翻译结果
- [x] failed 状态显示错误信息
- [x] 失败任务显示"重试"按钮
- [x] 添加手动刷新按钮
- [x] 添加返回列表的导航
- [x] 进行中任务自动刷新

**验收标准**:
- ✅ 任务信息完整显示
- ✅ 进度条正确反映 progress 值
- ✅ 翻译结果正确显示
- ✅ 错误信息正确显示
- ✅ 重试功能正常工作
- ✅ 手动刷新能更新数据

**依赖项**:
- 依赖 3.2 类型定义完成
- 依赖 3.3 API 服务扩展完成

---

### 3.7 配置路由

**状态**: ✅ 已完成
**优先级**: 高
**预计时间**: 1 小时
**文件**: `frontend/src/App.tsx`

**任务描述**:
配置页面路由（采用状态管理方式）

**实现要点**:
- [x] 定义 PageType 和 PageState 类型
- [x] 实现导航函数（navigateToHome, navigateToStream, navigateToTasks, navigateToTaskDetail）
- [x] 使用 renderPageContent() 条件渲染页面
- [x] 设置路由映射:
  - `home` → 首页（表单 + 最近任务）
  - `stream` → 实时翻译（原有流式翻译）
  - `tasks` → 任务列表页（全部任务）
  - `task-detail` → 任务详情页

**验收标准**:
- ✅ 路由正确匹配页面
- ✅ 页面切换流畅

**依赖项**:
- 依赖 3.4、3.5、3.6 页面组件完成

---

### 3.8 更新导航组件

**状态**: ✅ 已完成
**优先级**: 低
**预计时间**: 0.5 小时

**任务描述**:
在 Header 组件添加导航链接

**实现要点**:
- [x] 添加"后台任务"链接
- [x] 添加"实时翻译"链接
- [x] 添加"任务列表"链接
- [x] 当前页面高亮显示

**验收标准**:
- ✅ 导航链接显示正确
- ✅ 点击能正确跳转
- ✅ 当前页面有视觉区分

**依赖项**:
- 依赖 3.7 路由配置完成

---

## Phase 4: Docker 配置

**整体状态**: ✅ 已完成
**依赖项**: Phase 1-3 完成
**阶段目标**: 配置 Docker 以支持数据持久化

### 4.1 修改 docker-compose.yml

**状态**: ✅ 已完成
**优先级**: 中
**预计时间**: 0.5 小时
**文件**: `docker-compose.yml`

**任务描述**:
添加数据目录挂载配置

**实现要点**:
- [x] 在 backend 服务添加 volumes 配置
- [x] 挂载 `./data:/app/data`

**验收标准**:
- ✅ 容器内可以访问 /app/data 目录
- ✅ 数据在容器重启后保留

---

### 4.2 修改 Dockerfile

**状态**: ✅ 已完成
**优先级**: 中
**预计时间**: 0.5 小时
**文件**: `Dockerfile`

**任务描述**:
在 Dockerfile 中创建数据目录

**实现要点**:
- [x] 添加 `RUN mkdir -p /app/data/results`

**验收标准**:
- ✅ 镜像构建成功
- ✅ 容器启动时数据目录存在

---

## 技术工具清单

### 开发工具
- [x] Python 3.x - 后端开发
- [x] Node.js / npm - 前端开发
- [x] Docker / Docker Compose - 容器化部署

### 后端依赖库
- [x] Flask - Web 框架
- [x] threading - 多线程支持（标准库）
- [x] queue - 线程安全队列（标准库）
- [x] json - JSON 处理（标准库）

### 前端依赖库
- [x] React - UI 框架
- [x] TypeScript - 类型支持
- [x] 状态管理 - 使用 useState 替代 react-router-dom

### 配置文件
- [x] `data/tasks.json` - 任务持久化数据
- [x] `data/results/*.txt` - 翻译结果文件

---

## 参考内容

### 技术规范
- 参考 `background-translation-plan.md` 完整方案

### 关键配置
| 配置项 | 值 |
|--------|-----|
| 最大重试次数 | 3 次 |
| 重试算法 | 指数退避（1s → 2s → 4s） |
| Chunk 超时 | 5 分钟 |
| 快照间隔 | 30 秒 |
| 任务保留时间 | 7 天 |
| 清理时机 | 服务启动时 |

---

## 注意事项

### 开发规范
- ⚠️ 所有任务状态变更必须线程安全
- ⚠️ 文件操作需要原子性保证
- ⚠️ 大文本结果要存储到独立文件，避免内存膨胀

### 常见陷阱
- ❌ 直接在内存中保存翻译结果: 应写入文件后卸载
- ❌ 忽略线程安全: 队列操作和状态更新需要锁
- ❌ 硬编码超时时间: 应使用配置常量

### 最佳实践
- ✅ 使用指数退避重试，避免 API 过载
- ✅ 状态变更立即持久化，防止数据丢失
- ✅ 优雅关闭，等待当前任务完成
- ✅ 日志记录关键事件便于调试

### 测试要求
- 🧪 后台执行测试: 提交任务 → 关闭浏览器 → 重新打开 → 查看结果
- 🧪 持久化测试: 提交任务 → 重启服务 → 验证任务恢复
- 🧪 重试机制测试: 模拟 API 失败 → 验证指数退避重试
- 🧪 手动重试测试: 失败任务 → 点击重试 → 验证重新执行
- 🧪 过期清理测试: 创建测试任务 → 修改时间戳 → 触发清理
- 🧪 大文本测试: 提交大文本 → 验证内存卸载正常
- 🧪 无限滚动测试: 创建多个任务 → 验证分页加载

---

## 进度追踪

### 总体进度
- 总任务数: 16
- 已完成: 16 (100%)
- 进行中: 0
- 未开始: 0
- 阻塞中: 0

### 已完成任务
- [x] 1.1 创建数据目录
- [x] 1.2 创建 BackgroundTaskManager
- [x] 1.3 创建 TaskPersistenceService
- [x] 1.4 扩展 CacheService
- [x] 2.1 创建任务管理路由
- [x] 2.2 修改应用入口
- [x] 3.1 前端路由方案
- [x] 3.2 添加类型定义
- [x] 3.3 扩展 API 服务
- [x] 3.4 改造首页
- [x] 3.5 创建任务列表页
- [x] 3.6 创建任务详情页
- [x] 3.7 配置路由
- [x] 3.8 更新导航组件
- [x] 4.1 修改 docker-compose.yml
- [x] 4.2 修改 Dockerfile

### 遇到的问题
（无）

---

## 实现摘要

### 后端实现
| 文件 | 说明 |
|------|------|
| `backend/services/task_manager.py` | 后台任务管理器，含队列、工作线程、重试机制 |
| `backend/services/task_persistence.py` | 任务持久化服务，含快照、恢复、清理 |
| `backend/services/cache_service.py` | 扩展了列表查询、统计、状态管理方法 |
| `backend/routes/tasks.py` | 6个 RESTful API 接口 |
| `backend/app.py` | 集成后台服务初始化和关闭 |

### 前端实现
| 文件 | 说明 |
|------|------|
| `frontend/src/pages/HomePage.tsx` | 首页：表单 + 最近任务列表 |
| `frontend/src/pages/TaskListPage.tsx` | 任务列表页：分页、删除、刷新 |
| `frontend/src/pages/TaskDetailPage.tsx` | 任务详情页：进度、结果、重试 |
| `frontend/src/services/api.ts` | 任务管理 API 调用函数 |
| `frontend/src/types/index.ts` | 任务相关类型定义 |
| `frontend/src/App.tsx` | 状态管理路由、导航集成 |
| `frontend/src/components/TranslateForm.tsx` | 支持 mode 属性切换模式 |

### Docker 配置
| 文件 | 修改 |
|------|------|
| `docker-compose.yml` | 添加 `./data:/app/data` 卷挂载 |
| `Dockerfile` | 添加 `RUN mkdir -p /app/data/results` |

---

*文档最后更新: 2026-01-08*
*项目状态: ✅ 100% 完成*
