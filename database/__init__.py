from __future__ import annotations

import config
from database import models

import sqlalchemy
import sqlalchemy.sql
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
import asyncio
from typing import Union, Any, AsyncGenerator


class Database:
    def __init__(self):
        self.engine = create_async_engine(f"mysql+aiomysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}", echo=False)
        self.session = async_sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=True)
        self.base = models.base.Base

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()

    async def create_all(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(self.base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, Any]:
    async with Database().session() as session:
        yield session


async def _test():
    async with Database() as db:
        await db.create_all()
        async with db.session() as db_session:
            pass


if __name__ == "__main__":
    asyncio.run(_test())


