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
                        RewardsTable.reserveBoosts,
                        RewardsTable.battleWins
                    ).filter(
                        RewardsTable.xrpId == xrpId
                    )
                    
            sessionResult = await session.execute(query)
            sessionResult = sessionResult.first()
            
            loggingInstance.info(f"getNFTInfo({xrpId}): {sessionResult}") if self.verbose else None

            if not sessionResult:
                raise Exception("xrpIdNotFound")
            
            tokenId, xrainPower, nftLink, reserveXrain, reserveBoosts, battleWins = sessionResult
            
            if battleWins >= 100:
                battleRank = "Diamond Xrain King :gem::crown:"
            elif battleWins < 10:
                battleRank = "Rookie :punch:"
            elif battleWins < 25:
                battleRank = "Bronze Warrior :third_place:"
            elif battleWins < 50:
                battleRank = "Silver Xrain Lord :coin:"
            elif battleWins < 100:
                battleRank = "Golden Oracle Warlord :trident:"
            
            return {'nftToken': tokenId,
                    'xrainPower': xrainPower,
                    'nftLink': nftLink,
                    'reserveXrain': reserveXrain,
                    'reserveBoosts': reserveBoosts,
                    'battleWins': battleWins,
                    'battleRank': battleRank}
            
    async def setNFT(self, xrpId, token, nftLink, xrainPower, taxonId, groupName):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(tokenIdBattleNFT = token, nftlink = nftLink, xrainPower = xrainPower, taxonId = taxonId, nftGroupName = groupName)
                        )
                loggingInstance.info(f"setNFT({xrpId}, {token}): Success") if self.verbose else None
    
    async def getNFTOption(self, xrpId):
        async with self.asyncSessionMaker() as session:     
            query = select(NFTTraitList.tokenId,
                           NFTTraitList.nftlink,
                           NFTTraitList.totalXRAIN,
                           NFTTraitList.nftGroupName,
                           NFTTraitList.taxonId
                    ).filter(
                            NFTTraitList.xrpId == xrpId,
                            NFTTraitList.nftlink != ''
                    ).order_by(
                            NFTTraitList.nftGroupName
                    ).order_by(NFTTraitList.totalXRAIN.desc())
            queryResult = await session.execute(query)
            queryResult = queryResult.all()
            
            if not queryResult:
                raise Exception("xrpIdNotFound")
            
            nftOptions = {}
            
            for row in queryResult:
                tokenId, nftLink, totalXrain, nftGroupName, taxonId = row
                entry = {"tokenId": tokenId, 'nftLink': nftLink, 'totalXrain': totalXrain, 'taxonId': taxonId, 'label': f"*{tokenId[-6:]}   | Base power: {totalXrain}"}
                if nftGroupName in nftOptions.keys():
                    nftOptions[nftGroupName].append(entry)
                else:
                    nftOptions[nftGroupName] = [entry]
            
            loggingInstance.error(f"getNFTOption({xrpId}): {nftOptions}") if self.verbose else None
            
            return nftOptions
        
    async def addWin(self, xrpId):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(battleWins = RewardsTable.battleWins + 1)
                        )
                loggingInstance.info(f"addWin({xrpId}): Success") if self.verbose else None
    
    async def addBoost(self, xrpId, boost):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(reserveBoosts = RewardsTable.reserveBoosts + boost)
                        )
                loggingInstance.info(f"addBoost({xrpId}): Success") if self.verbose else None
                
    async def addXrain(self, xrpId, xrain):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(reserveXRAIN = RewardsTable.reserveXRAIN + xrain)
                        )
                loggingInstance.info(f"addXrain({xrpId}): Success") if self.verbose else None
                
    async def placeWager(self, xrpId, xrain):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(reserveXRAIN = RewardsTable.reserveXRAIN - xrain)
                        )
                loggingInstance.info(f"addXrain({xrpId}): Success") if self.verbose else None
                
    async def claimBoost (self, xrpId):
        async with self.asyncSessionMaker() as session:    
            async with session.begin(): 
                await session.execute(
                    update(RewardsTable).where(RewardsTable.xrpId == xrpId).values(reserveBoosts = RewardsTable.reserveBoosts - 1)
                        )
                loggingInstance.info(f"addBoost({xrpId}): Success") if self.verbose else None
                
    async def getRandomQuote(self):
        async with self.asyncSessionMaker() as session:    
            query = select(BattleQuotes.quoteType,
                           BattleQuotes.quoteDesc
                    ).order_by(
                            func.random()
                    )
            queryResult = await session.execute(query)
            queryResult = queryResult.all()
            
            if not queryResult:
                loggingInstance.info(f"addBoost(): RandomQuoteGetError") if self.verbose else None
                raise Exception("RandomQuoteGetError")
            
            loggingInstance.info(f"addBoost(): {queryResult}") if self.verbose else None
            return queryResult