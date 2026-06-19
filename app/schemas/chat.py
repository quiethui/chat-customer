"""聊天接口的数据模型定义。"""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """聊天提问请求体。"""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., min_length=1, max_length=2000, description="用户本轮输入的问题文本。")
    session_id: str | None = Field(default=None, alias="sessionId", max_length=64, description="会话 ID；为空时后端自动创建新会话。")
    rag_test: bool = Field(default=False, alias="ragTest", description="是否开启 RAG 测试模式；开启后只返回检索结果和 Prompt，不调用模型。")
    knowledge_base_ids: list[int] | None = Field(default=None, alias="knowledgeBaseIds", description="可选的知识库过滤 ID 列表。")
    file_ids: list[int] | None = Field(default=None, alias="fileIds", description="可选的知识库文件过滤 ID 列表。")


class RagDebugChunk(BaseModel):
    """RAG 测试模式下返回的单个检索 Chunk。"""

    rank: int = Field(..., description="检索结果排序，从 1 开始。")
    score: float = Field(..., description="向量相似度分数。")
    content: str = Field(..., description="Chunk 文本内容。")
    file_name: str | None = Field(default=None, alias="fileName", description="命中的文件名。")
    file_id: str | None = Field(default=None, alias="fileId", description="命中的文件 ID。")
    knowledge_base_id: str | None = Field(default=None, alias="knowledgeBaseId", description="命中的知识库 ID。")
    knowledge_base_name: str | None = Field(default=None, alias="knowledgeBaseName", description="命中的知识库名称。")
    vector_id: str | None = Field(default=None, alias="vectorId", description="命中的向量业务 ID。")
    document_id: str | None = Field(default=None, alias="documentId", description="文档批次 ID。")
    used_in_prompt: bool = Field(default=False, alias="usedInPrompt", description="该 Chunk 是否进入最终 Prompt。")


class RagDebugResponse(BaseModel):
    """RAG 测试模式的调试信息。"""

    elapsed_ms: float = Field(..., alias="elapsedMs", description="RAG 检索和 Prompt 构建耗时，单位毫秒。")
    search_limit: int = Field(..., alias="searchLimit", description="向量库本次实际检索候选数量。")
    prompt_context_count: int = Field(..., alias="promptContextCount", description="进入最终 Prompt 的 Chunk 数量。")
    final_prompt: str = Field(..., alias="finalPrompt", description="最终 Prompt。")
    chunks: list[RagDebugChunk] = Field(default_factory=list, description="检索命中的 Chunk 列表。")


class ChatResponse(BaseModel):
    """聊天回答响应数据。"""

    model_config = ConfigDict(populate_by_name=True)

    answer: str = Field(..., description="大模型最终生成的客服回答。")
    references: list[str] = Field(default_factory=list, description="本次回答引用的知识库片段或业务工具结果。")
    session_id: str | None = Field(default=None, alias="sessionId", description="本次问答所属会话 ID。")
    prompt: str = Field(..., description="实际发送给模型的 Prompt，方便调试 RAG 效果。")
    rag_test: bool = Field(default=False, alias="ragTest", description="是否为 RAG 测试响应。")
    rag_debug: RagDebugResponse | None = Field(default=None, alias="ragDebug", description="RAG 测试调试信息。")
