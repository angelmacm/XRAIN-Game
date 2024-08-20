from database.db import BattleRoyaleDB
from components.config import dbConfig
from asyncio import run


dbInstance = BattleRoyaleDB(
    host=dbConfig["db_server"],
    dbName=dbConfig["db_name"],
    username=dbConfig["db_username"],
    password=dbConfig["db_password"],
    verbose=dbConfig.getboolean("verbose"),
)


async def main():
    await dbInstance.syncBattleWins()


run(main())
