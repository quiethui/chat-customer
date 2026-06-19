import { defineStore } from 'pinia';

export const useRagTestStore = defineStore('rag-test', () => {
  const enabled = ref(false);

  return {
    enabled,
  };
}, {
  persist: true,
});
