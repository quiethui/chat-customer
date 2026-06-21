import type { RequestOptions } from '@@/plugin-request/request';
import type { RequestConfig } from '@umijs/max';
import { history } from '@umijs/max';
import { message } from 'antd';
import { clearToken, getToken } from '@/utils/auth';

const loginPath = '/user/login';

// 与后端约定的统一响应结构：{ success, code, message, msg, data }
interface ResponseStructure<T = unknown> {
  success: boolean;
  code: number;
  message: string;
  msg: string;
  data: T;
}

/**
 * @name 错误处理与请求拦截
 * 适配后端统一响应格式，并注入 Bearer Token、处理登录失效。
 * @doc https://umijs.org/docs/max/request#配置
 */
export const errorConfig: RequestConfig = {
  errorConfig: {
    // HTTP 2xx 但业务标记失败时，转为异常交给 errorHandler
    errorThrower: (res) => {
      const {
        success,
        message: bizMessage,
        msg,
        data,
      } = res as unknown as ResponseStructure;
      if (!success) {
        const error: any = new Error(bizMessage || msg);
        error.name = 'BizError';
        error.info = { message: bizMessage || msg, data };
        throw error;
      }
    },
    // 统一错误处理
    errorHandler: (error: any, opts: any) => {
      if (opts?.skipErrorHandler) throw error;

      // errorThrower 抛出的业务错误
      if (error.name === 'BizError') {
        const info = error.info as { message?: string } | undefined;
        if (info?.message) {
          message.error(info.message);
        }
        return;
      }

      // Axios 错误：服务器返回了非 2xx 状态码
      if (error.response) {
        const { status } = error.response;
        const body = error.response.data as
          | Partial<ResponseStructure>
          | undefined;
        const text = body?.message || body?.msg;
        // 登录失效：清除本地 Token 并跳转登录页
        if (status === 401) {
          clearToken();
          if (window.location.pathname !== loginPath) {
            history.replace(
              `${loginPath}?redirect=${encodeURIComponent(
                window.location.pathname + window.location.search,
              )}`,
            );
          }
          message.error(text || '登录已过期，请重新登录');
          return;
        }
        message.error(text || `请求失败：${status}`);
        return;
      }

      // 请求已发出但无响应
      if (error.request) {
        message.error('网络无响应，请稍后重试');
        return;
      }
      message.error('请求发生错误，请重试');
    },
  },

  // 请求拦截器：为每个请求注入 Bearer Token
  requestInterceptors: [
    (config: RequestOptions) => {
      const token = getToken();
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      return config;
    },
  ],

  responseInterceptors: [],
};
