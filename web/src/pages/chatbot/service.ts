// src/pages/chatbot/service.ts
import { request } from '@umijs/max';
import type { ChatAnswer } from './data';

/** 发送提问 POST /chat（非流式，返回完整回答；机器人调试用，不保存前端会话） */
export async function sendChat(body: {
  question: string;
  sessionId?: string;
  knowledgeBaseIds?: number[];
  /** 是否开启 RAG 测试模式：true 时后端只返回检索结果和 Prompt、不调用大模型。 */
  ragTest?: boolean;
}) {
  return request<{ data: ChatAnswer }>('/chat', {
    method: 'POST',
    data: body,
  });
}
