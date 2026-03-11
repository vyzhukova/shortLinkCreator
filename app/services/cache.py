import redis.asyncio as redis
from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def cache_get(key: str):
    return await redis_client.get(key)

async def cache_set(key: str, value: str, ttl: int = 3600):
    await redis_client.setex(key, ttl, value)

async def cache_delete(key: str):
    await redis_client.delete(key)