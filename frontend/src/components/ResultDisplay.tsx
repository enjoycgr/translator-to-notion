import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface ResultDisplayProps {
  originalContent?: string;
  translatedContent: string;
  title?: string;
  sourceUrl?: string;
  domain?: string;
  cost?: number;
  isStreaming?: boolean;
}

export function ResultDisplay({
  // originalContent 保留在 props 定义中以保持 API 兼容性，但当前未使用
  translatedContent,
  title,
  sourceUrl,
  domain,
  cost,
  isStreaming = false,
}: ResultDisplayProps) {
  const [copied, setCopied] = useState(false);

  const domainNames: Record<string, string> = {
    tech: '技术/编程',
    business: '商务/金融',
    academic: '学术研究',
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(translatedContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Parse bilingual content for better display
  const formattedContent = useMemo(() => {
    // The content is already in markdown format with > for original
    return translatedContent;
  }, [translatedContent]);

  if (!translatedContent) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">
              {title || '翻译结果'}
            </h2>
            <div className="flex items-center gap-4 mt-1 text-primary-100 text-sm">
              {domain && (
                <span>领域: {domainNames[domain] || domain}</span>
              )}
              {cost !== undefined && (
                <span>费用: ${cost.toFixed(4)}</span>
              )}
            </div>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                已复制
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                复制译文
              </>
            )}
          </button>
        </div>
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-2 text-primary-100 hover:text-white text-sm transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            查看原文
          </a>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        <div className={`prose prose-gray max-w-none bilingual-content ${isStreaming ? 'stream-text' : ''}`}>
          <ReactMarkdown>{formattedContent}</ReactMarkdown>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-100 px-6 py-3 bg-gray-50">
        <p className="text-xs text-gray-500">
          💡 原文以引用格式显示，译文紧跟其后
        </p>
      </div>
    </div>
  );
}

export default ResultDisplay;
