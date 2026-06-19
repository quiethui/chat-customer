<!-- 每个回话对应的聊天内容 -->
<script setup lang="ts">
import type { BubbleProps } from 'vue-element-plus-x/types/Bubble';
import type { BubbleListInstance } from 'vue-element-plus-x/types/BubbleList';
import type { ThinkingStatus } from 'vue-element-plus-x/types/Thinking';
import { ElMessage } from 'element-plus';
import { Sender } from 'vue-element-plus-x';
import { useRoute } from 'vue-router';
import { askCustomer } from '@/api';
import ModelSelect from '@/components/ModelSelect/index.vue';
import { useChatStore } from '@/stores/modules/chat';
import { useRagTestStore } from '@/stores/modules/ragTest';
import { useUserStore } from '@/stores/modules/user';

type MessageItem = BubbleProps & {
  key: number;
  role: 'ai' | 'user' | 'system';
  avatar: string;
  thinkingStatus?: ThinkingStatus;
  thinlCollapse?: boolean;
  reasoning_content?: string;
};

const route = useRoute();
const chatStore = useChatStore();
const ragTestStore = useRagTestStore();
const userStore = useUserStore();

const avatar = computed(() => {
  const userInfo = userStore.userInfo;
  return userInfo?.avatar || 'https://picsum.photos/200';
});

const inputValue = ref('');
const bubbleItems = ref<MessageItem[]>([]);
const bubbleListRef = ref<BubbleListInstance | null>(null);
const isLoading = ref(false);
let activeController: AbortController | null = null;

watch(
  () => route.params?.id,
  async (_id_) => {
    if (_id_) {
      await chatStore.requestChatList(`${_id_}`);
      bubbleItems.value = (chatStore.chatMap[`${_id_}`] || []) as MessageItem[];

      setTimeout(() => {
        bubbleListRef.value?.scrollToBottom();
      }, 350);

      const v = localStorage.getItem('chatContent');
      if (v) {
        setTimeout(() => {
          startSSE(v);
        }, 350);

        localStorage.removeItem('chatContent');
      }
    }
  },
  { immediate: true, deep: true },
);

function persistCurrentChat() {
  const sessionId = String(route.params?.id || 'not_login');
  chatStore.setChatMap(
    sessionId,
    bubbleItems.value.map((item, index) => ({
      id: index,
      content: item.content as string,
      role: item.role === 'user' ? 'user' : 'assistant',
      sessionId,
    })),
  );
}

function handleError(err: any) {
  if (err?.name === 'AbortError') {
    ElMessage.warning('已停止生成');
    return;
  }
  ElMessage.error(err?.message || '请求失败');
  console.error('Fetch error:', err);
}

async function startSSE(chatContent: string) {
  const question = chatContent.trim();
  if (!question || isLoading.value)
    return;
  if (!userStore.token) {
    ElMessage.warning('请先登录后再发送消息');
    userStore.openLoginDialog();
    return;
  }

  activeController = new AbortController();
  isLoading.value = true;

  try {
    inputValue.value = '';
    addMessage(question, true);
    addMessage('', false);

    bubbleListRef.value?.scrollToBottom();

    const res = await askCustomer(question, String(route.params?.id || ''), activeController.signal, ragTestStore.enabled);
    const answerItem = bubbleItems.value[bubbleItems.value.length - 1];
    const references = res.data.references?.length
      ? `\n\n---\n参考片段：\n${res.data.references.map((item, index) => `${index + 1}. ${item}`).join('\n')}`
      : '';

    answerItem.content = res.data.ragTest && res.data.ragDebug
      ? formatRagDebugMarkdown(res.data.ragDebug)
      : `${res.data.answer}${references}`;
    answerItem.loading = false;
    answerItem.typing = false;
    answerItem.thinkingStatus = 'end';
    persistCurrentChat();
  }
  catch (err) {
    if (bubbleItems.value.length) {
      const answerItem = bubbleItems.value[bubbleItems.value.length - 1];
      answerItem.loading = false;
      answerItem.typing = false;
      answerItem.content = '请求失败，请稍后重试。';
    }
    handleError(err);
  }
  finally {
    isLoading.value = false;
    activeController = null;
    bubbleListRef.value?.scrollToBottom();
  }
}

function formatRagDebugMarkdown(debug: NonNullable<Awaited<ReturnType<typeof askCustomer>>['data']['ragDebug']>) {
  const lines = [
    '# RAG 测试结果',
    '',
    `- 耗时：${debug.elapsedMs} ms`,
    `- 检索候选数：${debug.searchLimit}`,
    `- 进入 Prompt 的 Chunk 数：${debug.promptContextCount}`,
    '',
    '## 命中 Chunks',
  ];

  for (const chunk of debug.chunks) {
    lines.push(
      '',
      `### #${chunk.rank}  score=${chunk.score}`,
      `- 文件：${chunk.fileName || '-'}`,
      `- 知识库：${chunk.knowledgeBaseName || chunk.knowledgeBaseId || '-'}`,
      `- File ID：${chunk.fileId || '-'}`,
      `- Vector ID：${chunk.vectorId || '-'}`,
      `- 进入 Prompt：${chunk.usedInPrompt ? '是' : '否'}`,
      '',
      '```text',
      chunk.content || '',
      '```',
    );
  }

  lines.push('', '## 最终 Prompt', '', '```text', debug.finalPrompt || '', '```');
  return lines.join('\n');
}

async function cancelSSE() {
  activeController?.abort();
  isLoading.value = false;
  if (bubbleItems.value.length) {
    bubbleItems.value[bubbleItems.value.length - 1].typing = false;
    bubbleItems.value[bubbleItems.value.length - 1].loading = false;
  }
}

function addMessage(message: string, isUser: boolean) {
  const i = bubbleItems.value.length;
  const obj: MessageItem = {
    key: i,
    avatar: isUser
      ? avatar.value
      : 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
    avatarSize: '32px',
    role: isUser ? 'user' : 'system',
    placement: isUser ? 'end' : 'start',
    isMarkdown: !isUser,
    loading: !isUser,
    content: message || '',
    reasoning_content: '',
    thinkingStatus: 'start',
    thinlCollapse: false,
    noStyle: !isUser,
  };
  bubbleItems.value.push(obj);
  persistCurrentChat();
}

function handleChange(payload: { value: boolean; status: ThinkingStatus }) {
  console.log('value', payload.value, 'status', payload.status);
}
</script>

<template>
  <div class="chat-with-id-container">
    <div class="chat-warp">
      <BubbleList ref="bubbleListRef" :list="bubbleItems" max-height="calc(100vh - 240px)">
        <template #header="{ item }">
          <Thinking
            v-if="item.reasoning_content" v-model="item.thinlCollapse" :content="item.reasoning_content"
            :status="item.thinkingStatus" class="thinking-chain-warp" @change="handleChange"
          />
        </template>

        <template #content="{ item }">
          <XMarkdown v-if="item.content && item.role === 'system'" :markdown="item.content" class="markdown-body" :themes="{ light: 'github-light', dark: 'github-dark' }" default-theme-mode="dark" />
          <div v-if="item.content && item.role === 'user'" class="user-content">
            {{ item.content }}
          </div>
        </template>
      </BubbleList>

      <Sender
        v-model="inputValue" class="chat-defaul-sender" :auto-size="{
          maxRows: 6,
          minRows: 2,
        }" variant="updown" clearable allow-speech :loading="isLoading" @submit="startSSE" @cancel="cancelSSE"
      >
        <template #prefix>
          <div class="flex-1 flex items-center gap-8px flex-none w-fit overflow-hidden">
            <ModelSelect />
            <el-switch
              v-model="ragTestStore.enabled"
              size="small"
              active-text="RAG测试"
              inline-prompt
              class="rag-test-switch"
            />
          </div>
        </template>
      </Sender>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-with-id-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 800px;
  height: 100%;
  .chat-warp {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 100%;
    height: calc(100vh - 60px);
    .thinking-chain-warp {
      margin-bottom: 12px;
    }
  }
  :deep() {
    .el-bubble-list {
      padding-top: 24px;
    }
    .el-bubble {
      padding: 0 12px;
      padding-bottom: 24px;
    }
    .el-typewriter {
      overflow: hidden;
      border-radius: 12px;
    }
    .user-content {
      white-space: pre-wrap;
    }
    .markdown-body {
      background-color: transparent;
    }
    .markdown-elxLanguage-header-div {
      top: -25px !important;
    }

    .elx-xmarkdown-container {
      padding: 8px 4px;
    }
  }
  .chat-defaul-sender {
    width: 100%;
    margin-bottom: 22px;
  }
  .rag-test-switch {
    flex: none;
  }
}
</style>
