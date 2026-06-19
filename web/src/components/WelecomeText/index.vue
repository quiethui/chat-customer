<!-- 欢迎提示词 -->
<script setup lang="ts">
import { Typewriter } from 'vue-element-plus-x';
import { useTimeGreeting } from '@/hooks/useTimeGreeting';
import { useUserStore } from '@/stores';

const greeting = useTimeGreeting();
const userStore = useUserStore();

const username = computed(() => userStore.userInfo?.username ?? '我是 Element Plus X');

// 首页示例问题，提示用户可以直接在聊天框里查询当前登录用户的订单。
const exampleQuestions = ['查询我的最近订单', '订单 OD202605280001 发货了吗？', '我的订单金额是多少？'];
</script>

<template>
  <div
    class="welcome-text w-full flex flex-wrap items-center justify-center text-center text-lg font-semibold mb-32px mt-12px font-size-32px line-height-32px"
  >
    <Typewriter
      :content="`${greeting}好，${username}`"
      :typing="{
        step: 2,
        interval: 45,
      }"
      :is-fog="{
        bgColor: '#fff',
      }"
    />
    <div class="w-full mt-18px flex flex-wrap justify-center gap-8px font-size-14px line-height-20px font-normal c-#6b7280">
      <span>你可以试试：</span>
      <span v-for="item in exampleQuestions" :key="item" class="rounded-12px bg-#f3f4f6 px-10px py-4px">
        {{ item }}
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
:deep {
  .typer-container {
    overflow: initial;
  }
}
</style>
