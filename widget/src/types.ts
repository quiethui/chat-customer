/** 挂件共享类型定义。 */

/** 客户信息，对齐后端 CustomerResponse。 */
export interface Customer {
  customerId: number;
  customerNo: string;
  username?: string | null;
  nickname?: string | null;
  avatar?: string | null;
  isAnonymous: boolean;
  source: string;
  lastLoginAt?: string | null;
}

/** 消息发送方。 */
export type SenderType = 'customer' | 'bot' | 'agent';

/** 会话服务状态。 */
export type ConversationStatus = 'bot' | 'waiting' | 'serving' | 'closed';

/** 挂件渲染用的聊天消息。 */
export interface WidgetMessage {
  id: string;
  sender: SenderType;
  content: string;
  streaming?: boolean;
  references?: string[];
}

/** 「我的会话」列表项，对齐后端 CustomerConversationItem。 */
export interface ConversationSummary {
  sessionId: string;
  sessionTitle: string;
  status: ConversationStatus;
  mode: string;
  rating?: number | null;
  lastMessageAt?: string | null;
  updatedAt?: string | null;
  createdAt?: string | null;
}

