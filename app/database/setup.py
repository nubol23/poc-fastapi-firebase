import asyncio

import databases
import orm

database = databases.Database("sqlite:///db.sqlite")
models = orm.ModelRegistry(database=database)


async def init_database():
    await models.create_all()
