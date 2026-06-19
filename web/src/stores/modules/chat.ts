import type { ChatMessageVo } from '@/api/chat/types';
import { defineStore } from 'pinia';
import { getChatList } from '@/api/chat';
import { useUserStore } from './user';

export const useChatStore = defineStore(
  'chat',
  () => {
    const userStore = useUserStore();

    const avatar = computed(() => {
      const userInfo = userStore.userInfo;
      return userInfo?.avatar || 'https://picsum.photos/200';
    });

    const isDeepThinking = ref<boolean>(false);

    const setDeepThinking = (value: boolean) => {
      isDeepThinking.value = value;
    };

    const chatMap = ref<Record<string, ChatMessageVo[]>>({});

    const setChatMap = (id: string, data: ChatMessageVo[]) => {
      chatMap.value[id] = data?.map((item: ChatMessageVo) => {
        const isUser = item.role === 'user';
        const thinkContent = extractThkContent(item.content as string);
        return {
          ...item,
          role: isUser ? 'user' : 'system',
          key: item.id,
          placement: isUser ? 'end' : 'start',
          isMarkdown: !isUser,
          avatar: isUser
            ? avatar.value
            : 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
          avatarSize: '32px',
          typing: false,
          reasoning_content: thinkContent,
          thinkingStatus: 'end',
          content: extractThkContentAfter(item.content as string),
          thinlCollapse: false,
        };
      });
    };

    const requestChatList = async (sessionId: string) => {
      if (!userStore.token) {
        chatMap.value[sessionId] = [];
        return;
      }
      const res = await getChatList({ sessionId });
      setChatMap(sessionId, res.data || []);
    };

    function extractThkContent(content: string) {
      const regex = /<think>(.*?)<\/think>/s;
      const matchResult = content.match(regex);
      return matchResult?.[1] ?? '';
    }

    function extractThkContentAfter(content: string) {
      if (!content.includes('</think>')) {
        return content;
      }
      const regex = /<\/think>(.*)/s;
      const matchResult = content.match(regex);
      return matchResult?.[1] ?? '';
    }

    return {
      chatMap,
      setChatMap,
      requestChatList,
      isDeepThinking,
      setDeepThinking,
    };
  },
  {
    persist: true,
  },
);
