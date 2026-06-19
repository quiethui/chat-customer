import type { EmailCodeDTO, LoginDTO, LoginVO, RegisterDTO } from './types';
import { post } from '@/utils/request';

export const login = (data: LoginDTO) => post<LoginVO>('/auth/login', data).json();

export const emailCode = (data: EmailCodeDTO) => post('/resource/email/code', data).json();

export const register = (data: RegisterDTO) => post('/auth/register', data).json();

export const logoutApi = () => post('/auth/logout', {}).json();
