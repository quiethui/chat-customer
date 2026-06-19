import type {
  ChatSessionVo,
  CreateSessionDTO,
  GetSessionListParams,
} from './types';
import { del, get, post, put } from '@/utils/request';

export function get_session_list(params: GetSessionListParams) {
  return get<ChatSessionVo[]>('/system/session/list', params).json();
}

export function create_session(data: CreateSessionDTO) {
  return post<ChatSessionVo>('/system/session', data).json();
}

export function update_session(data: ChatSessionVo) {
  return put<ChatSessionVo>('/system/session', data).json();
}

export function get_session(id: string) {
  return get<ChatSessionVo>(`/system/session/${id}`).json();
}

export function delete_session(ids: string[]) {
  return del(`/system/session/${ids.join(',')}`).json();
}
