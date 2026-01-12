/**
 * Type definitions for the Translation Agent frontend.
 */

// Domain types
export type Domain = 'tech' | 'business' | 'academic';

export interface DomainInfo {
  key: Domain;
  name: string;
  description: string;
}

export const DOMAINS: DomainInfo[] = [
  {
    key: 'tech',
    name: '技术/编程',
    description: '适用于技术文档、编程教程、API文档等',
  },
  {
    key: 'business',
    name: '商务/金融',
    description: '适用于商业报告、金融分析、商务邮件等',
  },
  {
    key: 'academic',
    name: '学术研究',
    description: '适用于学术论文、研究报告、学术文献等',
  },
];

// Task status types
export type TaskStatus = 'pending' | 'preparing' | 'in_progress' | 'completed' | 'failed';

// API Request types
export interface TranslateRequest {
  content?: string;
  url?: string;
  title?: string;
  domain: Domain;
  sync_to_notion?: boolean;
}

export interface NotionSyncRequest {
  task_id: string;
  title?: string;
}

// Background task request
export interface BackgroundTaskRequest {
  content?: string;
  url?: string;
  title?: string;
  source_url?: string;
  domain: Domain;
  source_lang?: string;
  target_lang?: string;
  sync_to_notion?: boolean;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface TranslateResponseData {
  task_id: string;
  original_content: string;
  translated_content: string;
  title?: string;
  source_url?: string;
  domain?: string;
  notion_page_url?: string;
  cost_usd: number;
}

export interface ResumeResponseData {
  task_id: string;
  status: TaskStatus;
  progress: number;
  partial_result?: string;
  original_content?: string;
  error?: string;
}

export interface NotionSyncResponseData {
  notion_page_url: string;
  page_id?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: {
    translation: string;
    notion: string;
  };
  config: {
    model: string;
    max_chunk_tokens: number;
    cache_ttl_minutes: number;
  };
}

// Stream chunk type
export interface StreamChunk {
  text: string;
  is_complete: boolean;
  task_id?: string;
  input_tokens?: number;
  output_tokens?: number;
  // Notion sync result (from notion_synced event)
  success?: boolean;
  notion_page_url?: string;
  page_id?: string;
  error?: string;
}

// Application state types
export interface TranslationState {
  isLoading: boolean;
  isStreaming: boolean;
  taskId?: string;
  originalContent?: string;
  translatedContent: string;
  title?: string;
  sourceUrl?: string;
  domain?: Domain;
  cost?: number;
  error?: string;
  progress?: number;
}

export interface NotionState {
  isSyncing: boolean;
  pageUrl?: string;
  error?: string;
}

// Input mode type
export type InputMode = 'text' | 'url';

// ============================================================
// Background Task Types (for task management)
// ============================================================

/**
 * Task list item (lightweight, for listing)
 */
export interface TaskListItem {
  task_id: string;
  title: string;
  status: TaskStatus;
  progress: number;
  domain: string;
  created_at: string;
}

/**
 * Task list response with pagination
 */
export interface TaskListResponse {
  tasks: TaskListItem[];
  total: number;
  has_more: boolean;
}

/**
 * Task detail (full information)
 */
export interface TaskDetail extends TaskListItem {
  original_content: string;
  source_url?: string;
  updated_at: string;
  total_chunks: number;
  completed_chunks: number;
  total_input_tokens: number;
  total_output_tokens: number;
  result?: string;           // only for completed status
  partial_result?: string;   // for in_progress status
  error_message?: string;    // only for failed status
  status_message?: string;   // for preparing status
  completed_at?: string;
}

/**
 * Background task submission response
 */
export interface BackgroundTaskResponse {
  task_id: string;
  status: TaskStatus;
  created_at: string;
}

/**
 * Task stats response
 */
export interface TaskStatsResponse {
  total_tasks: number;
  by_status: Record<TaskStatus, number>;
  queue_size: number;
}
