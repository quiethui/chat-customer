/** 客户身份相关接口：领取匿名访客、查询当前客户、注册/登录/登出。 */

import type { Customer } from '../types';
import { apiFetch, clearToken, setToken } from './client';

interface VisitorResult {
  token: string;
  access_token: string;
  customer: Customer;
}

/** 注册 / 登录成功后的结果，对齐后端 CustomerAuthResponse。 */
export interface AuthResult {
  token: string;
  access_token: string;
  customer: Customer;
}

/** 领取匿名访客身份并保存 token，返回新建客户。 */
export async function createVisitor(): Promise<Customer> {
  const result = await apiFetch<VisitorResult>('/customer/visitor', { method: 'POST' });
  setToken(result.token);
  return result.customer;
}

/** 查询当前客户信息（用于复访时校验 token 是否仍有效）。 */
export async function fetchMe(): Promise<Customer> {
  return apiFetch<Customer>('/customer/me', { method: 'GET' });
}

/** 登录已有账号；携当前匿名 token 时后端会合并当前会话，成功后保存新 token。 */
export async function login(username: string, password: string): Promise<AuthResult> {
  const result = await apiFetch<AuthResult>('/customer/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  setToken(result.token);
  return result;
}

/** 注册账号；携当前匿名 token 时后端会就地升级该访客行，成功后保存 token。 */
export async function register(username: string, password: string, nickname?: string): Promise<AuthResult> {
  const result = await apiFetch<AuthResult>('/customer/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, nickname }),
  });
  setToken(result.token);
  return result;
}

/** 登出：撤销当前 token 并清除本地保存。 */
export async function logout(): Promise<void> {
  await apiFetch('/customer/logout', { method: 'POST' });
  clearToken();
}

