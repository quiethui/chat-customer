/** 登录 / 注册弹窗：纯 React 实现，登录与注册可切换。 */

import { useState } from 'react';
import type { Customer } from '../types';

interface AuthModalProps {
  /** 弹窗是否打开。 */
  open: boolean;
  /** 关闭弹窗回调。 */
  onClose: () => void;
  /** 登录动作（来自 useVisitor）。 */
  onLogin: (username: string, password: string) => Promise<Customer>;
  /** 注册动作（来自 useVisitor）。 */
  onRegister: (username: string, password: string, nickname?: string) => Promise<Customer>;
}

/** 登录/注册弹窗组件。 */
export function AuthModal({ open, onClose, onLogin, onRegister }: AuthModalProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const reset = () => {
    setUsername('');
    setPassword('');
    setNickname('');
    setError('');
  };

  const close = () => {
    reset();
    onClose();
  };

  const submit = async () => {
    if (!username.trim() || !password) {
      setError('请输入账号和密码');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      if (mode === 'login') {
        await onLogin(username.trim(), password);
      } else {
        await onRegister(username.trim(), password, nickname.trim() || undefined);
      }
      close();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="aics-modal-mask" onClick={close}>
      <div
        className="aics-modal"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="aics-modal-head">
          <span className="aics-modal-title">{mode === 'login' ? '登录' : '注册'}</span>
          <button className="aics-icon-btn aics-modal-close" type="button" onClick={close} aria-label="关闭">
            ×
          </button>
        </div>
        <input
          className="aics-field"
          placeholder="账号"
          value={username}
          autoComplete="username"
          onChange={(event) => setUsername(event.target.value)}
        />
        <input
          className="aics-field"
          type="password"
          placeholder="密码"
          value={password}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          onChange={(event) => setPassword(event.target.value)}
        />
        {mode === 'register' && (
          <input
            className="aics-field"
            placeholder="昵称（可选）"
            value={nickname}
            onChange={(event) => setNickname(event.target.value)}
          />
        )}
        {error && <div className="aics-modal-error">{error}</div>}
        <button className="aics-modal-submit" type="button" disabled={submitting} onClick={submit}>
          {submitting ? '处理中…' : mode === 'login' ? '登录' : '注册'}
        </button>
        <button
          className="aics-link"
          type="button"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login');
            setError('');
          }}
        >
          {mode === 'login' ? '没有账号？去注册' : '已有账号？去登录'}
        </button>
      </div>
    </div>
  );
}
