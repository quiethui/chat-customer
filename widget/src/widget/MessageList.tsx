/** 消息列表：区分客户/机器人/坐席气泡，机器人与坐席内容按 Markdown 渲染。 */

import Markdown from 'react-markdown';
import type { WidgetMessage } from '../types';

const SENDER_LABEL: Record<string, string> = {
  customer: '我',
  bot: '智能助手',
  agent: '人工客服',
};

export function MessageList({ messages }: { messages: WidgetMessage[] }) {
  return (
    <div className="aics-messages">
      {messages.map((message) => (
        <div key={message.id} className={`aics-msg aics-msg-${message.sender}`}>
          <div className="aics-msg-role">{SENDER_LABEL[message.sender] ?? message.sender}</div>
          <div className="aics-bubble">
            {message.sender === 'customer' ? (
              <span className="aics-plain">{message.content}</span>
            ) : (
              <div className="aics-markdown">
                <Markdown>{message.content}</Markdown>
                {message.streaming && <span className="aics-cursor">▍</span>}
              </div>
            )}
            {message.references && message.references.length > 0 && (
              <details className="aics-refs">
                <summary>参考 {message.references.length} 条</summary>
                {message.references.map((reference, index) => (
                  <div key={`${message.id}-ref-${index}`} className="aics-ref-item">
                    {reference}
                  </div>
                ))}
              </details>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
