from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
import pytest
from app.auth import get_optional_user
from app.routers.links import generate_short_code
from app.schemas import LinkCreate
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone

def test_generate_short_code_length():
    code = generate_short_code(8)
    assert len(code) == 8
    assert code.isalnum()

def test_generate_short_code_uniqueness():
    codes = {generate_short_code() for _ in range(100)}
    assert len(codes) == 100  

def test_validate_expires_at_future():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    link = LinkCreate(original_url="https://example.com", expires_at=future)
    assert link.expires_at == future

def test_validate_expires_at_past():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValidationError):
        LinkCreate(original_url="https://example.com", expires_at=past)

def test_validate_expires_at_aware_future():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    link = LinkCreate(original_url="https://example.com", expires_at=future)
    assert link.expires_at == future

def test_validate_expires_at_aware_past():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValidationError):
        LinkCreate(original_url="https://example.com", expires_at=past)

def test_validate_expires_at_naive_future():
    naive_future = datetime.utcnow() + timedelta(days=1)  
    link = LinkCreate(original_url="https://example.com", expires_at=naive_future)
    assert link.expires_at == naive_future.replace(tzinfo=timezone.utc)

def test_validate_expires_at_naive_past():
    naive_past = datetime.utcnow() - timedelta(days=1)
    with pytest.raises(ValidationError):
        LinkCreate(original_url="https://example.com", expires_at=naive_past)

@pytest.mark.asyncio
async def test_get_optional_user_invalid_token():
    """Должен вернуть None при недействительном токене (HTTPException)."""
    mock_db = AsyncMock()
    token = "invalid_token"

    with patch("app.auth.get_current_user", new=AsyncMock(side_effect=HTTPException(status_code=401))) as mock_get_current:
        result = await get_optional_user(token=token, db=mock_db)

        assert result is None
        mock_get_current.assert_awaited_once_with(token, mock_db)