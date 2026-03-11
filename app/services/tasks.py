import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Link
from app.config import settings
from app.services.cache import cache_delete

async def delete_unused_links():
    while True:
        await asyncio.sleep(24 * 60 * 60)  # раз в сутки
        async with AsyncSessionLocal() as db:
            cutoff = datetime.now(timezone.utc) - timedelta(days=settings.UNUSED_LINK_DAYS)
            result = await db.execute(
                select(Link).where(Link.last_accessed_at < cutoff)
            )
            links = result.scalars().all()
            for link in links:
                await cache_delete(f"link:{link.code}")
                await db.delete(link)
            await db.commit()