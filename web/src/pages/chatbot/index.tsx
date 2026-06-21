import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import { Bubble, Sender, XProvider } from '@ant-design/x';
import type {
  BubbleItemType,
  BubbleListProps,
} from '@ant-design/x/es/bubble/interface';
import XMarkdown from '@ant-design/x-markdown';
import { Avatar, Card, Select, Switch } from 'antd';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { listKnowledgeBases } from '@/services/knowledge';
import type { ChatItem } from './data';
import { sendChat } from './service';
import { useStyles } from './style';

const WELCOME_TEXT = '🤖 机器人调试 · 内部测试知识库检索与工具调用（无状态，不保存会话）';

const TypewriterTitle: React.FC = () => {
  const { styles } = useStyles();
  const [index, setIndex] = useState(0);
  const done = index >= WELCOME_TEXT.length;

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => {
        if (i >= WELCOME_TEXT.length) {
          clearInterval(timer);
          return i;
        }
        return i + 1;
      });
    }, 60);
    return () => clearInterval(timer);
  }, []);

  return (
    <>
      {WELCOME_TEXT.slice(0, index)}
      {!done && <span className={styles.cursor}>|</span>}
    </>
  );
};

/** AI 与用户气泡的角色样式：助手回答按 Markdown 渲染 */
const roleConfig: BubbleListProps['role'] = {
  user: {
    placement: 'end',
    avatar: <Avatar icon={<UserOutlined />} />,
  },
  ai: {
    placement: 'start',
    avatar: <Avatar style={{ background: '#f0f5ff' }} icon={<RobotOutlined />} />,
    contentRender: (content: string) => {
      if (!content) return undefined;
      return <XMarkdown>{content}</XMarkdown>;
    },
  },
};

const ChatbotPage: React.FC = () => {
  const { styles } = useStyles();
  const msgIdRef = useRef(0);
  const nextId = useCallback(() => `m-${++msgIdRef.current}`, []);

  const [inputValue, setInputValue] = useState('');
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [kbOptions, setKbOptions] = useState<{ label: string; value: number }[]>(
    [],
  );
  const [kbIds, setKbIds] = useState<number[]>([]);
  // 是否开启大模型：开启时正常调用模型回答；关闭时只看检索结果和 Prompt（ragTest=true）。
  const [useLlm, setUseLlm] = useState(true);

  // 加载知识库列表，供发送时按知识库过滤检索范围
  useEffect(() => {
    listKnowledgeBases()
      .then((res) => {
        setKbOptions(
          (res.data ?? []).map((kb) => ({ label: kb.name, value: kb.id })),
        );
      })
      .catch(() => {
        // 错误已由统一请求拦截器提示
      });
  }, []);

  /** 发送提问：乐观插入气泡 → 调用 /chat → 回填回答（不创建/复用会话） */
  const sendMessage = useCallback(
    async (content: string) => {
      const question = content.trim();
      if (!question || loading) return;

      setInputValue('');
      const userItem: ChatItem = { id: nextId(), role: 'user', content: question };
      const aiId = nextId();
      setChatItems((prev) => [
        ...prev,
        userItem,
        { id: aiId, role: 'ai', content: '', loading: true },
      ]);
      setLoading(true);

      try {
        const res = await sendChat({
          question,
          knowledgeBaseIds: kbIds.length > 0 ? kbIds : undefined,
          // 开启大模型 → 正常生成回答（ragTest=false）；关闭 → 仅返回检索+Prompt（ragTest=true）。
          ragTest: !useLlm,
        });
        const { answer, references } = res.data;
        setChatItems((prev) =>
          prev.map((it) =>
            it.id === aiId
              ? { ...it, content: answer, references, loading: false }
              : it,
          ),
        );
      } catch {
        // 失败：移除占位的助手气泡，错误提示由请求拦截器统一处理
        setChatItems((prev) => prev.filter((it) => it.id !== aiId));
      } finally {
        setLoading(false);
      }
    },
    [kbIds, loading, nextId, useLlm],
  );

  const bubbleItems = useMemo<BubbleItemType[]>(
    () =>
      chatItems.map((it) => {
        const item: BubbleItemType = {
          key: it.id,
          role: it.role,
          content: it.content,
          loading: it.loading,
        };
        if (it.role === 'ai' && it.references && it.references.length > 0) {
          item.footer = (
            <details className={styles.references}>
              <summary>引用 {it.references.length} 条</summary>
              {it.references.map((ref) => (
                <div key={`${it.id}-ref-${ref}`} className={styles.referenceItem}>
                  {ref}
                </div>
              ))}
            </details>
          );
        }
        return item;
      }),
    [chatItems, styles.references, styles.referenceItem],
  );

  const hasMessages = chatItems.length > 0;

  return (
    <PageContainer
      ghost
      childrenContentStyle={{
        paddingBlock: 0,
        height: 'calc(100vh - 160px)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <Card
        variant="borderless"
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        styles={{
          body: {
            flex: 1,
            padding: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        <XProvider>
          <div className={styles.main}>
            {hasMessages && (
              <div className={styles.messages}>
                <Bubble.List
                  items={bubbleItems}
                  role={roleConfig}
                  autoScroll
                  styles={{ root: { maxWidth: 940 } }}
                />
              </div>
            )}

            <div className={hasMessages ? styles.footer : styles.footerCenter}>
              {!hasMessages && (
                <div className={styles.welcomeTitle}>
                  <TypewriterTitle />
                </div>
              )}
              <div className={styles.senderArea}>
                <div className={styles.controls}>
                  <span>开启大模型</span>
                  <Switch
                    checked={useLlm}
                    onChange={setUseLlm}
                    checkedChildren="是"
                    unCheckedChildren="否"
                  />
                </div>
                <Select
                  mode="multiple"
                  allowClear
                  value={kbIds}
                  onChange={setKbIds}
                  options={kbOptions}
                  placeholder="选择知识库（留空则检索全部）"
                  maxTagCount="responsive"
                  style={{ width: '100%' }}
                />
                <Sender
                  value={inputValue}
                  onChange={setInputValue}
                  loading={loading}
                  onSubmit={sendMessage}
                  placeholder="输入消息，按 Enter 发送…（仅调试，不保存会话）"
                  autoSize={{ minRows: 3, maxRows: 8 }}
                  style={{ width: '100%' }}
                  styles={{ input: { paddingBlock: 0 } }}
                />
              </div>
            </div>
          </div>
        </XProvider>
      </Card>
    </PageContainer>
  );
};

export default ChatbotPage;
