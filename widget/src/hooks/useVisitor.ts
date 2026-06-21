/** 首次进入领取匿名访客身份，复访时复用 localStorage 中的 token；并提供登录/注册/登出。 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createVisitor,
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from '../api/auth';
import { getToken } from '../api/client';
import type { Customer } from '../types';

interface VisitorState {
  customer: Customer | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<Customer>;
  register: (username: string, password: string, nickname?: string) => Promise<Customer>;
  logout: () => Promise<void>;
}

/** 返回当前访客信息、初始化状态与登录/注册/登出动作。 */
export function useVisitor(): VisitorState {
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [ready, setReady] = useState(false);
  // 仅初始化一次：StrictMode 下 effect 会挂载两次，用 ref 去重，避免 /customer/me、/customer/visitor 被请求两遍。
  const startedRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    if (startedRef.current) return;
    startedRef.current = true;
    (async () => {
      try {
        if (getToken()) {
          try {
            const me = await fetchMe();
            if (mountedRef.current) setCustomer(me);
            return;
          } catch {
            // token 失效，落到下面重新领取
          }
        }
        const visitor = await createVisitor();
        if (mountedRef.current) setCustomer(visitor);
      } catch {
        // 网络异常时保持未就绪，由 UI 提示
      } finally {
        if (mountedRef.current) setReady(true);
      }
    })();
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /** 登录已有账号，成功后切换为该账号身份。 */
  const login = useCallback(async (username: string, password: string) => {
    const result = await apiLogin(username, password);
    setCustomer(result.customer);
    return result.customer;
  }, []);

  /** 注册账号（携匿名身份时为就地升级），成功后切换为注册客户身份。 */
  const register = useCallback(async (username: string, password: string, nickname?: string) => {
    const result = await apiRegister(username, password, nickname);
    setCustomer(result.customer);
    return result.customer;
  }, []);

  /** 登出：撤销当前身份后自动重新领取匿名身份，保证仍可匿名聊天。 */
  const logout = useCallback(async () => {
    await apiLogout();
    const visitor = await createVisitor();
    setCustomer(visitor);
  }, []);

  return { customer, ready, login, register, logout };
}
