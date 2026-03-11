from fastapi import FastAPI
from app.database import engine, Base
from app.routers import users, links
from app.services.tasks import delete_unused_links
import asyncio

app = FastAPI(title="URL Shortener API")

@app.on_event("startup")
async def startup():
    # создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # запуск фоновой задачи удаления неиспользуемых ссылок
    asyncio.create_task(delete_unused_links())

app.include_router(users.router)
app.include_router(links.router)

@app.get("/")
async def root():
    return {"message": "URL Shortener Service"}