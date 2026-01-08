import React, { useState } from 'react';
import type { Domain, InputMode } from '@/types';
import { DomainSelector } from './DomainSelector';
import { LoadingSpinner } from './LoadingSpinner';
import { FileText, Link, Send } from 'lucide-react';

interface TranslateFormProps {
  onSubmit: (data: {
    content?: string;
    url?: string;
    title?: string;
    domain: Domain;
    syncToNotion?: boolean;
  }) => void;
  isLoading: boolean;
  disabled?: boolean;
  /** Mode: 'stream' for SSE streaming, 'background' for background task */
  mode?: 'stream' | 'background';
}

export function TranslateForm({
  onSubmit,
  isLoading,
  disabled = false,
  mode = 'stream',
}: TranslateFormProps) {
  const [inputMode, setInputMode] = useState<InputMode>('text');
  const [content, setContent] = useState('');
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [domain, setDomain] = useState<Domain>('tech');
  const [syncToNotion, setSyncToNotion] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validate = (): boolean => {
    const newErrors: string[] = [];

    if (inputMode === 'text' && !content.trim()) {
      newErrors.push('请输入要翻译的内容');
    }

    if (inputMode === 'url') {
      if (!url.trim()) {
        newErrors.push('请输入要翻译的 URL');
      } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
        newErrors.push('URL 必须以 http:// 或 https:// 开头');
      }
    }

    setErrors(newErrors);
    return newErrors.length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    onSubmit({
      content: inputMode === 'text' ? content : undefined,
      url: inputMode === 'url' ? url : undefined,
      title: title || undefined,
      domain,
      syncToNotion,
    });
  };

  const isFormDisabled = isLoading || disabled;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Input Mode Toggle */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden">
        <button
          type="button"
          onClick={() => {
            setInputMode('text');
            setErrors([]);
          }}
          className={`
            flex-1 flex items-center justify-center gap-2 py-3 px-4 text-sm font-medium transition-colors
            ${
              inputMode === 'text'
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }
          `}
          disabled={isFormDisabled}
        >
          <FileText className="w-4 h-4" />
          文本输入
        </button>
        <button
          type="button"
          onClick={() => {
            setInputMode('url');
            setErrors([]);
          }}
          className={`
            flex-1 flex items-center justify-center gap-2 py-3 px-4 text-sm font-medium transition-colors
            ${
              inputMode === 'url'
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }
          `}
          disabled={isFormDisabled}
        >
          <Link className="w-4 h-4" />
          URL 抓取
        </button>
      </div>

      {/* Content Input */}
      {inputMode === 'text' ? (
        <div>
          <label
            htmlFor="content"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            待翻译内容
          </label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="在此粘贴需要翻译的英文内容..."
            rows={10}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
            disabled={isFormDisabled}
          />
          <p className="text-xs text-gray-500 mt-1">
            {content.length} 字符
          </p>
        </div>
      ) : (
        <div>
          <label
            htmlFor="url"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            文章 URL
          </label>
          <input
            type="url"
            id="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/article"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            disabled={isFormDisabled}
          />
          <p className="text-xs text-gray-500 mt-1">
            支持静态网页内容抓取（博客、新闻等）
          </p>
        </div>
      )}

      {/* Title Input */}
      <div>
        <label
          htmlFor="title"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          标题（可选）
        </label>
        <input
          type="text"
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="输入文章标题，便于后续同步到 Notion"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          disabled={isFormDisabled}
        />
      </div>

      {/* Domain Selector */}
      <DomainSelector
        value={domain}
        onChange={setDomain}
        disabled={isFormDisabled}
      />

      {/* Notion 同步复选框 - 仅在 stream 模式下显示 */}
      {mode === 'stream' && (
        <div className="flex items-center gap-3 py-2">
          <input
            type="checkbox"
            id="syncToNotion"
            checked={syncToNotion}
            onChange={(e) => setSyncToNotion(e.target.checked)}
            disabled={isFormDisabled}
            className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2 cursor-pointer"
          />
          <label
            htmlFor="syncToNotion"
            className="text-sm font-medium text-gray-700 cursor-pointer select-none"
          >
            翻译完成后自动同步到 Notion
          </label>
        </div>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <ul className="list-disc list-inside text-sm text-red-600">
            {errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isFormDisabled}
        className={`
          w-full flex items-center justify-center gap-2 py-4 px-6 rounded-lg font-medium text-white transition-all
          ${
            isFormDisabled
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-primary-600 hover:bg-primary-700 active:bg-primary-800'
          }
        `}
      >
        {isLoading ? (
          <>
            <LoadingSpinner size="sm" />
            {mode === 'background' ? '提交中...' : '翻译中...'}
          </>
        ) : (
          <>
            <Send className="w-5 h-5" />
            {mode === 'background' ? '提交任务' : '开始翻译'}
          </>
        )}
      </button>
    </form>
  );
}

export default TranslateForm;
