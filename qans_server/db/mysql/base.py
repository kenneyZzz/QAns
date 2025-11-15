from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from qans_server.setting_config import settings

# 读取连接串，优先环境变量 MYSQL_DSN，例如：
MYSQL_DSN = settings.mysql_dsn

# 建立 Engine（推荐开启 pool_pre_ping 避免连接断开）
engine = create_engine(MYSQL_DSN, pool_pre_ping=True, future=True)

# 创建 Session 工厂（避免提交后属性过期导致 DetachedInstanceError）
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)

# Declarative Base，模型需从此 Base 继承
Base = declarative_base()

@contextmanager
def get_session() -> Session:
    """上下文管理的 Session，自动提交/回滚/关闭。"""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


