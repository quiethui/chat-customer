import type { GetSessionListVO } from './types';

export function getModelList() {
  const modelName = import.meta.env.VITE_MODEL_NAME || 'FastAPI RAG';
  return Promise.resolve({
    data: [
      {
        id: 1,
        modelName,
        modelDescribe: '当前 FastAPI 项目的知识库问答接口',
        modelType: 'rag',
        remark: '对接 POST /chat 与 POST /upload',
      } satisfies GetSessionListVO,
    ],
  });
}
