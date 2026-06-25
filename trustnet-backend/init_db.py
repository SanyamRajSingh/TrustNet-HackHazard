import asyncio
from app.models.database import engine
from app.models.postgres import Base

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())
