/** 历史会话列表视图：登录后可切换查看，点击某条恢复该会话。 */

import { useEffect, useState } from 'react';
import { listConversations } from '../api/chat';
import type { ConversationStatus, ConversationSummary } from '../types';

interface ConversationListProps {
  /** 点击某条会话，载入并切回对话视图。 */
  onSelect: (sessionId: string, status: ConversationStatus) => void;
  /** 返回对话视图。 */
  onBack: () => void;
  /** 开启新会话。 */
  onNew: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  bot: '智能助手',
  waiting: '等待人工',
  serving: '人工服务',
  closed: '已结束',
};

/** 将 ISO 时间格式化为 YYYY-MM-DD HH:mm，空值返回空串。 */
function formatTime(value?: string | null): string {
  if (!value) return '';
  return value.replace('T', ' ').slice(0, 16);
}

/** 历史会话列表组件。 */
export function ConversationList({ onSelect, onBack, onNew }: ConversationListProps) {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listConversations()
      .then((list) => {
        if (!cancelled) setItems(list);
      })
      .catch(() => {
        // 拉取失败时展示空列表
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="aics-conv">
      <div className="aics-conv-head">
        <button className="aics-text-btn" type="button" onClick={onBack}>
          ← 返回
        </button>
        <span>历史会话</span>
        <button className="aics-text-btn" type="button" onClick={onNew}>
          + 新会话
        </button>
      </div>
      <div className="aics-conv-body">
        {loading ? (
          <div className="aics-conv-empty">加载中…</div>
        ) : items.length === 0 ? (
          <div className="aics-conv-empty">暂无历史会话</div>
        ) : (
          items.map((item) => (
            <button
              key={item.sessionId}
              type="button"
              className="aics-conv-item"
              onClick={() => onSelect(item.sessionId, item.status)}
            >
              <div className="aics-conv-title">{item.sessionTitle || '未命名会话'}</div>
              <div className="aics-conv-meta">
                <span>{STATUS_LABEL[item.status] ?? item.status}</span>
                <span>{formatTime(item.lastMessageAt || item.updatedAt)}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
