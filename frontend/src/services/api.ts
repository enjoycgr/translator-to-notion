/**
 * API service for the Translation Agent frontend.
 */

import type {
  ApiResponse,
  TranslateRequest,
  TranslateResponseData,
  ResumeResponseData,
  NotionSyncRequest,
  NotionSyncResponseData,
  HealthResponse,
  StreamChunk,
} from '@/types';

// API configuration
const API_BASE_URL = '/api';

// Access key storage key
const ACCESS_KEY_STORAGE_KEY = 'translation_agent_access_key';

/**
 * Get the stored access key.
 */
export function getAccessKey(): string {
  return localStorage.getItem(ACCESS_KEY_STORAGE_KEY) || '';
}

/**
 * Set the access key.
 */
export function setAccessKey(key: string): void {
  localStorage.setItem(ACCESS_KEY_STORAGE_KEY, key);
}

/**
 * Clear the access key.
 */
export function clearAccessKey(): void {
  localStorage.removeItem(ACCESS_KEY_STORAGE_KEY);
}

/**
 * Check if access key is set.
 */
export function hasAccessKey(): boolean {
  return Boolean(getAccessKey());
}

/**
 * Build headers for API requests.
 */
function buildHeaders(includeAuth: boolean = true): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (includeAuth) {
    const accessKey = getAccessKey();
    if (accessKey) {
      headers['X-Access-Key'] = accessKey;
    }
  }

  return headers;
}

/**
 * Handle API response.
 */
async function handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const data = await response.json();

  if (!response.ok) {
    return {
      success: false,
      error: data.error || {
        code: 'UNKNOWN_ERROR',
        message: `HTTP ${response.status}: ${response.statusText}`,
      },
    };
  }

  return data;
}

/**
 * Health check API.
 */
export async function healthCheck(): Promise<ApiResponse<HealthResponse>> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: 'GET',
    headers: buildHeaders(false),
  });

  return handleResponse<HealthResponse>(response);
}

/**
 * Synchronous translation API.
 */
export async function translate(
  request: TranslateRequest
): Promise<ApiResponse<TranslateResponseData>> {
  const response = await fetch(`${API_BASE_URL}/translate`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });

  return handleResponse<TranslateResponseData>(response);
}

/**
 * Streaming translation API.
 * Returns an async generator that yields stream chunks.
 */
export async function* translateStream(
  request: TranslateRequest
): AsyncGenerator<StreamChunk, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/translate/stream`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.message || 'Stream request failed');
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE 事件以双换行符分隔
      const events = buffer.split('\n\n');
      // 保留最后一个可能不完整的事件
      buffer = events.pop() || '';

      for (const event of events) {
        if (!event.trim()) continue;

        // 解析单个 SSE 事件的所有行
        const lines = event.split('\n');
        let data = '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            data = line.slice(6);
          }
        }

        // 只处理有数据的事件
        if (data.trim()) {
          try {
            const chunk: StreamChunk = JSON.parse(data);
            yield chunk;

            if (chunk.is_complete) {
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, 'Data:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Get translation progress / resume translation.
 */
export async function getTranslationProgress(
  taskId: string,
  resume: boolean = false
): Promise<ApiResponse<ResumeResponseData | TranslateResponseData>> {
  const url = `${API_BASE_URL}/translate/resume/${taskId}${resume ? '?resume=true' : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: buildHeaders(),
  });

  return handleResponse(response);
}

/**
 * Sync translation to Notion.
 */
export async function syncToNotion(
  request: NotionSyncRequest
): Promise<ApiResponse<NotionSyncResponseData>> {
  const response = await fetch(`${API_BASE_URL}/notion/sync`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(request),
  });

  return handleResponse<NotionSyncResponseData>(response);
}

/**
 * Test Notion connection.
 */
export async function testNotionConnection(): Promise<ApiResponse<{ message: string }>> {
  const response = await fetch(`${API_BASE_URL}/notion/test`, {
    method: 'GET',
    headers: buildHeaders(),
  });

  return handleResponse(response);
}
