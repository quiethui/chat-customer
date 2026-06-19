"""SQLAlchemy 连接地址、引擎和 Session 工厂。"""

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def create_session_factory(settings: Settings) -> sessionmaker[Session]:
    """按应用配置创建 SQLAlchemy Session 工厂。

    Args:
        settings: 应用运行配置，包含 MySQL 连接参数。
    """
    return sessionmaker(bind=create_engine_for_settings(settings), autoflush=False, expire_on_commit=False)


def create_engine_for_settings(settings: Settings):
    """按应用配置创建 SQLAlchemy 数据库引擎。

    Args:
        settings: 应用运行配置，包含 MySQL 连接参数和连接超时时间。
    """
    return create_engine(
        build_database_url(settings),
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "charset": settings.mysql_charset,
            "connect_timeout": settings.mysql_connect_timeout,
        },
    )


def build_database_url(settings: Settings) -> URL:
    """根据 MySQL 配置构建 SQLAlchemy 数据库 URL。

    Args:
        settings: 应用运行配置，包含 MySQL 主机、端口、账号、密码和库名。
    """
    return URL.create(
        "mysql+pymysql",
        username=settings.mysql_user,
        password=settings.mysql_password,
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database,
        query={"charset": settings.mysql_charset},
    )
