import type { Domain } from '@/types';
import { DOMAINS } from '@/types';
import { BookOpen, Briefcase, Code } from 'lucide-react';

interface DomainSelectorProps {
  value: Domain;
  onChange: (domain: Domain) => void;
  disabled?: boolean;
}

const domainIcons: Record<Domain, React.ReactNode> = {
  tech: <Code className="w-5 h-5" />,
  business: <Briefcase className="w-5 h-5" />,
  academic: <BookOpen className="w-5 h-5" />,
};

export function DomainSelector({
  value,
  onChange,
  disabled = false,
}: DomainSelectorProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        翻译领域
      </label>
      <div className="grid grid-cols-3 gap-3">
        {DOMAINS.map((domain) => (
          <button
            key={domain.key}
            type="button"
            onClick={() => onChange(domain.key)}
            disabled={disabled}
            className={`
              relative flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all
              ${
                value === domain.key
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            <div
              className={`
              ${value === domain.key ? 'text-primary-600' : 'text-gray-400'}
            `}
            >
              {domainIcons[domain.key]}
            </div>
            <span className="font-medium text-sm">{domain.name}</span>
            {value === domain.key && (
              <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-primary-500" />
            )}
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500 mt-2">
        {DOMAINS.find((d) => d.key === value)?.description}
      </p>
    </div>
  );
}

export default DomainSelector;
