# 后台翻译功能实施计划

## 概述

将翻译代理系统从"前台流式翻译"改为"后台任务翻译"，实现关闭浏览器后翻译任务继续执行。

### 核心决策
| 决策项 | 选择 |
|--------|------|
| **持久化** | JSON 文件持久化，重启后恢复未完成任务 |
| **前端** | 首页合并展示（表单 + 任务列表），保留任务详情页 |
| **并发** | 单工作线程串行执行 |
| **实时更新** | 取消 SSE，手动刷新获取进度 |
| **用户认证** | 无认证，所有用户共享任务列表 |

---

## 架构变更

```
[现有流程 - 已废弃]
浏览器 --POST--> Flask --SSE流--> 浏览器关闭 = 任务终止

[新流程]
浏览器 --POST--> Flask --> 返回 task_id --> 浏览器可关闭
                  |
                  V
          [后台任务队列] --> [单工作线程串行执行]
                  |
                  V
          [JSON 持久化] <--> [CacheService 内存缓存]
                  |
                  V
浏览器重连 --GET task_id--> 手动刷新查询进度/结果
```

---

## 技术规格详细说明

### 1. 失败处理与重试机制

| 配置项 | 值 |
|--------|-----|
| 失败策略 | 自动重试 |
| 重试算法 | 指数退避（1秒 → 2秒 → 4秒） |
| 最大重试次数 | 3 次 |
| 重试耗尽后 | 标记整个任务为 `failed` |

```python
# 重试间隔计算
def get_retry_delay(retry_count: int) -> float:
    """指数退避：1s, 2s, 4s"""
    return 2 ** retry_count  # retry_count: 0, 1, 2
```

### 2. 超时机制

| 配置项 | 值 |
|--------|-----|
| 超时级别 | Chunk 级 |
| 超时时间 | 5 分钟 |
| 超时处理 | 触发重试机制 |

### 3. 持久化策略

| 配置项 | 值 |
|--------|-----|
| 快照间隔 | 30 秒 |
| 立即持久化时机 | 任务状态变更（pending→in_progress→completed/failed） |
| 结果存储 | 内存卸载模式 |

**内存卸载模式说明：**
- 任务完成后，翻译结果写入独立文件 `data/results/{task_id}.txt`
- 内存中仅保留任务元数据（状态、进度、创建时间等）
- 查看结果时从文件读取

```
data/
├── tasks.json           # 任务元数据（不含翻译结果）
└── results/
    ├── {task_id_1}.txt  # 任务1的翻译结果
    ├── {task_id_2}.txt  # 任务2的翻译结果
    └── ...
```

### 4. 任务队列

| 配置项 | 值 |
|--------|-----|
| 队列容量 | 无限制（依赖系统内存） |
| 执行方式 | 单工作线程串行执行 |
| 重复任务 | 允许（生成新 task_id） |

### 5. 任务生命周期

| 配置项 | 值 |
|--------|-----|
| 任务保留时间 | 7 天 |
| 清理时机 | 服务启动时 + 每日凌晨 0 点 |
| 清理范围 | completed/failed 状态且超过 7 天的任务 |

### 6. 服务重启恢复

| 配置项 | 值 |
|--------|-----|
| 恢复策略 | 谨慎恢复 |
| pending 任务 | 保持 pending，重新加入队列 |
| in_progress 任务 | 重置为 pending，重新排队执行 |
| completed/failed 任务 | 保持原状态 |

### 7. 日志记录

记录关键事件：
- 任务提交（task_id, 内容摘要）
- 任务开始执行
- 任务完成/失败（耗时、chunk 数量）
- 重试事件（chunk 索引、重试次数、错误原因）
- 持久化操作（快照写入、任务恢复、过期清理）

---

## 实施步骤

### 阶段 1: 后端基础设施

#### 1.1 创建数据目录
- [x] 创建 `data/` 目录
- [x] 创建 `data/results/` 子目录
- [x] 添加 `.gitkeep` 文件

#### 1.2 创建 `backend/services/task_manager.py`
后台任务管理器，核心职责：
- 维护任务队列（线程安全）
- 单工作线程串行处理任务
- 与 CacheService 协作更新状态
- 支持任务手动重试

关键实现：
```python
class BackgroundTaskManager:
    # 配置常量
    MAX_RETRY_COUNT = 3
    CHUNK_TIMEOUT_SECONDS = 300  # 5分钟

    # 核心属性
    - _task_queue: queue.Queue  # 任务队列（无限制）
    - _worker: threading.Thread  # 单工作线程
    - _running: bool  # 运行状态标志

    # 公共方法
    + submit_task(task) -> str       # 提交任务，返回 task_id
    + retry_task(task_id) -> bool    # 手动重试失败任务
    + cancel_task(task_id) -> bool   # 取消排队中的任务
    + shutdown()                     # 优雅关闭

    # 私有方法
    - _worker_loop()                 # 工作线程主循环
    - _execute_task(task)            # 执行单个任务
    - _execute_chunk_with_retry(chunk, task_id) -> str  # 带重试的chunk执行
    - _get_retry_delay(retry_count) -> float  # 计算重试延迟
```

#### 1.3 创建 `backend/services/task_persistence.py`
任务持久化服务：
- 每 30 秒快照到 `data/tasks.json`
- 任务状态变更时立即持久化
- 启动时从文件恢复未完成任务
- 每日清理过期任务

数据结构：
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

#### 1.4 扩展 `backend/services/cache_service.py`
- [x] 添加 `get_all_tasks()` 方法用于持久化
- [x] 添加 `restore_tasks(tasks_dict)` 方法用于恢复
- [ ] 添加 `get_task_metadata(task_id)` 方法（不含结果）
- [ ] 添加 `save_result_to_file(task_id, result)` 方法

---

### 阶段 2: API 路由

#### 2.1 创建 `backend/routes/tasks.py`
新增 4 个 API 接口（移除 SSE 接口）：

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/translate/background` | 提交后台翻译任务 |
| GET | `/api/tasks` | 获取任务列表（支持无限滚动） |
| GET | `/api/tasks/{task_id}` | 获取任务详情（含翻译结果） |
| DELETE | `/api/tasks/{task_id}` | 删除任务 |
| POST | `/api/tasks/{task_id}/retry` | 手动重试失败任务 |

**API 详细规格：**

```
POST /api/translate/background
Request:
{
  "content": "待翻译内容",
  "source_lang": "en",
  "target_lang": "zh",
  "domain": "general"
}
Response:
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "ISO时间"
}

GET /api/tasks?offset=0&limit=20
Response:
{
  "tasks": [...],
  "total": 50,
  "has_more": true
}

GET /api/tasks/{task_id}
Response:
{
  "task_id": "...",
  "status": "completed",
  "progress": 100,
  "result": "翻译结果...",  // 从文件读取
  "created_at": "...",
  "completed_at": "..."
}

DELETE /api/tasks/{task_id}
Response:
{
  "success": true
}

POST /api/tasks/{task_id}/retry
Response:
{
  "success": true,
  "status": "pending"
}
```

#### 2.2 修改 `backend/app.py`
- [x] 导入并注册 `tasks_bp` 蓝图
- [x] 应用启动时初始化 `TaskPersistenceService` 并恢复任务
- [x] 应用启动时初始化 `BackgroundTaskManager`
- [x] 添加 `DELETE` 到 CORS 允许方法
- [ ] 注册每日清理定时任务

---

### 阶段 3: 前端改造

#### 3.1 安装依赖
```bash
cd frontend && npm install react-router-dom
```

#### 3.2 添加类型定义 `frontend/src/types/index.ts`
```typescript
// 任务列表项（轻量）
interface TaskListItem {
  task_id: string;
  title: string;           // 内容摘要（前50字符）
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;        // 0-100
  created_at: string;
  domain: string;
}

// 任务列表响应
interface TaskListResponse {
  tasks: TaskListItem[];
  total: number;
  has_more: boolean;
}

// 任务详情（完整）
interface TaskDetail extends TaskListItem {
  original_content: string;
  result?: string;         // 仅 completed 状态有值
  error_message?: string;  // 仅 failed 状态有值
  completed_at?: string;
}
```

#### 3.3 扩展 API 服务 `frontend/src/services/api.ts`
- [x] `submitBackgroundTask()` - 提交后台任务
- [x] `getTaskList(offset, limit)` - 获取任务列表
- [x] `getTaskDetail(taskId)` - 获取任务详情
- [x] `deleteTask(taskId)` - 删除任务
- [x] `retryTask(taskId)` - 重试失败任务

#### 3.4 改造首页 `frontend/src/pages/HomePage.tsx`
**布局：上下结构**
```
┌─────────────────────────────────────┐
│         翻译表单（现有）              │
│  [URL输入] [语言选择] [提交按钮]      │
├─────────────────────────────────────┤
│         最近任务（10条）              │
│  ┌─────┐ ┌─────┐ ┌─────┐           │
│  │任务1│ │任务2│ │任务3│ ...       │
│  └─────┘ └─────┘ └─────┘           │
│              [查看全部任务 →]         │
└─────────────────────────────────────┘
```

**功能：**
- 提交后页面内刷新任务列表
- 显示最近 10 个任务
- 点击任务跳转详情页
- "查看全部任务"链接跳转任务列表页

#### 3.5 创建任务列表页 `frontend/src/pages/TaskListPage.tsx`
- 显示所有任务（无筛选）
- 无限滚动加载
- 点击任务进入详情页
- 支持删除（带确认对话框）

#### 3.6 创建任务详情页 `frontend/src/pages/TaskDetailPage.tsx`
- 显示任务基本信息
- 显示简单进度条（仅百分比）
- 显示翻译结果（completed 状态）
- 显示错误信息（failed 状态）
- 失败任务显示"重试"按钮
- 手动刷新按钮

#### 3.7 改造路由 `frontend/src/App.tsx`
```
/              → 首页（表单 + 最近任务）
/tasks         → 任务列表页（全部任务）
/tasks/:taskId → 任务详情页
```

#### 3.8 更新导航
- 在 Header 添加"任务列表"链接

---

### 阶段 4: Docker 配置

#### 4.1 修改 `docker-compose.yml`
```yaml
volumes:
  - ./data:/app/data  # 挂载数据目录
```

#### 4.2 修改 `Dockerfile`
```dockerfile
RUN mkdir -p /app/data/results
```

---

## 关键文件清单

### 新建文件
| 文件路径 | 说明 |
|---------|------|
| `docs/background-translation-plan.md` | 方案文档（本文件） |
| `backend/services/task_manager.py` | 后台任务管理器 |
| `backend/services/task_persistence.py` | 任务持久化服务 |
| `backend/routes/tasks.py` | 任务管理 API 路由 |
| `frontend/src/pages/TaskListPage.tsx` | 任务列表页 |
| `frontend/src/pages/TaskDetailPage.tsx` | 任务详情页 |
| `data/.gitkeep` | 数据目录占位 |
| `data/results/.gitkeep` | 结果目录占位 |

### 修改文件
| 文件路径 | 改动说明 |
|---------|---------|
| `backend/app.py` | 注册路由、初始化后台服务、定时清理 |
| `backend/services/cache_service.py` | 添加批量查询/恢复/文件操作方法 |
| `frontend/src/types/index.ts` | 添加任务相关类型 |
| `frontend/src/services/api.ts` | 添加任务 API 函数 |
| `frontend/src/App.tsx` | 添加 React Router |
| `frontend/src/pages/HomePage.tsx` | 改为合并布局 |
| `docker-compose.yml` | 添加数据目录挂载 |
| `Dockerfile` | 创建数据目录 |

---

## 测试要点

1. **后台执行测试**: 提交任务 → 关闭浏览器 → 重新打开 → 查看结果
2. **持久化测试**: 提交任务 → 重启服务 → 验证任务恢复并继续（in_progress 重置为 pending）
3. **重试机制测试**: 模拟 API 失败 → 验证指数退避重试 → 3次后标记失败
4. **手动重试测试**: 失败任务 → 点击重试 → 验证重新执行
5. **过期清理测试**: 创建测试任务 → 修改时间戳 → 触发清理 → 验证删除
6. **大文本测试**: 提交大文本 → 验证内存卸载正常工作
7. **无限滚动测试**: 创建多个任务 → 验证分页加载

---

## 风险与注意事项

1. **内存限制**: 大量任务会占用内存，通过内存卸载机制缓解
2. **单机限制**: 方案不支持多实例部署
3. **恢复限制**: in_progress 任务恢复后从头执行，可能导致部分重复翻译
4. **无实时更新**: 用户需手动刷新查看进度，体验略逊于 SSE

---

## 变更历史

| 日期 | 变更内容 |
|------|---------|
| 初版 | 基础方案，包含 SSE 实时订阅 |
| v2 | 基于访谈完善：取消 SSE、添加重试机制、内存卸载、首页合并布局等 |
