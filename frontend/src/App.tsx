import { useState, useCallback } from 'react';
import { translateStream, setAccessKey, getAccessKey, hasAccessKey } from '@/services/api';
import type { Domain, TranslationState } from '@/types';
import { TranslateForm } from '@/components/TranslateForm';
import { ResultDisplay } from '@/components/ResultDisplay';
import { NotionSyncButton } from '@/components/NotionSyncButton';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Settings, Key, Languages, AlertCircle, X, Check, ExternalLink, Loader2 } from 'lucide-react';

function App() {
  // Translation state
  const [translation, setTranslation] = useState<TranslationState>({
    isLoading: false,
    isStreaming: false,
    translatedContent: '',
  });

  // Notion 同步状态
  const [notionSync, setNotionSync] = useState<{
    shouldSync: boolean;
    isSyncing: boolean;
    syncResult: { success: boolean; pageUrl?: string; error?: string } | null;
  }>({
    shouldSync: false,
    isSyncing: false,
    syncResult: null,
  });

  // Access key modal state
  const [showSettings, setShowSettings] = useState(!hasAccessKey());
  const [accessKeyInput, setAccessKeyInput] = useState(getAccessKey());

  // Handle translation submission
  const handleTranslate = useCallback(
    async (data: {
      content?: string;
      url?: string;
      title?: string;
      domain: Domain;
      syncToNotion?: boolean;
    }) => {
      // Check for access key
      if (!hasAccessKey()) {
        setShowSettings(true);
        return;
      }

      // Reset state
      setTranslation({
        isLoading: true,
        isStreaming: true,
        translatedContent: '',
        originalContent: data.content,
        title: data.title,
        sourceUrl: data.url,
        domain: data.domain,
      });

      // 重置 Notion 同步状态，如果需要同步则设置为同步中
      setNotionSync({
        shouldSync: data.syncToNotion || false,
        isSyncing: data.syncToNotion || false,
        syncResult: null,
      });

      try {
        // Use streaming translation
        let fullContent = '';

        for await (const chunk of translateStream({
          content: data.content,
          url: data.url,
          title: data.title,
          domain: data.domain,
          sync_to_notion: data.syncToNotion,
        })) {
          // 处理 notion_synced 事件
          if (chunk.success !== undefined || chunk.error !== undefined) {
            if (chunk.success) {
              setNotionSync((prev) => ({
                ...prev,
                isSyncing: false,
                syncResult: {
                  success: true,
                  pageUrl: chunk.notion_page_url,
                },
              }));
            } else {
              setNotionSync((prev) => ({
                ...prev,
                isSyncing: false,
                syncResult: {
                  success: false,
                  error: chunk.error || '同步失败',
                },
              }));
            }
            continue;
          }

          // 只有当 chunk.text 存在时才拼接，避免 undefined 被转为字符串
          if (chunk.text) {
            fullContent += chunk.text;
          }

          setTranslation((prev) => ({
            ...prev,
            translatedContent: fullContent,
            isStreaming: !chunk.is_complete,
          }));

          if (chunk.is_complete) {
            // Calculate approximate cost from tokens
            const cost =
              chunk.input_tokens && chunk.output_tokens
                ? (chunk.input_tokens * 3 + chunk.output_tokens * 15) / 1000000
                : undefined;

            setTranslation((prev) => ({
              ...prev,
              isLoading: false,
              isStreaming: false,
              taskId: chunk.task_id,
              cost,
            }));
          }
        }
      } catch (err) {
        setTranslation((prev) => ({
          ...prev,
          isLoading: false,
          isStreaming: false,
          error: err instanceof Error ? err.message : '翻译失败',
        }));
        // 同步失败
        if (notionSync.shouldSync) {
          setNotionSync((prev) => ({
            ...prev,
            isSyncing: false,
            syncResult: {
              success: false,
              error: '翻译失败，无法同步',
            },
          }));
        }
      }
    },
    []
  );
  // Handle access key save
  const handleSaveAccessKey = () => {
    if (accessKeyInput.trim()) {
      setAccessKey(accessKeyInput.trim());
      setShowSettings(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Languages className="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  翻译代理系统
                </h1>
                <p className="text-sm text-gray-500">
                  基于 Claude AI 的英译中翻译
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="设置"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Form */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <TranslateForm
                onSubmit={handleTranslate}
                isLoading={translation.isLoading}
              />
            </div>
          </div>

          {/* Right: Result */}
          <div className="space-y-6">
            {translation.error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-medium text-red-800">翻译出错</h3>
                  <p className="text-sm text-red-600 mt-1">
                    {translation.error}
                  </p>
                </div>
              </div>
            )}

            {translation.isLoading && !translation.translatedContent && (
              <div className="bg-white rounded-xl shadow-lg p-8 flex flex-col items-center justify-center">
                <LoadingSpinner size="lg" />
                <p className="mt-4 text-gray-600">正在获取内容并翻译...</p>
              </div>
            )}

            {translation.translatedContent && (
              <>
                <ResultDisplay
                  originalContent={translation.originalContent}
                  translatedContent={translation.translatedContent}
                  title={translation.title}
                  sourceUrl={translation.sourceUrl}
                  domain={translation.domain}
                  cost={translation.cost}
                  isStreaming={translation.isStreaming}
                />

                {translation.taskId && !translation.isLoading && (
                  <div className="bg-white rounded-xl shadow-lg p-6">
                    <h3 className="font-medium text-gray-900 mb-4">
                      同步到 Notion
                    </h3>

                    {/* 自动同步中 */}
                    {notionSync.isSyncing && (
                      <div className="flex items-center gap-3 text-gray-600">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>正在同步到 Notion...</span>
                      </div>
                    )}

                    {/* 自动同步成功 */}
                    {notionSync.syncResult?.success && (
                      <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-2 text-green-700">
                          <Check className="w-5 h-5" />
                          <span className="font-medium">已自动同步到 Notion</span>
                        </div>
                        <a
                          href={notionSync.syncResult.pageUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm"
                        >
                          <ExternalLink className="w-4 h-4" />
                          打开页面
                        </a>
                      </div>
                    )}

                    {/* 自动同步失败 */}
                    {notionSync.syncResult && !notionSync.syncResult.success && (
                      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-center gap-2 text-red-700 mb-2">
                          <AlertCircle className="w-5 h-5" />
                          <span className="font-medium">自动同步失败</span>
                        </div>
                        <p className="text-sm text-red-600 mb-3">{notionSync.syncResult.error}</p>
                        <NotionSyncButton
                          taskId={translation.taskId}
                          title={translation.title}
                          disabled={translation.isLoading}
                        />
                      </div>
                    )}

                    {/* 未选择自动同步 - 显示手动按钮 */}
                    {!notionSync.shouldSync && !notionSync.isSyncing && !notionSync.syncResult && (
                      <NotionSyncButton
                        taskId={translation.taskId}
                        title={translation.title}
                        disabled={translation.isLoading}
                      />
                    )}
                  </div>
                )}
              </>
            )}

            {!translation.isLoading && !translation.translatedContent && (
              <div className="bg-white rounded-xl shadow-lg p-8 flex flex-col items-center justify-center text-center">
                <div className="p-4 bg-gray-100 rounded-full mb-4">
                  <Languages className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-700 mb-2">
                  准备翻译
                </h3>
                <p className="text-sm text-gray-500 max-w-xs">
                  在左侧输入内容或 URL，选择翻译领域后点击"开始翻译"
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-auto">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <p className="text-center text-sm text-gray-500">
            Translation Agent System v1.0.0 · Powered by Claude AI
          </p>
        </div>
      </footer>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold text-gray-900">设置</h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label
                  htmlFor="accessKey"
                  className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2"
                >
                  <Key className="w-4 h-4" />
                  Access Key
                </label>
                <input
                  type="password"
                  id="accessKey"
                  value={accessKeyInput}
                  onChange={(e) => setAccessKeyInput(e.target.value)}
                  placeholder="输入你的 Access Key"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Access Key 用于验证 API 请求，请从管理员处获取
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 p-4 border-t bg-gray-50 rounded-b-xl">
              <button
                onClick={() => setShowSettings(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleSaveAccessKey}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
