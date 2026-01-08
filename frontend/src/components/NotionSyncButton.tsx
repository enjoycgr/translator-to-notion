import { useState } from 'react';
import { syncToNotion } from '@/services/api';
import { LoadingSpinner } from './LoadingSpinner';
import { ExternalLink, Upload, Check, AlertCircle } from 'lucide-react';

interface NotionSyncButtonProps {
  taskId: string;
  title?: string;
  disabled?: boolean;
}

export function NotionSyncButton({
  taskId,
  title,
  disabled = false,
}: NotionSyncButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [pageUrl, setPageUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSync = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await syncToNotion({
        task_id: taskId,
        title: title,
      });

      if (response.success && response.data) {
        setPageUrl(response.data.notion_page_url);
      } else {
        setError(response.error?.message || '同步失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '同步失败');
    } finally {
      setIsLoading(false);
    }
  };

  // Already synced - show success state
  if (pageUrl) {
    return (
      <div className="flex items-center gap-4 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center gap-2 text-green-700">
          <Check className="w-5 h-5" />
          <span className="font-medium">已同步到 Notion</span>
        </div>
        <a
          href={pageUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          打开页面
        </a>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2 text-red-700 mb-2">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">同步失败</span>
        </div>
        <p className="text-sm text-red-600 mb-3">{error}</p>
        <button
          onClick={handleSync}
          disabled={disabled || isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          重试
        </button>
      </div>
    );
  }

  // Default state
  return (
    <button
      onClick={handleSync}
      disabled={disabled || isLoading}
      className={`
        flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all
        ${
          disabled || isLoading
            ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
            : 'bg-gray-800 hover:bg-gray-900 text-white'
        }
      `}
    >
      {isLoading ? (
        <>
          <LoadingSpinner size="sm" />
          同步中...
        </>
      ) : (
        <>
          <Upload className="w-5 h-5" />
          同步到 Notion
        </>
      )}
    </button>
  );
}

export default NotionSyncButton;
