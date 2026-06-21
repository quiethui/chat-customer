/** 聊天流编排：机器人 SSE 流式问答 + 人工模式下接收坐席推送。 */

import { useCallback, useRef, useState } from 'react';
import {
  chatStreamUrl,
  conversationEventsUrl,
  fetchHistory,
  rateConversation,
  readSSE,
  requestHandoff,
  sendCustomerMessage,
} from '../api/chat';
import type { ConversationStatus, SenderType, WidgetMessage } from '../types';

let messageSeq = 0;
const nextId = (): string => `m${++messageSeq}`;

/** localStorage 中记录当前活跃会话 ID 的键，供复访快速恢复。 */
const ACTIVE_KEY = 'aics_active_session';

/** 把历史消息的 senderType 收敛到挂件渲染用的发送方。 */
const toSender = (senderType: string): SenderType =>
  senderType === 'customer' || senderType === 'agent' ? senderType : 'bot';

interface ChatStream {
  messages: WidgetMessage[];
  status: ConversationStatus;
  hint: string;
  sending: boolean;
  hasSession: boolean;
  send: (text: string) => Promise<void>;
  handoff: () => Promise<void>;
  rate: (score: number, comment?: string) => Promise<void>;
  loadSession: (sessionId: string, sessionStatus: ConversationStatus) => Promise<void>;
  reset: () => void;
}

/** 提供挂件聊天所需的状态与动作。 */
export function useChatStream(): ChatStream {
  const [messages, setMessages] = useState<WidgetMessage[]>([]);
  const [status, setStatus] = useState<ConversationStatus>('bot');
  const [hint, setHint] = useState('');
  const [sending, setSending] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const sessionIdRef = useRef<string>('');
  const eventsAbortRef = useRef<AbortController | null>(null);

  const rememberSession = useCallback((sessionId?: string) => {
    if (sessionId && sessionId !== sessionIdRef.current) {
      sessionIdRef.current = sessionId;
      setHasSession(true);
      localStorage.setItem(ACTIVE_KEY, sessionId);
    }
  }, []);

  /** 订阅坐席消息推送（人工模式）。 */
  const subscribeAgent = useCallback((sessionId: string) => {
    eventsAbortRef.current?.abort();
    const controller = new AbortController();
    eventsAbortRef.current = controller;
    (async () => {
      try {
        for await (const event of readSSE(conversationEventsUrl(sessionId), controller.signal)) {
          if (event.type === 'agent_message') {
            setMessages((prev) => [...prev, { id: nextId(), sender: 'agent', content: event.text ?? '' }]);
          } else if (event.type === 'status' && event.status) {
            setStatus(event.status as ConversationStatus);
            if (event.message) setHint(event.message);
          }
        }
      } catch {
        // 连接中断（含主动 abort）时忽略
      }
    })();
  }, []);

  /** 人工模式（waiting/serving）下把消息发给坐席，并乐观渲染。 */
  const sendToAgent = useCallback(async (text: string) => {
    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    setMessages((prev) => [...prev, { id: nextId(), sender: 'customer', content: text }]);
    try {
      await sendCustomerMessage(sessionId, text);
    } catch {
      setHint('消息发送失败，请稍后再试');
    }
  }, []);

  /** 发送一条消息：bot 模式走机器人 SSE 流，人工模式发给坐席。 */
  const send = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question || sending) return;
      if (status === 'waiting' || status === 'serving') {
        await sendToAgent(question);
        return;
      }
      setSending(true);
      setMessages((prev) => [...prev, { id: nextId(), sender: 'customer', content: question }]);
      const botId = nextId();
      setMessages((prev) => [...prev, { id: botId, sender: 'bot', content: '', streaming: true }]);
      try {
        for await (const event of readSSE(chatStreamUrl(question, sessionIdRef.current || undefined))) {
          if (event.type === 'status') {
            setHint(event.message ?? '');
            rememberSession(event.sessionId);
          } else if (event.type === 'delta') {
            setMessages((prev) =>
              prev.map((item) => (item.id === botId ? { ...item, content: item.content + (event.text ?? '') } : item)),
            );
          } else if (event.type === 'done') {
            rememberSession(event.sessionId);
            setMessages((prev) =>
              prev.map((item) =>
                item.id === botId ? { ...item, streaming: false, references: event.references } : item,
              ),
            );
            setHint('');
          }
        }
      } catch {
        setMessages((prev) =>
          prev.map((item) =>
            item.id === botId
              ? { ...item, streaming: false, content: item.content || '抱歉，网络开小差了，请稍后再试。' }
              : item,
          ),
        );
        setHint('');
      } finally {
        setSending(false);
      }
    },
    [sending, status, sendToAgent, rememberSession],
  );

  /** 请求转人工，并开始订阅坐席推送。 */
  const handoff = useCallback(async () => {
    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    try {
      await requestHandoff(sessionId);
      setStatus('waiting');
      setHint('正在为您转接人工客服…');
      subscribeAgent(sessionId);
    } catch {
      setHint('转人工失败，请稍后再试');
    }
  }, [subscribeAgent]);

  /** 提交满意度评分。 */
  const rate = useCallback(async (score: number, comment?: string) => {
    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    await rateConversation(sessionId, score, comment);
  }, []);

  /** 载入某个会话的历史消息并设为当前会话（复访恢复 / 历史列表点击）。 */
  const loadSession = useCallback(
    async (sessionId: string, sessionStatus: ConversationStatus) => {
      eventsAbortRef.current?.abort();
      eventsAbortRef.current = null;
      try {
        const history = await fetchHistory(sessionId);
        setMessages(history.map((item) => ({ id: nextId(), sender: toSender(item.senderType), content: item.content })));
      } catch {
        setMessages([]);
      }
      sessionIdRef.current = sessionId;
      setHasSession(true);
      setStatus(sessionStatus);
      setHint('');
      localStorage.setItem(ACTIVE_KEY, sessionId);
      // 人工模式恢复时继续订阅坐席推送。
      if (sessionStatus === 'waiting' || sessionStatus === 'serving') subscribeAgent(sessionId);
    },
    [subscribeAgent],
  );

  /** 重置会话（结束后重新咨询 / 新会话）。 */
  const reset = useCallback(() => {
    eventsAbortRef.current?.abort();
    eventsAbortRef.current = null;
    sessionIdRef.current = '';
    setHasSession(false);
    setMessages([]);
    setStatus('bot');
    setHint('');
    localStorage.removeItem(ACTIVE_KEY);
  }, []);

  return { messages, status, hint, sending, hasSession, send, handoff, rate, loadSession, reset };
}
