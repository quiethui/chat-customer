import { useUserStore } from '@/stores';

interface FastApiResponse<T> {
  success: boolean;
  code?: number;
  message: string;
  msg?: string;
  data: T;
}

export interface KnowledgeBaseItem {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
}

export interface KnowledgeFileItem {
  id: number;
  knowledge_base_id: number;
  filename: string;
  file_path: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeFileUploadResponse {
  file: KnowledgeFileItem;
  chunk_count: number;
}

export interface KnowledgeChunkItem {
  id: number;
  knowledge_base_id: number;
  file_id: number;
  chunk_index: number;
  content: string;
  char_count: number;
  vector_id: string;
  created_at: string;
}

export interface KnowledgeFileRebuildResponse {
  id: number;
  chunk_count: number;
}

export interface CreateKnowledgeBasePayload {
  name: string;
  description?: string;
}

function getApiBaseUrl() {
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

function buildHeaders(headers?: HeadersInit) {
  const userStore = useUserStore();
  const mergedHeaders = new Headers(headers);
  if (userStore.token) {
    mergedHeaders.set('Authorization', `Bearer ${userStore.token}`);
  }
  return mergedHeaders;
}

async function requestJson<T>(path: string, init?: RequestInit) {
  const userStore = useUserStore();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: buildHeaders(init?.headers),
  });
  const result = (await response.json()) as FastApiResponse<T>;

  if (!response.ok || !result.success) {
    if (response.status === 401) {
      userStore.logout();
      userStore.openLoginDialog();
    }
    throw new Error(result.message || result.msg || '请求失败');
  }

  return result;
}

export function createKnowledgeBase(data: CreateKnowledgeBasePayload) {
  return requestJson<KnowledgeBaseItem>('/knowledge-bases', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
}

export function getKnowledgeBases() {
  return requestJson<KnowledgeBaseItem[]>('/knowledge-bases');
}

export function uploadKnowledgeBaseFile(knowledgeBaseId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return requestJson<KnowledgeFileUploadResponse>(`/knowledge-bases/${knowledgeBaseId}/files`, {
    method: 'POST',
    body: formData,
  });
}

export function getKnowledgeBaseFiles(knowledgeBaseId: number) {
  return requestJson<KnowledgeFileItem[]>(`/knowledge-bases/${knowledgeBaseId}/files`);
}

export function deleteKnowledgeBaseFile(knowledgeBaseId: number, fileId: number) {
  return requestJson<{ id: number }>(`/knowledge-bases/${knowledgeBaseId}/files/${fileId}`, {
    method: 'DELETE',
  });
}

export function reuploadKnowledgeBaseFile(knowledgeBaseId: number, fileId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return requestJson<KnowledgeFileUploadResponse>(`/knowledge-bases/${knowledgeBaseId}/files/${fileId}`, {
    method: 'PUT',
    body: formData,
  });
}

export function getKnowledgeFileChunks(knowledgeBaseId: number, fileId: number) {
  return requestJson<KnowledgeChunkItem[]>(`/knowledge-bases/${knowledgeBaseId}/files/${fileId}/chunks`);
}

export function reparseKnowledgeBaseFile(knowledgeBaseId: number, fileId: number) {
  return requestJson<KnowledgeFileRebuildResponse>(`/knowledge-bases/${knowledgeBaseId}/files/${fileId}/reparse`, {
    method: 'POST',
  });
}

export function reembeddingKnowledgeBaseFile(knowledgeBaseId: number, fileId: number) {
  return requestJson<KnowledgeFileRebuildResponse>(`/knowledge-bases/${knowledgeBaseId}/files/${fileId}/re-embedding`, {
    method: 'POST',
  });
}
