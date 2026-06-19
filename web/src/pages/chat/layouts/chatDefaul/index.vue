<!-- 默认消息列表页 -->
<script setup lang="ts">
import ModelSelect from '@/components/ModelSelect/index.vue';
import WelecomeText from '@/components/WelecomeText/index.vue';
import { useRagTestStore } from '@/stores/modules/ragTest';
import { useSessionStore } from '@/stores/modules/session';
import { useUserStore } from '@/stores/modules/user';

const sessionStore = useSessionStore();
const userStore = useUserStore();
const ragTestStore = useRagTestStore();

const senderValue = ref('');

async function handleSend() {
  const content = senderValue.value.trim();
  if (!content)
    return;
  if (!userStore.token) {
    ElMessage.warning('请先登录后再开始对话');
    userStore.openLoginDialog();
    return;
  }
  localStorage.setItem('chatContent', content);
  await sessionStore.createSessionList({
    userId: userStore.userInfo?.userId || 0,
    sessionContent: content,
    sessionTitle: content.slice(0, 10),
    remark: content.slice(0, 10),
  });
}
</script>

<template>
  <div class="chat-defaul-wrap">
    <WelecomeText />
    <Sender
      v-model="senderValue"
      class="chat-defaul-sender"
      :auto-size="{
        maxRows: 9,
        minRows: 3,
      }"
      variant="updown"
      clearable
      allow-speech
      @submit="handleSend"
    >
      <template #prefix>
        <div class="flex-1 flex items-center gap-8px flex-none w-fit overflow-hidden">
          <ModelSelect />
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
</template>

<style scoped lang="scss">
.chat-defaul-wrap {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 800px;
  min-height: 450px;
  .chat-defaul-sender {
    width: 100%;
  }
  .rag-test-switch {
    flex: none;
  }
}
</style>
