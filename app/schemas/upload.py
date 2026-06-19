"""上传接口的数据模型定义。"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """知识库文件上传后的导入结果。"""

    file_name: str = Field(..., description="用户上传时的原始文件名。")
    document_id: str = Field(..., description="本次导入生成的文档唯一 ID。")
    chunk_count: int = Field(..., description="文档解析后写入向量库的文本块数量。")


class ChunkItem(BaseModel):
    """单个文档切块的响应对象。"""

    index: int = Field(..., description="切块序号，从 1 开始。")
    content: str = Field(..., description="切块文本内容。")
    char_count: int = Field(..., description="切块文本字符数。")


class VectorChunkItem(ChunkItem):
    """包含 embedding 向量值的文档切块响应对象。"""

    vector: list[float] = Field(..., description="当前切块对应的 embedding 向量值。")


class UploadChunksResponse(BaseModel):
    """上传文档后直接返回切块的响应对象。"""

    file_name: str = Field(..., description="用户上传时的原始文件名。")
    chunk_count: int = Field(..., description="文档解析后的文本切块数量。")
    chunks: list[ChunkItem] = Field(..., description="文档切块列表。")


class UploadVectorsResponse(BaseModel):
    """上传文档后直接返回切块和向量的响应对象。"""

    file_name: str = Field(..., description="用户上传时的原始文件名。")
    document_id: str | None = Field(default=None, description="导入向量库时生成的文档 ID；仅预览时为空。")
    chunk_count: int = Field(..., description="文档解析后的文本切块数量。")
    embedding_dimension: int = Field(..., description="当前 embedding 模型输出向量维度。")
    chunks: list[VectorChunkItem] = Field(..., description="包含文本和向量值的切块列表。")
