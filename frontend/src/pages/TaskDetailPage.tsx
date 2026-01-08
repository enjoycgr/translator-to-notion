import { useState, useEffect, useCallback } from 'react';
import { getTaskDetail, retryTask } from '@/services/api';
import type { TaskDetail, TaskStatus } from '@/types';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import ReactMarkdown from 'react-markdown';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  RotateCcw,
  FileText,
  ExternalLink,
} from 'lucide-react';

interface TaskDetailPageProps {
  taskId: string;
  onBack: () => void;
}

const STATUS_CONFIG: Record<TaskStatus, { icon: React.ReactNode; label: string; color: string; bg: string }> = {
  pending: {
    icon: <Clock className="w-5 h-5" />,
    label: '排队中',
    color: 'text-yellow-600',
    bg: 'bg-yellow-50 border-yellow-200',
  },
  preparing: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    label: '准备中',
    color: 'text-purple-600',
    bg: 'bg-purple-50 border-purple-200',
  },
  in_progress: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    label: '翻译中',
    color: 'text-blue-600',
    bg: 'bg-blue-50 border-blue-200',
  },
  completed: {
    icon: <CheckCircle2 className="w-5 h-5" />,
    label: '已完成',
    color: 'text-green-600',
    bg: 'bg-green-50 border-green-200',
  },
  failed: {
    icon: <XCircle className="w-5 h-5" />,
    label: '失败',
    color: 'text-red-600',
    bg: 'bg-red-50 border-red-200',
  },
};

export function TaskDetailPage({ taskId, onBack }: TaskDetailPageProps) {
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchTask = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await getTaskDetail(taskId);

      if (response.success && response.data) {
        setTask(response.data);
      } else {
        setError(response.error?.message || '获取任务详情失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取任务详情失败');
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  // Auto-refresh for active tasks (pending, preparing, in_progress)
  useEffect(() => {
    if (task?.status === 'in_progress' || task?.status === 'pending' || task?.status === 'preparing') {
      const interval = setInterval(fetchTask, 5000);
      return () => clearInterval(interval);
    }
  }, [task?.status, fetchTask]);

  const handleCopy = async () => {
    const content = task?.result || task?.partial_result || '';
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRetry = async () => {
    try {
      setIsRetrying(true);
      const response = await retryTask(taskId);
      if (response.success) {
        // Refresh task detail
        await fetchTask();
      } else {
        setError(response.error?.message || '重试失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '重试失败');
    } finally {
      setIsRetrying(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isLoading && !task) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-gray-600">加载任务详情...</p>
      </div>
    );
  }

  if (error && !task) {
    return (
      <div className="space-y-4">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
        >
          <ArrowLeft className="w-4 h-4" />
          返回列表
        </button>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!task) return null;

  const statusConfig = STATUS_CONFIG[task.status];
  const translationContent = task.result || task.partial_result || '';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回列表
          </button>
          <h2 className="text-xl font-semibold text-gray-900">{task.title}</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchTask}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title="刷新"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Status Card */}
      <div className={`rounded-xl border p-4 ${statusConfig.bg}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={statusConfig.color}>{statusConfig.icon}</div>
            <div>
              <p className={`font-medium ${statusConfig.color}`}>{statusConfig.label}</p>
              {task.status === 'in_progress' && (
                <p className="text-sm text-gray-600 mt-1">
                  进度: {task.progress}% ({task.completed_chunks}/{task.total_chunks} chunks)
                </p>
              )}
            </div>
          </div>

          {/* Retry button for failed tasks */}
          {task.status === 'failed' && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {isRetrying ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RotateCcw className="w-4 h-4" />
              )}
              重试
            </button>
          )}
        </div>

        {/* Progress bar for in_progress */}
        {task.status === 'in_progress' && (
          <div className="mt-4">
            <div className="h-2 bg-blue-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-500"
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error message for failed */}
        {task.status === 'failed' && task.error_message && (
          <div className="mt-4 p-3 bg-red-100 rounded-lg">
            <p className="text-sm text-red-700">{task.error_message}</p>
          </div>
        )}
      </div>

      {/* Task Info */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="font-medium text-gray-900 mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4" />
          任务信息
        </h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">任务ID</p>
            <p className="font-mono text-gray-900 truncate" title={task.task_id}>
              {task.task_id}
            </p>
          </div>
          <div>
            <p className="text-gray-500">领域</p>
            <p className="text-gray-900">{task.domain}</p>
          </div>
          <div>
            <p className="text-gray-500">创建时间</p>
            <p className="text-gray-900">{formatDate(task.created_at)}</p>
          </div>
          <div>
            <p className="text-gray-500">更新时间</p>
            <p className="text-gray-900">{formatDate(task.updated_at)}</p>
          </div>
          {task.source_url && (
            <div className="col-span-2">
              <p className="text-gray-500">来源URL</p>
              <a
                href={task.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline flex items-center gap-1"
              >
                {task.source_url}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Translation Result */}
      {translationContent && (
        <div className="bg-white rounded-xl shadow-lg">
          <div className="flex items-center justify-between p-4 border-b">
            <h3 className="font-medium text-gray-900">
              {task.status === 'completed' ? '翻译结果' : '翻译进度'}
            </h3>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-500" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  复制
                </>
              )}
            </button>
          </div>
          <div className="p-6 prose prose-sm max-w-none">
            <ReactMarkdown>{translationContent}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Waiting message for pending */}
      {task.status === 'pending' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center">
          <Clock className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <p className="text-yellow-700">任务正在排队等待处理...</p>
          <p className="text-sm text-yellow-600 mt-2">
            页面会自动刷新，您也可以关闭页面稍后查看
          </p>
        </div>
      )}

      {/* Preparing message */}
      {task.status === 'preparing' && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-6 text-center">
          <Loader2 className="w-12 h-12 text-purple-400 mx-auto mb-4 animate-spin" />
          <p className="text-purple-700">{task.status_message || '正在准备翻译任务...'}</p>
          <p className="text-sm text-purple-600 mt-2">
            页面会自动刷新，您也可以关闭页面稍后查看
          </p>
        </div>
      )}
    </div>
  );
}
