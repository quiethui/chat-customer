"""文件处理工具。"""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


async def save_supported_upload_file(
    file: UploadFile,
    upload_dir: Path,
    supported_extensions: set[str],
    sub_dir: Path | str | None = None,
    max_bytes: int | None = None,
) -> tuple[Path, str]:
    """校验上传文件类型并保存到本地目录。

    Args:
        file: 前端上传的文件对象。
        upload_dir: 上传文件根目录。
        supported_extensions: 允许上传的文件扩展名集合。
        sub_dir: 上传目录下的可选子目录名称。
    """
    original_name = file.filename or "document"
    suffix = Path(original_name).suffix.lower()
    if suffix not in supported_extensions:
        supported = ", ".join(sorted(supported_extensions))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"仅支持以下文件类型：{supported}",
        )
    return await save_upload_file(file, upload_dir, sub_dir, max_bytes), original_name


async def save_upload_file(
    file: UploadFile,
    upload_dir: Path,
    sub_dir: Path | str | None = None,
    max_bytes: int | None = None,
) -> Path:
    """将上传文件分块保存到本地目录，并返回保存后的路径。

    Args:
        file: 前端上传的文件对象。
        upload_dir: 上传文件根目录。
        sub_dir: 上传目录下的可选子目录名称。
    """
    target_dir = build_upload_subdirectory(upload_dir, sub_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    # 只取文件名部分，避免用户上传的文件名中带路径导致目录穿越。
    safe_name = Path(file.filename or "document").name.replace("\\", "_")
    saved_path = target_dir / f"{uuid4().hex}_{safe_name}"
    written_bytes = 0
    try:
        with saved_path.open("wb") as target:
            # 每次读取 1MB，避免大文件一次性读入内存。
            while chunk := await file.read(1024 * 1024):
                written_bytes += len(chunk)
                if max_bytes is not None and max_bytes > 0 and written_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"上传文件不能超过 {max_bytes} 字节",
                    )
                target.write(chunk)
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise
    return saved_path


def build_upload_subdirectory(
    upload_dir: Path,
    sub_dir: Path | str | None = None,
) -> Path:
    """按业务子目录构建上传文件保存目录。

    Args:
        upload_dir: 上传文件根目录。
        sub_dir: 上传目录下的可选子目录名称。
    """
    business_dir = _normalize_upload_subdir(sub_dir)
    return upload_dir / business_dir


def _normalize_upload_subdir(sub_dir: Path | str | None) -> Path:
    """标准化上传业务子目录，避免绝对路径和目录穿越。

    Args:
        sub_dir: 上传目录下的可选子目录名称。
    """
    if sub_dir is None:
        return Path("documents")

    path = Path(sub_dir)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise ValueError("上传子目录必须是安全的相对路径")
    return path
