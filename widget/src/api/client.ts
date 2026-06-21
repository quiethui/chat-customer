/** fetch 封装：拼接后端地址、注入 customer Bearer token、适配统一响应。 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'aics_customer_token';

/** 读取本地保存的 customer token。 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** 保存 customer token。 */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

/** 清除 customer token。 */
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** 构造带 token 的鉴权请求头。 */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 拼接完整后端地址。 */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** 后端统一响应信封。 */
interface Envelope<T> {
  success: boolean;
  code: number;
  message: string;
  msg: string;
  data: T;
}

/** 发起 JSON 请求并返回 data 字段；失败时抛出错误。 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || !body?.success) {
    throw new Error(body?.message || `请求失败 (${response.status})`);
  }
  return body.data;
}
