import os
import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock
import importlib
from httpx import AsyncClient, ASGITransport
from app.database import get_db

# Добавляем корень проекта в путь импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Принудительно ставим тестовую БД (SQLite)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

# Перезагружаем модуль database, чтобы использовать новую переменную окружения
import app.database
importlib.reload(app.database)
from app.database import Base, get_db
from app.main import app

# Создаём тестовый движок
engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=False)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="function")
async def db_session():
    # Создаём таблицы перед тестом
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    # Очищаем после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client(db_session):
    # Переопределяем зависимость get_db
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    # Создаём клиент с явным транспортом
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Мокаем redis_client, чтобы тесты не зависели от реального Redis"""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_client.setex.return_value = None
    mock_client.delete.return_value = None
    monkeypatch.setattr("app.services.cache.redis_client", mock_client)