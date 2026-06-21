/** 聊天与会话接口：SSE 流式问答、转人工、评分、历史、人工消息订阅。 */

import type { ConversationSummary } from '../types';
import { apiFetch, apiUrl, authHeaders } from './client';

/** SSE 事件（机器人流 + 人工推送共用的宽松结构）。 */
export interface StreamEvent {
  type: string;
  message?: string;
  text?: string;
  references?: string[];
  sessionId?: string;
  status?: string;
}

/**
 * 通用 SSE 读取：用 fetch + ReadableStream 逐帧解析 `data:` 行。
 * 之所以不用 EventSource，是因为需要在请求头携带 customer Bearer token。
 */
export async function* readSSE(url: string, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
  const response = await fetch(url, {
    headers: { Accept: 'text/event-stream', ...authHeaders() },
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`流式请求失败 (${response.status})`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let separator = buffer.indexOf('\n\n');
    while (separator >= 0) {
      const frame = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      for (const line of frame.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice(5).trim();
        if (!payload) continue;
        try {
          yield JSON.parse(payload) as StreamEvent;
        } catch {
          // 忽略无法解析的帧
        }
      }
      separator = buffer.indexOf('\n\n');
    }
  }
}

/** 机器人流式问答地址。 */
export function chatStreamUrl(question: string, sessionId?: string): string {
  const params = new URLSearchParams({ question });
  if (sessionId) params.set('sessionId', sessionId);
  return apiUrl(`/customer/chat/stream?${params.toString()}`);
}

/** 会话事件订阅地址（接收坐席消息与状态变更）。 */
export function conversationEventsUrl(sessionId: string): string {
  return apiUrl(`/customer/conversations/${sessionId}/events`);
}

/** 请求转人工。 */
export async function requestHandoff(sessionId: string): Promise<{ sessionId: string; status: string }> {
  return apiFetch(`/customer/conversations/${sessionId}/handoff`, { method: 'POST' });
}

/** 客户在人工会话中给坐席发送消息。 */
export async function sendCustomerMessage(
  sessionId: string,
  content: string,
): Promise<{ id: number; senderType: string; content: string }> {
  return apiFetch(`/customer/conversations/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

/** 提交满意度评分。 */
export async function rateConversation(
  sessionId: string,
  rating: number,
  comment?: string,
): Promise<{ sessionId: string; rating: number }> {
  return apiFetch(`/customer/conversations/${sessionId}/rating`, {
    method: 'POST',
    body: JSON.stringify({ rating, comment }),
  });
}

/** 会话历史消息（复访拉取）。 */
export interface HistoryMessage {
  id: number;
  role: string;
  senderType: string;
  agentId?: number | null;
  content: string;
  createdAt?: string | null;
}

/** 拉取会话历史消息。 */
export async function fetchHistory(sessionId: string): Promise<HistoryMessage[]> {
  return apiFetch<HistoryMessage[]>(`/customer/conversations/${sessionId}/messages`, { method: 'GET' });
}

/** 列出当前客户的会话（倒序），供复访恢复与历史会话列表。 */
export async function listConversations(): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>('/customer/conversations', { method: 'GET' });
}
