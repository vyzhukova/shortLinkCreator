from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models
from app.database import get_db

async def get_link_or_404(code: str, db: AsyncSession):
    result = await db.execute(select(models.Link).where(models.Link.code == code))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return link

async def check_link_owner(link: models.Link, user: models.User):
    if link.user_id is not None and link.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return True