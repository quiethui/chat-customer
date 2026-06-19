import type { ChatSessionVo, CreateSessionDTO } from '@/api/session/types';
import { ChatLineRound } from '@element-plus/icons-vue';
import { defineStore } from 'pinia';
import { markRaw } from 'vue';
import { useRouter } from 'vue-router';
import { create_session, delete_session, get_session_list, update_session } from '@/api/session';
import { useUserStore } from './user';

export const useSessionStore = defineStore(
  'session',
  () => {
    const router = useRouter();
    const userStore = useUserStore();

    const currentSession = ref<ChatSessionVo | null>(null);
    const setCurrentSession = (session: ChatSessionVo | null) => {
      currentSession.value = session;
    };

    const sessionList = ref<ChatSessionVo[]>([]);
    const currentPage = ref(1);
    const pageSize = ref(25);
    const hasMore = ref(false);
    const isLoading = ref(false);
    const isLoadingMore = ref(false);

    const createSessionBtn = async () => {
      setCurrentSession(null);
      router.replace({ name: 'chat' });
    };

    const requestSessionList = async (page: number = currentPage.value, force: boolean = false) => {
      if (!userStore.token) {
        sessionList.value = [];
        hasMore.value = false;
        return;
      }
      if (isLoading.value && !force)
        return;
      isLoading.value = true;
      try {
        const res = await get_session_list({ pageNum: page, pageSize: pageSize.value, userId: userStore.userInfo?.userId || 0 });
        const list = (res.data || []) as ChatSessionVo[];
        sessionList.value = processSessions(page === 1 ? list : [...sessionList.value, ...list]);
        currentPage.value = page;
        hasMore.value = list.length >= pageSize.value;
      }
      finally {
        isLoading.value = false;
      }
    };

    const createSessionList = async (data: Omit<CreateSessionDTO, 'id'>) => {
      if (!userStore.token) {
        userStore.openLoginDialog();
        return;
      }
      const res = await create_session(data as CreateSessionDTO);
      const session = processSessions([res.data as ChatSessionVo])[0];
      sessionList.value = processSessions([
        session,
        ...sessionList.value.filter(item => item.id !== session.id),
      ]);
      setCurrentSession(session);

      router.replace({
        name: 'chatWithId',
        params: { id: session.id },
      });
    };

    const loadMoreSessions = async () => {
      if (!hasMore.value || isLoadingMore.value)
        return;
      isLoadingMore.value = true;
      try {
        await requestSessionList(currentPage.value + 1, true);
      }
      finally {
        isLoadingMore.value = false;
      }
    };

    const updateSession = async (item: ChatSessionVo) => {
      if (!item.id)
        return;
      const res = await update_session(item);
      const updated = processSessions([res.data as ChatSessionVo])[0];
      sessionList.value = processSessions(
        sessionList.value.map(session => session.id === updated.id ? { ...session, ...updated } : session),
      );
      if (currentSession.value?.id === updated.id) {
        setCurrentSession({ ...currentSession.value, ...updated });
      }
    };

    const deleteSessions = async (ids: string[]) => {
      await delete_session(ids);
      sessionList.value = sessionList.value.filter(session => !ids.includes(session.id!));
      if (currentSession.value?.id && ids.includes(currentSession.value.id)) {
        setCurrentSession(null);
      }
    };

    function processSessions(sessions: ChatSessionVo[]) {
      const currentDate = new Date();

      return sessions.map((session) => {
        const createDate = session.createTime ? new Date(session.createTime) : currentDate;
        const diffDays = Math.floor(
          (currentDate.getTime() - createDate.getTime()) / (1000 * 60 * 60 * 24),
        );

        let group: string;
        if (diffDays < 7) {
          group = '7 天内';
        }
        else if (diffDays < 30) {
          group = '30 天内';
        }
        else {
          const year = createDate.getFullYear();
          const month = String(createDate.getMonth() + 1).padStart(2, '0');
          group = `${year}-${month}`;
        }

        return {
          ...session,
          group,
          prefixIcon: markRaw(ChatLineRound),
        };
      });
    }

    return {
      currentSession,
      setCurrentSession,
      sessionList,
      currentPage,
      pageSize,
      hasMore,
      isLoading,
      isLoadingMore,
      createSessionBtn,
      createSessionList,
      requestSessionList,
      loadMoreSessions,
      updateSession,
      deleteSessions,
    };
  },
  {
    persist: true,
  },
);
