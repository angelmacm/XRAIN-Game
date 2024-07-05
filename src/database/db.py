from database.models import BattleQuotes, NFTTraitList, RewardsTable
from components.config import dbConfig
from components.logging import loggingInstance

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import update
from sqlalchemy.sql import func
from datetime import timedelta, datetime
from sqlalchemy.future import select

class BattleRoyaleDB:
    def __init__(self, host, dbName, username, password, verbose):
        
        #                   username          if empty, do not add :, else :password      host   dbName
        sqlLink = f"mysql+aiomysql://{username}{'' if password in ['', None] else f':{password}'}@{host}/{dbName}"
        loggingInstance.info(f"DB Link: {sqlLink}")
        self.dbEngine = create_async_engine(sqlLink, 
                                            echo=verbose,
                                            pool_recycle = 3600,
                                            pool_pre_ping=True)
        
        self.asyncSessionMaker = async_sessionmaker(bind=self.dbEngine,
                                                    expire_on_commit=False)
        self.verbose = verbose
        
    async def getNFTInfo(self, xrpId):
        async with self.asyncSessionMaker() as session: 
            
            query = select(
                        RewardsTable.tokenIdBattleNFT,
                        RewardsTable.xrainPower,
                        RewardsTable.nftlink,
                        RewardsTable.reserveXRAIN,
                        RewardsTable.reserveBoosts
                    ).filter(
                        RewardsTable.xrpId == xrpId
                    )
                    
            sessionResult = await session.execute(query)
            sessionResult = sessionResult.first()

            if not sessionResult:
                raise Exception("xrpIdNotFound")
            
            tokenId, xrainPower, nftLink, reserveXrain, reserveBoosts = sessionResult
            
            return {'nftToken': tokenId,
                    'xrainPower': xrainPower,
                    'nftLink': nftLink,
                    'reserveXrain': reserveXrain,
                    'reserveBoosts': reserveBoosts}