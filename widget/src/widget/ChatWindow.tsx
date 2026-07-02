/** 对话窗：标题栏状态/身份 + 消息区 + 输入/转人工/结束评分；支持登录与历史会话切换。 */

import { useLayoutEffect, useRef, useState } from 'react';
import type { useChatStream } from '../hooks/useChatStream';
import type { Customer } from '../types';
import { AuthModal } from './AuthModal';
import { Composer } from './Composer';
import { ConversationList } from './ConversationList';
import { MessageList } from './MessageList';

const STATUS_TEXT: Record<string, string> = {
  bot: '智能助手在线',
  waiting: '正在转接人工…',
  serving: '人工客服服务中',
  closed: '会话已结束',
};

type ChatStream = ReturnType<typeof useChatStream>;

interface ChatWindowProps {
  chat: ChatStream;
  customer: Customer | null;
  onClose: () => void;
  onLogin: (username: string, password: string) => Promise<Customer>;
  onRegister: (username: string, password: string, nickname?: string) => Promise<Customer>;
  onLogout: () => Promise<void>;
}

export function ChatWindow({ chat, customer, onClose, onLogin, onRegister, onLogout }: ChatWindowProps) {
  const { messages, status, rating, hint, sending, hasSession, send, handoff, rate, loadSession, reset } = chat;
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [hover, setHover] = useState(0);
  const [view, setView] = useState<'chat' | 'list'>('chat');
  const [authOpen, setAuthOpen] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);

  /** 记录用户是否停留在底部：向上翻看历史时不再强制下拉。 */
  const handleBodyScroll = () => {
    const el = bodyRef.current;
    if (!el) return;
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  };

  /** 新消息或 SSE 流式增量到达时，若仍吸附底部则滚动到最新内容。 */
  useLayoutEffect(() => {
    if (!pinnedRef.current) return;
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, hint]);

  const handleRate = async (score: number) => {
    if (rating != null || ratingSubmitting) return;
    setRatingSubmitting(true);
    try {
      await rate(score);
    } catch {
      // 评分失败忽略
    } finally {
      setRatingSubmitting(false);
    }
  };

  const handleLogout = async () => {
    try {
      await onLogout();
      setView('chat');
    } catch {
      // 登出失败忽略，下次重试
    }
  };

  const loggedIn = !!customer && !customer.isAnonymous;
  const greeting = customer?.nickname ? `${customer.nickname}，您好！` : '您好！';
  // 人工模式（waiting/serving）下允许客户继续给坐席发消息；仅在机器人流式回答中禁用输入。
  const composerDisabled = sending;
  const composerPlaceholder =
    status === 'waiting'
      ? '正在转接人工，您可以继续留言…'
      : status === 'serving'
        ? '与人工客服对话中，请输入…'
        : '输入您的问题…';

  return (
    <div className="aics-window">
      <div className="aics-header">
        <div className="aics-header-title">
          <span className="aics-dot" data-status={status} />
          在线客服
          <span className="aics-status">{STATUS_TEXT[status] ?? status}</span>
        </div>
        <div className="aics-header-actions">
          {loggedIn ? (
            <>
              <span className="aics-user" title={customer?.username ?? undefined}>
                {customer?.nickname || customer?.username}
              </span>
              <button className="aics-text-btn" type="button" onClick={() => setView('list')}>
                历史
              </button>
              <button className="aics-text-btn" type="button" onClick={handleLogout}>
                登出
              </button>
            </>
          ) : (
            <button className="aics-text-btn" type="button" onClick={() => setAuthOpen(true)}>
              登录
            </button>
          )}
          <button className="aics-icon-btn" type="button" onClick={onClose} aria-label="收起">
            ×
          </button>
        </div>
      </div>

      {view === 'list' ? (
        <ConversationList
          onSelect={async (sessionId, sessionStatus, sessionRating) => {
            await loadSession(sessionId, sessionStatus, sessionRating);
            setView('chat');
          }}
          onBack={() => setView('chat')}
          onNew={() => {
            reset();
            setView('chat');
          }}
        />
      ) : (
        <>
          <div className="aics-body" ref={bodyRef} onScroll={handleBodyScroll}>
            {messages.length === 0 ? (
              <div className="aics-greeting">
                <div className="aics-greeting-emoji">🛎️</div>
                <p>{greeting}我是您的智能客服，订单、商品、售后都可以问我～</p>
              </div>
            ) : (
              <MessageList messages={messages} />
            )}
            {hint && <div className="aics-hint">{hint}</div>}
          </div>

          <div className="aics-footer">
            {status === 'closed' ? (
              <div className="aics-rating">
                {rating != null ? (
                  <div className="aics-rating-done">
                    感谢您的评价！
                    <button
                      className="aics-link"
                      type="button"
                      onClick={() => {
                        reset();
                      }}
                    >
                      重新咨询
                    </button>
                  </div>
                ) : (
                  <>
                    <span>为本次服务评分：</span>
                    <div className="aics-stars" onMouseLeave={() => setHover(0)}>
                      {[1, 2, 3, 4, 5].map((score) => (
                        <button
                          key={score}
                          type="button"
                          className={`aics-star ${score <= (hover || rating || 0) ? 'on' : ''}`}
                          disabled={ratingSubmitting}
                          onMouseEnter={() => setHover(score)}
                          onClick={() => handleRate(score)}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ) : (
              <>
                <Composer
                  disabled={composerDisabled}
                  placeholder={composerPlaceholder}
                  onSend={send}
                />
                {status === 'bot' && hasSession && (
                  <button className="aics-handoff" type="button" onClick={handoff}>
                    转人工客服
                  </button>
                )}
              </>
            )}
          </div>
        </>
      )}

      <AuthModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        onLogin={onLogin}
        onRegister={onRegister}
      />
    </div>
  );
}
