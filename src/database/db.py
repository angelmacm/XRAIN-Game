from database.models import BattleQuotes, NFTTraitList, RewardsTable, ClaimQuotes
from components.config import dbConfig
from components.logging import loggingInstance

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import update, or_
from sqlalchemy.sql import func
from datetime import timedelta, datetime
from sqlalchemy.future import select


class BattleRoyaleDB:
    def __init__(self, host, dbName, username, password, verbose):

        #                   username          if empty, do not add :, else :password      host   dbName
        sqlLink = f"mysql+aiomysql://{username}{'' if password in ['', None] else f':{password}'}@{host}/{dbName}"
        loggingInstance.info(f"DB Link: {sqlLink}")
        self.dbEngine = create_async_engine(
            sqlLink, pool_recycle=3600, pool_pre_ping=True
        )

        self.asyncSessionMaker = async_sessionmaker(
            bind=self.dbEngine, expire_on_commit=False
        )
        self.verbose = verbose

    # A temporary function that helps with the migration of battle wins from rewards to nfttraitlist
    async def syncBattleWins(self):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                query = select(
                    RewardsTable.tokenIdBattleNFT, RewardsTable.battleWins
                ).filter(RewardsTable.tokenIdBattleNFT != "")
                query = await session.execute(query)
                entries = query.all()

                for tokenId, battleWins in entries:
                    await session.execute(
                        update(NFTTraitList)
                        .where(NFTTraitList.tokenId == tokenId)
                        .values(battleWins=battleWins)
                    )
                    (
                        loggingInstance.info(
                            f"addBoost({tokenId}, {battleWins}): Success"
                        )
                        if self.verbose
                        else None
                    )
        print("Done")

    async def getNFTInfo(self, uniqueId="", npc=False):
        async with self.asyncSessionMaker() as session:

            query = select(
                RewardsTable.xrpId,
                RewardsTable.tokenIdBattleNFT,
                RewardsTable.xrainPower,
                RewardsTable.nftlink,
                RewardsTable.reserveXRAIN,
                RewardsTable.reserveBoosts,
                RewardsTable.battleWins,
                RewardsTable.nftGroupName,
                RewardsTable.taxonId,
            )

            if not npc:
                query = query.filter(
                    or_(
                        RewardsTable.xrpId == uniqueId,
                        RewardsTable.discordId == uniqueId,
                    )
                )

            if npc:
                query = (
                    query.filter(RewardsTable.xrpId.like("npcPlayer%"))
                    .order_by(func.random())
                    .limit(1)
                )

            sessionResult = await session.execute(query)
            sessionResult = sessionResult.first()

            (
                loggingInstance.info(f"getNFTInfo({uniqueId}): {sessionResult}")
                if self.verbose
                else None
            )

            if not sessionResult:
                raise Exception("xrpIdNotFound")

            (
                xrpId,
                tokenId,
                xrainPower,
                nftLink,
                reserveXrain,
                reserveBoosts,
                battleWins,
                nftGroupName,
                taxonId,
            ) = sessionResult

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

            (
                loggingInstance.info(f"getNFTInfo({uniqueId}): Success")
                if self.verbose
                else None
            )

            return {
                "xrpId": xrpId,
                "nftToken": tokenId,
                "xrainPower": xrainPower,
                "nftLink": nftLink,
                "reserveXrain": reserveXrain,
                "reserveBoosts": reserveBoosts,
                "battleWins": battleWins,
                "battleRank": battleRank,
                "nftGroupName": nftGroupName,
                "taxonId": taxonId,
                "npc": npc,
            }

    async def setNFT(self, xrpId, token, nftLink, xrainPower, taxonId, groupName):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(RewardsTable.xrpId == xrpId)
                    .values(
                        tokenIdBattleNFT=token,
                        nftlink=nftLink,
                        xrainPower=xrainPower,
                        taxonId=taxonId,
                        nftGroupName=groupName,
                    )
                )
                (
                    loggingInstance.info(f"setNFT({xrpId}, {token}): Success")
                    if self.verbose
                    else None
                )

    async def getNFTOption(self, discordID):
        async with self.asyncSessionMaker() as session:
            query = (
                select(
                    NFTTraitList.tokenId,
                    NFTTraitList.nftlink,
                    NFTTraitList.totalXRAIN,
                    NFTTraitList.nftGroupName,
                    NFTTraitList.taxonId,
                )
                .filter(RewardsTable.discordId == discordID, NFTTraitList.nftlink != "")
                .order_by(NFTTraitList.nftGroupName)
                .order_by(NFTTraitList.totalXRAIN.desc())
                .join(RewardsTable, RewardsTable.xrpId == NFTTraitList.xrpId)
            )
            queryResult = await session.execute(query)
            queryResult = queryResult.all()

            if not queryResult:
                (
                    loggingInstance.Error(f"getNFTOption({discordID}): xrpIdNotFound")
                    if self.verbose
                    else None
                )
                raise Exception("xrpIdNotFound")

            nftOptions = {}

            for row in queryResult:
                tokenId, nftLink, totalXrain, nftGroupName, taxonId = row
                entry = {
                    "tokenId": tokenId,
                    "nftLink": nftLink,
                    "totalXrain": totalXrain,
                    "taxonId": taxonId,
                    "label": f"{nftGroupName} *{tokenId[-6:]} | XRAIN {totalXrain}",
                }

                if not len(nftGroupName):
                    continue

                if nftGroupName in nftOptions.keys():
                    nftOptions[nftGroupName].append(entry)
                else:
                    nftOptions[nftGroupName] = [entry]

            (
                loggingInstance.info(f"getNFTOption({discordID}): success")
                if self.verbose
                else None
            )

            return nftOptions

    async def addWin(self, xrpId):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(RewardsTable.xrpId == xrpId)
                    .values(battleWins=RewardsTable.battleWins + 1)
                )
                (
                    loggingInstance.info(f"addWin({xrpId}): Success")
                    if self.verbose
                    else None
                )

    async def addBoost(self, uniqueId, boost):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(
                        or_(
                            RewardsTable.xrpId == uniqueId,
                            RewardsTable.discordId == uniqueId,
                        )
                    )
                    .values(reserveBoosts=RewardsTable.reserveBoosts + boost)
                )
                (
                    loggingInstance.info(f"addBoost({uniqueId}): Success")
                    if self.verbose
                    else None
                )

    async def addXrain(self, uniqueId, xrain):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(
                        or_(
                            RewardsTable.xrpId == uniqueId,
                            RewardsTable.discordId == uniqueId,
                        )
                    )
                    .values(reserveXRAIN=RewardsTable.reserveXRAIN + xrain)
                )
                (
                    loggingInstance.info(f"addXrain({uniqueId}): Success")
                    if self.verbose
                    else None
                )

    async def placeWager(self, xrpId, xrain):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(RewardsTable.xrpId == xrpId)
                    .values(reserveXRAIN=RewardsTable.reserveXRAIN - xrain)
                )
                (
                    loggingInstance.info(f"addXrain({xrpId}): Success")
                    if self.verbose
                    else None
                )

    async def claimBoost(self, xrpId):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                await session.execute(
                    update(RewardsTable)
                    .where(RewardsTable.xrpId == xrpId)
                    .values(reserveBoosts=RewardsTable.reserveBoosts - 1)
                )
                (
                    loggingInstance.info(f"addBoost({xrpId}): Success")
                    if self.verbose
                    else None
                )

    async def getRandomQuote(self, revival: bool = False):
        async with self.asyncSessionMaker() as session:
            query = (
                select(BattleQuotes.quoteType, BattleQuotes.quoteDesc)
                .order_by(func.random())
                .limit(1)
            )
            queryResult = await session.execute(query)
            queryResult = queryResult.first()

            if not queryResult:
                raise Exception("RandomQuoteGetError")

            if queryResult[0] == "Revival" and not revival:
                return await self.getRandomQuote()

            return queryResult

    async def checkDiscordId(self, discordId):
        async with self.asyncSessionMaker() as session:
            query = select(RewardsTable.discordId, RewardsTable.xrpId).filter(
                RewardsTable.discordId == discordId
            )
            queryResult = await session.execute(query)
            queryResult = queryResult.first()

            if queryResult is None:
                (
                    loggingInstance.error(
                        f"checkDiscordId({discordId}): DiscordIdNotFound"
                    )
                    if self.verbose
                    else None
                )
                raise Exception("DiscordIdNotFound")

            (
                loggingInstance.info(f"checkDiscordId({discordId}): Success")
                if self.verbose
                else None
            )
            return queryResult[1]

    async def setDiscordId(self, discordId, xrpId):
        async with self.asyncSessionMaker() as session:
            async with session.begin():
                # Check if there is any xrpId that the discordId is linked to
                checkQuery = select(RewardsTable.xrpId, RewardsTable.discordId).filter(
                    RewardsTable.discordId == discordId
                )

                checkQuery = await session.execute(checkQuery)
                checkQueryResult = checkQuery.first()

                if checkQueryResult is not None:
                    # If there is not, remove the link
                    (
                        loggingInstance.info(f"Discord ID Found, removing...")
                        if self.verbose
                        else None
                    )
                    await session.execute(
                        update(RewardsTable)
                        .where(RewardsTable.xrpId == checkQueryResult[0])
                        .values(discordId="")
                    )

                # add the Discord ID
                await session.execute(
                    update(RewardsTable)
                    .where(RewardsTable.xrpId == xrpId)
                    .values(discordId=discordId)
                )
                (
                    loggingInstance.info(f"setDiscordI({discordId}, {xrpId}): Success")
                    if self.verbose
                    else None
                )

    async def getClaimQuote(self, taxonId) -> dict:
        async with self.asyncSessionMaker() as session:
            # Query the rows of taxonId
            query = select(ClaimQuotes.taxonId).group_by(ClaimQuotes.taxonId)
            taxonIdList = await session.execute(query)

            # Get, parse, and put them into a list
            taxonIdList = [row[0] for row in taxonIdList.all()]

            # Retain taxonId if it is in the list, else 0
            taxonId = taxonId if taxonId in taxonIdList else 0

            funcResult = {"nftGroupName": None, "description": None}
            query = (
                select(ClaimQuotes.nftGroupName, ClaimQuotes.description)
                .filter(
                    ClaimQuotes.taxonId == taxonId,
                )
                .order_by(func.random())
                .limit(1)
            )
            queryResult = await session.execute(query)
            queryResult = queryResult.first()

            if not queryResult:
                loggingInstance.error(f"getClaimQuote({taxonId}): ClaimQuoteError")
                raise Exception("ClaimQuoteError")

            nftGroupName, description = queryResult

            funcResult["description"] = description
            funcResult["nftGroupName"] = nftGroupName

            (
                loggingInstance.info(f"getClaimQuote({taxonId}): {description}")
                if self.verbose
                else None
            )
            return funcResult
