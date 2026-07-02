/** 右下角悬浮客服挂件：悬浮按钮 + 开合对话窗 + 未读徽标 + 标题闪烁。 */

import { useEffect, useRef, useState } from 'react';
import { listConversations } from '../api/chat';
import { useChatStream } from '../hooks/useChatStream';
import { useVisitor } from '../hooks/useVisitor';
import { ChatWindow } from './ChatWindow';

const ACTIVE_KEY = 'aics_active_session';

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const { customer, ready, login, register, logout } = useVisitor();
  // 提到挂件层：关掉窗口也保留 SSE 连接与状态机，才能在窗口外接收坐席消息。
  const chat = useChatStream();

  const customerId = customer?.customerId;

  /** 身份就绪或切换（登录/注册/登出）时，拉取会话并恢复最近一条未结束会话。 */
  useEffect(() => {
    if (customerId == null) return;
    let cancelled = false;
    (async () => {
      try {
        const list = await listConversations();
        if (cancelled) return;
        const active = localStorage.getItem(ACTIVE_KEY);
        const preferred =
          (active
            ? list.find((item) => item.sessionId === active && (item.status !== 'closed' || item.rating == null))
            : undefined) ??
          list.find((item) => item.status !== 'closed');
        if (preferred) {
          await chat.loadSession(preferred.sessionId, preferred.status, preferred.rating);
        } else {
          chat.reset();
        }
      } catch {
        // 拉取失败时保持当前界面
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [customerId, chat.loadSession, chat.reset]);

  // 未读消息计数：窗口关闭时,新增的非客户消息(机器人/坐席)累计为未读。
  const [unreadCount, setUnreadCount] = useState(0);
  const prevLenRef = useRef(0);
  useEffect(() => {
    const len = chat.messages.length;
    const prev = prevLenRef.current;
    prevLenRef.current = len;
    if (open) {
      setUnreadCount(0);
      return;
    }
    // 批量替换（loadSession）或重置不计入未读；仅单条增量视为新消息。
    if (len - prev !== 1) return;
    const last = chat.messages[len - 1];
    if (!last || last.sender === 'customer') return;
    setUnreadCount((c) => c + 1);
  }, [chat.messages, open]);

  // 浏览器标签标题闪烁，提示坐席侧有未读。
  const hasUnread = unreadCount > 0;
  useEffect(() => {
    if (!hasUnread) return;
    const original = document.title;
    let flipped = false;
    const timer = setInterval(() => {
      flipped = !flipped;
      document.title = flipped ? `【新消息】${original}` : original;
    }, 1000);
    return () => {
      clearInterval(timer);
      document.title = original;
    };
  }, [hasUnread]);

  const badgeText = unreadCount > 99 ? '99+' : String(unreadCount);

  return (
    <div className="aics-root">
      {open &&
        (ready ? (
          <ChatWindow
            chat={chat}
            customer={customer}
            onClose={() => setOpen(false)}
            onLogin={login}
            onRegister={register}
            onLogout={logout}
          />
        ) : (
          <div className="aics-window aics-window-loading">正在接入客服…</div>
        ))}
      <button
        className={`aics-launcher${hasUnread && !open ? ' aics-launcher-alert' : ''}`}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label="在线客服"
      >
        {open ? '×' : '💬'}
        {!open && hasUnread && <span className="aics-launcher-badge">{badgeText}</span>}
      </button>
    </div>
  );
}
