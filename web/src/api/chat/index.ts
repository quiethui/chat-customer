import type { ChatMessageVo, GetChatListParams, SendDTO } from './types';
import { useUserStore } from '@/stores';

export interface FastApiResponse<T> {
  success: boolean;
  code?: number;
  message: string;
  msg?: string;
  data: T;
}

export interface CustomerChatResponse {
  answer: string;
  references: string[];
  sessionId: string;
  prompt: string;
  ragTest?: boolean;
  ragDebug?: RagDebugResponse | null;
}

export interface RagDebugChunk {
  rank: number;
  score: number;
  content: string;
  fileName?: string | null;
  fileId?: string | null;
  knowledgeBaseId?: string | null;
  knowledgeBaseName?: string | null;
  vectorId?: string | null;
  documentId?: string | null;
  usedInPrompt: boolean;
}

export interface RagDebugResponse {
  elapsedMs: number;
  searchLimit: number;
  promptContextCount: number;
  finalPrompt: string;
  chunks: RagDebugChunk[];
}

function getApiBaseUrl() {
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

function buildHeaders(headers?: HeadersInit) {
  const userStore = useUserStore();
  const mergedHeaders = new Headers(headers);
  if (userStore.token) {
    mergedHeaders.set('Authorization', `Bearer ${userStore.token}`);
  }
  return mergedHeaders;
}

async function requestJson<T>(path: string, init?: RequestInit) {
  const userStore = useUserStore();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: buildHeaders(init?.headers),
  });
  const result = (await response.json()) as FastApiResponse<T>;

  if (!response.ok || !result.success) {
    if (response.status === 401) {
      userStore.logout();
      userStore.openLoginDialog();
    }
    throw new Error(result.message || result.msg || '请求失败');
  }

  return result;
}

export async function askCustomer(question: string, sessionId?: string, signal?: AbortSignal, ragTest = false) {
  return requestJson<CustomerChatResponse>('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, sessionId, ragTest }),
    signal,
  });
}

export function send(data: SendDTO) {
  const question = [...data.messages].reverse().find(message => message.role === 'user')?.content || '';
  return askCustomer(question, data.sessionId);
}

export function addChat(data: ChatMessageVo) {
  return Promise.resolve({ data });
}

export function getChatList(params: GetChatListParams) {
  const query = new URLSearchParams();
  if (params.sessionId) {
    query.set('sessionId', String(params.sessionId));
  }
  return requestJson<ChatMessageVo[]>(`/system/message/list?${query.toString()}`);
}
