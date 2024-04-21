from database.models import Base
from database.engine import async_engine
import asyncio


async def create_tables(engine):
    """
    Создает таблицы в БД
    :param engine: Асинхронный движок для выполнения операций с БД.
    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine):
    """
    Удаляет таблицы из БД.
    :param engine: Асинхронный движок для выполнения операций с БД.
    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Создает таблицы
# asyncio.run(create_tables(async_engine))

# Удаляет таблицы
# asyncio.run(drop_tables(async_engine))
