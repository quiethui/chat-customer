"""项目根目录的兼容入口，用于直接暴露 FastAPI 应用实例。"""

from app.main import app

__all__ = ["app"]

# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")