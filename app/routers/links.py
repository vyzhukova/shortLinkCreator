import random
import string
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models, schemas, dependencies
from app.database import get_db, AsyncSessionLocal
from app.auth import get_optional_user, get_current_user
from app.services.cache import cache_get, cache_set, cache_delete
from app.config import settings
from app.schemas import LinkOut
from pydantic import HttpUrl

router = APIRouter(prefix="/links", tags=["links"])

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

async def update_stats(code: str):
    """Фоновая задача для обновления статистики перехода"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.Link).where(models.Link.code == code))
        link = result.scalar_one_or_none()
        if link:
            link.access_count += 1
            link.last_accessed_at = datetime.now(timezone.utc)
            await db.commit()

@router.post("/shorten", response_model=schemas.LinkOut)
async def create_short_link(
    link_data: schemas.LinkCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user)
):
    # проверка кастомного алиаса
    if link_data.custom_alias:
        result = await db.execute(select(models.Link).where(models.Link.code == link_data.custom_alias))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Custom alias already in use")
        code = link_data.custom_alias
    else:
        while True:
            code = generate_short_code()
            result = await db.execute(select(models.Link).where(models.Link.code == code))
            if not result.scalar_one_or_none():
                break

    link = models.Link(
        original_url=str(link_data.original_url),
        code=code,
        user_id=current_user.id if current_user else None,
        expires_at=link_data.expires_at,
        project=link_data.project
    )
    print(f"Creating link with data: {link_data}")
    db.add(link)
    await db.commit()
    await db.refresh(link)

    await cache_set(f"link:{code}", link.original_url, ttl=3600)
    return link

@router.get("/search", response_model=list[schemas.LinkSearchResult])
async def search_links(
    original_url: HttpUrl = Query(...),
    db: AsyncSession = Depends(get_db)
):
    normalized = str(original_url)
    print(f"Поиск по нормализованному URL: {normalized}")  # для отладки

    result = await db.execute(
        select(models.Link).where(models.Link.original_url == normalized)
    )
    links = result.scalars().all()
    if not links:
        all_links = await db.execute(select(models.Link.original_url))
        existing = [row[0] for row in all_links]
        print(f"Существующие URL в БД: {existing}")
        raise HTTPException(status_code=404, detail="No links found for this URL")
    return links

@router.get("/by_project")
async def get_links_by_project(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    result = await db.execute(
        select(models.Link).where(models.Link.user_id == current_user.id)
    )
    links = result.scalars().all()
    
    projects = {}
    for link in links:
        proj = link.project or "default"
        projects.setdefault(proj, []).append(LinkOut.model_validate(link))
    
    return projects
@router.get("/expired", response_model=list[schemas.LinkOut])
async def get_expired_links(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    result = await db.execute(select(models.Link).where(models.Link.expires_at < now))
    return result.scalars().all()

@router.get("/{code}")
async def redirect_to_original(code: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    cached = await cache_get(f"link:{code}")
    if cached:
        background_tasks.add_task(update_stats, code)
        return RedirectResponse(url=cached, status_code=307)

    result = await db.execute(select(models.Link).where(models.Link.code == code))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Link has expired")

    link.access_count += 1
    link.last_accessed_at = datetime.now(timezone.utc)
    await db.commit()

    await cache_set(f"link:{code}", link.original_url, ttl=3600)
    return RedirectResponse(url=link.original_url, status_code=307)

@router.delete("/{code}", status_code=204)
async def delete_link(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    link = await dependencies.get_link_or_404(code, db)
    await dependencies.check_link_owner(link, current_user)
    await db.delete(link)
    await db.commit()
    await cache_delete(f"link:{code}")

@router.put("/{code}", response_model=schemas.LinkOut)
async def update_link(
    code: str,
    link_update: schemas.LinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    link = await dependencies.get_link_or_404(code, db)
    await dependencies.check_link_owner(link, current_user)
    link.original_url = str(link_update.original_url)
    await db.commit()
    await db.refresh(link)
    await cache_delete(f"link:{code}")
    return link

@router.get("/{code}/stats", response_model=schemas.LinkStats)
async def get_link_stats(code: str, db: AsyncSession = Depends(get_db)):
    link = await dependencies.get_link_or_404(code, db)
    return link