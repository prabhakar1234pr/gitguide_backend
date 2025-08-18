from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create async engine with connection health checks to avoid 'connection is closed'
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,        # Validate connections before using
    pool_recycle=1800          # Recycle connections periodically (seconds)
)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# FastAPI dependency for database sessions
async def get_db():
    """
    FastAPI dependency for getting database sessions
    Used in API endpoints with Depends(get_db)
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close() 