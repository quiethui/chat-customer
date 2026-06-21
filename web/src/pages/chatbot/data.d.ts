// src/pages/chatbot/data.d.ts

/** 侧边栏会话项（适配 @ant-design/x Conversations） */
export interface ConversationItem {
  key: string;
  label: string;
  group?: string;
  isDraft?: boolean;
}

/** 解析后的消息（用于区分用户/助手与思考内容） */
export type ParsedMessage =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string; thinkContent?: string };

/** 后端会话记录，对齐 ChatSessionResponse */
export interface ChatSession {
  id: string;
  userId: number;
  sessionTitle: string;
  sessionContent?: string | null;
  remark?: string | null;
  createTime?: string | null;
  updateTime?: string | null;
}

/** 后端消息记录，对齐 ChatMessageResponse */
export interface ChatMessage {
  id: number;
  sessionId: string;
  userId: number;
  role: 'user' | 'assistant' | string;
  content: string;
  modelName?: string | null;
  totalTokens?: number | null;
  references: string[];
  createTime?: string | null;
}

/** /chat 接口返回的回答数据，对齐 ChatResponse */
export interface ChatAnswer {
  answer: string;
  references: string[];
  sessionId?: string | null;
  prompt: string;
}

/** 前端渲染用的聊天气泡条目 */
export interface ChatItem {
  id: string;
  role: 'user' | 'ai';
  content: string;
  references?: string[];
  loading?: boolean;
}
