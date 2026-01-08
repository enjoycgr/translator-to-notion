import { useState, useEffect, useCallback } from 'react';
import { getTaskList, deleteTask } from '@/services/api';
import type { TaskListItem, TaskStatus } from '@/types';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Trash2,
  RefreshCw,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';

interface TaskListPageProps {
  onSelectTask: (taskId: string) => void;
  onBack: () => void;
}

const STATUS_CONFIG: Record<TaskStatus, { icon: React.ReactNode; label: string; color: string }> = {
  pending: {
    icon: <Clock className="w-4 h-4" />,
    label: '排队中',
    color: 'text-yellow-600 bg-yellow-50',
  },
  preparing: {
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
    label: '准备中',
    color: 'text-purple-600 bg-purple-50',
  },
  in_progress: {
    icon: <Loader2 className="w-4 h-4 animate-spin" />,
    label: '翻译中',
    color: 'text-blue-600 bg-blue-50',
  },
  completed: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    label: '已完成',
    color: 'text-green-600 bg-green-50',
  },
  failed: {
    icon: <XCircle className="w-4 h-4" />,
    label: '失败',
    color: 'text-red-600 bg-red-50',
  },
};

export function TaskListPage({ onSelectTask, onBack }: TaskListPageProps) {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchTasks = useCallback(async (offset: number = 0, append: boolean = false) => {
    try {
      if (append) {
        setIsLoadingMore(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const response = await getTaskList(offset, 20);

      if (response.success && response.data) {
        if (append) {
          setTasks((prev) => [...prev, ...response.data!.tasks]);
        } else {
          setTasks(response.data.tasks);
        }
        setTotal(response.data.total);
        setHasMore(response.data.has_more);
      } else {
        setError(response.error?.message || '获取任务列表失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取任务列表失败');
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleLoadMore = () => {
    if (!isLoadingMore && hasMore) {
      fetchTasks(tasks.length, true);
    }
  };

  const handleDelete = async (taskId: string) => {
    try {
      const response = await deleteTask(taskId);
      if (response.success) {
        setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
        setTotal((prev) => prev - 1);
      } else {
        setError(response.error?.message || '删除失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
    setDeleteConfirm(null);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-gray-600">加载任务列表...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">任务列表</h2>
          <p className="text-sm text-gray-500 mt-1">共 {total} 个任务</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchTasks()}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Task List */}
      {tasks.length === 0 ? (
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="p-4 bg-gray-100 rounded-full inline-block mb-4">
            <Clock className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-700 mb-2">暂无任务</h3>
          <p className="text-sm text-gray-500">提交翻译任务后会显示在这里</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-lg divide-y divide-gray-100">
          {tasks.map((task) => {
            const statusConfig = STATUS_CONFIG[task.status];
            return (
              <div
                key={task.task_id}
                className="p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {/* Status Badge */}
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.color}`}
                  >
                    {statusConfig.icon}
                    {statusConfig.label}
                  </div>

                  {/* Task Info */}
                  <div
                    className="flex-1 min-w-0 cursor-pointer"
                    onClick={() => onSelectTask(task.task_id)}
                  >
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {task.title}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{task.domain}</span>
                      <span>{formatDate(task.created_at)}</span>
                      {task.status === 'in_progress' && (
                        <span className="text-blue-600">{task.progress}%</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    {deleteConfirm === task.task_id ? (
                      <>
                        <button
                          onClick={() => handleDelete(task.task_id)}
                          className="px-3 py-1 text-xs text-white bg-red-500 hover:bg-red-600 rounded transition-colors"
                        >
                          确认删除
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(null)}
                          className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800"
                        >
                          取消
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setDeleteConfirm(task.task_id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onSelectTask(task.task_id)}
                          className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                          title="查看详情"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center">
          <button
            onClick={handleLoadMore}
            disabled={isLoadingMore}
            className="px-6 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoadingMore ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                加载中...
              </span>
            ) : (
              '加载更多'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
