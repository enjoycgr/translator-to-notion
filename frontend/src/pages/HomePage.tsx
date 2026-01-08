import { useState, useEffect, useCallback } from 'react';
import { submitBackgroundTask, getTaskList } from '@/services/api';
import type { Domain, TaskListItem, TaskStatus } from '@/types';
import { TranslateForm } from '@/components/TranslateForm';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronRight,
  Languages,
  RefreshCw,
  Check,
} from 'lucide-react';

interface HomePageProps {
  onSelectTask: (taskId: string) => void;
  onViewAllTasks: () => void;
}

const STATUS_CONFIG: Record<TaskStatus, { icon: React.ReactNode; label: string; color: string }> = {
  pending: {
    icon: <Clock className="w-3 h-3" />,
    label: '排队',
    color: 'text-yellow-600 bg-yellow-50',
  },
  preparing: {
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
    label: '准备',
    color: 'text-purple-600 bg-purple-50',
  },
  in_progress: {
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
    label: '翻译中',
    color: 'text-blue-600 bg-blue-50',
  },
  completed: {
    icon: <CheckCircle2 className="w-3 h-3" />,
    label: '完成',
    color: 'text-green-600 bg-green-50',
  },
  failed: {
    icon: <XCircle className="w-3 h-3" />,
    label: '失败',
    color: 'text-red-600 bg-red-50',
  },
};

export function HomePage({ onSelectTask, onViewAllTasks }: HomePageProps) {
  const [recentTasks, setRecentTasks] = useState<TaskListItem[]>([]);
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<{
    success: boolean;
    taskId?: string;
    error?: string;
  } | null>(null);

  const fetchRecentTasks = useCallback(async () => {
    try {
      setIsLoadingTasks(true);
      const response = await getTaskList(0, 10);
      if (response.success && response.data) {
        setRecentTasks(response.data.tasks);
      }
    } catch {
      // Silently fail for recent tasks
    } finally {
      setIsLoadingTasks(false);
    }
  }, []);

  useEffect(() => {
    fetchRecentTasks();
  }, [fetchRecentTasks]);

  // Auto-refresh for active tasks
  useEffect(() => {
    const hasActiveTasks = recentTasks.some(
      (t) => t.status === 'pending' || t.status === 'preparing' || t.status === 'in_progress'
    );
    if (hasActiveTasks) {
      const interval = setInterval(fetchRecentTasks, 5000);
      return () => clearInterval(interval);
    }
  }, [recentTasks, fetchRecentTasks]);

  const handleSubmit = async (data: {
    content?: string;
    url?: string;
    title?: string;
    domain: Domain;
  }) => {
    if (!data.content && !data.url) {
      return;
    }

    try {
      setIsSubmitting(true);
      setSubmitResult(null);

      const response = await submitBackgroundTask({
        content: data.content,
        url: data.url,
        title: data.title,
        domain: data.domain,
      });

      if (response.success && response.data) {
        setSubmitResult({
          success: true,
          taskId: response.data.task_id,
        });
        // Refresh task list
        await fetchRecentTasks();
      } else {
        setSubmitResult({
          success: false,
          error: response.error?.message || '提交失败',
        });
      }
    } catch (err) {
      setSubmitResult({
        success: false,
        error: err instanceof Error ? err.message : '提交失败',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className="grid lg:grid-cols-2 gap-8">
      {/* Left: Form */}
      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Languages className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">提交翻译任务</h2>
          </div>

          <TranslateForm
            onSubmit={handleSubmit}
            isLoading={isSubmitting}
            mode="background"
          />

          {/* Submit Result */}
          {submitResult && (
            <div
              className={`mt-4 p-4 rounded-lg ${
                submitResult.success
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}
            >
              {submitResult.success ? (
                <div className="flex items-center gap-3">
                  <Check className="w-5 h-5 text-green-500" />
                  <div>
                    <p className="text-green-700 font-medium">任务已提交</p>
                    <p className="text-sm text-green-600 mt-1">
                      任务将在后台执行，您可以关闭页面稍后查看结果
                    </p>
                  </div>
                  <button
                    onClick={() => onSelectTask(submitResult.taskId!)}
                    className="ml-auto px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition-colors"
                  >
                    查看任务
                  </button>
                </div>
              ) : (
                <p className="text-red-600">{submitResult.error}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right: Recent Tasks */}
      <div className="space-y-6">
        <div className="bg-white rounded-xl shadow-lg">
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="font-semibold text-gray-900">最近任务</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={fetchRecentTasks}
                className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                title="刷新"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingTasks ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={onViewAllTasks}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                查看全部
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {isLoadingTasks && recentTasks.length === 0 ? (
            <div className="p-8 flex flex-col items-center">
              <LoadingSpinner />
              <p className="mt-2 text-sm text-gray-500">加载中...</p>
            </div>
          ) : recentTasks.length === 0 ? (
            <div className="p-8 text-center">
              <div className="p-3 bg-gray-100 rounded-full inline-block mb-3">
                <Clock className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-gray-500 text-sm">暂无任务</p>
              <p className="text-gray-400 text-xs mt-1">提交翻译任务后会显示在这里</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {recentTasks.map((task) => {
                const statusConfig = STATUS_CONFIG[task.status];
                return (
                  <div
                    key={task.task_id}
                    onClick={() => onSelectTask(task.task_id)}
                    className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {/* Status Icon */}
                      <div
                        className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${statusConfig.color}`}
                      >
                        {statusConfig.icon}
                        {statusConfig.label}
                      </div>

                      {/* Task Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 truncate">{task.title}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {formatDate(task.created_at)}
                          {task.status === 'in_progress' && (
                            <span className="ml-2 text-blue-600">{task.progress}%</span>
                          )}
                        </p>
                      </div>

                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="bg-primary-50 border border-primary-100 rounded-xl p-6">
          <h3 className="font-medium text-primary-900 mb-2">后台翻译说明</h3>
          <ul className="space-y-2 text-sm text-primary-700">
            <li className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
              任务提交后在后台执行，可以关闭浏览器
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
              服务重启后任务会自动恢复执行
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
              翻译结果保存 7 天
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
