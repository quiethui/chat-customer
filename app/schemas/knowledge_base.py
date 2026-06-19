"""知识库管理接口的数据模型定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求对象。"""

    name: str = Field(..., min_length=1, max_length=100, description="知识库名称。")
    description: str | None = Field(default=None, max_length=500, description="知识库描述。")


class KnowledgeBaseResponse(BaseModel):
    """知识库响应对象。"""

    id: int = Field(..., description="知识库 ID。")
    name: str = Field(..., description="知识库名称。")
    description: str | None = Field(default=None, description="知识库描述。")
    created_at: datetime = Field(..., description="知识库创建时间。")


class KnowledgeFileResponse(BaseModel):
    """知识库文件响应对象。"""

    id: int = Field(..., description="文件 ID。")
    knowledge_base_id: int = Field(..., description="所属知识库 ID。")
    filename: str = Field(..., description="用户上传的原始文件名。")
    file_path: str = Field(..., description="文件保存路径。")
    status: str = Field(..., description="文件状态：processing=处理中，active=可用，deleted=已删除，failed=处理失败。")
    chunk_count: int = Field(default=0, description="文件当前关联的切块数量。")
    created_at: datetime = Field(..., description="文件创建时间。")


class KnowledgeFileUploadResponse(BaseModel):
    """知识库文件上传或重传响应对象。"""

    file: KnowledgeFileResponse = Field(..., description="文件信息。")
    chunk_count: int = Field(..., description="本次写入的切块数量。")


class KnowledgeChunkResponse(BaseModel):
    """知识库文件切块响应对象。"""

    id: int = Field(..., description="切块 ID。")
    knowledge_base_id: int = Field(..., description="所属知识库 ID。")
    file_id: int = Field(..., description="所属文件 ID。")
    chunk_index: int = Field(..., description="切块序号，从 1 开始。")
    content: str = Field(..., description="切块文本内容。")
    char_count: int = Field(..., description="切块文本字符数。")
    vector_id: str = Field(..., description="向量库中的业务向量 ID。")
    created_at: datetime = Field(..., description="切块创建时间。")
