import type { HookFetchPlugin } from 'hook-fetch';
import { ElMessage } from 'element-plus';
import hookFetch from 'hook-fetch';
import { sseTextDecoderPlugin } from 'hook-fetch/plugins';
import router from '@/routers';
import { useUserStore } from '@/stores';

interface BaseResponse {
  success?: boolean;
  message?: string;
  data: never;
  code?: number;
  msg?: string;
  rows: never;
}

export const request = hookFetch.create<BaseResponse, 'data' | 'rows'>({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  plugins: [sseTextDecoderPlugin({ json: true, prefix: 'data:' })],
});

function jwtPlugin(): HookFetchPlugin<BaseResponse> {
  const userStore = useUserStore();
  return {
    name: 'jwt',
    beforeRequest: async (config) => {
      config.headers = new Headers(config.headers);
      if (userStore.token) {
        config.headers.set('authorization', `Bearer ${userStore.token}`);
      }
      return config;
    },
    afterResponse: async (response) => {
      const result = response.result;
      if (result?.success === true || result?.code === 200) {
        return response;
      }

      const statusCode = result?.code;
      const message = result?.message || result?.msg || '请求失败';

      if (statusCode === 403) {
        router.replace({ name: '403' });
        ElMessage.error(message);
        return Promise.reject(response);
      }

      if (statusCode === 401 || message.includes('登录')) {
        userStore.logout();
        userStore.openLoginDialog();
      }

      ElMessage.error(message);
      return Promise.reject(response);
    },
  };
}

request.use(jwtPlugin());

export const post = request.post;

export const get = request.get;

export const put = request.put;

export const del = request.delete;

export default request;
