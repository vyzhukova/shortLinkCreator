from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = Field(None, min_length=1, max_length=50)
    expires_at: Optional[datetime] = None
    project: Optional[str] = None

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v):
        if v is not None:
            # Если datetime naive, считаем, что оно в UTC
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v < datetime.now(timezone.utc):
                raise ValueError('expires_at must be in the future')
        return v

class LinkUpdate(BaseModel):
    original_url: HttpUrl

class LinkOut(BaseModel):
    code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    access_count: int
    project: Optional[str]
    user_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class LinkStats(LinkOut):
    pass

class LinkSearchResult(BaseModel):
    code: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    project: Optional[str]