from database.models import BattleQuotes, NFTTraitList, RewardsTable, ClaimQuotes
from components.config import dbConfig
from components.logging import loggingInstance

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import update, or_, and_
from sqlalchemy.sql import func
from datetime import timedelta, datetime
from sqlalchemy.future import select


default_images = {
    "3D XChameleons": "https://drive.google.com/drive-viewer/AKGpihY9B0Ok1Q5d1q7ymGOY0l9Ctjk8URE0peEQEWYEP9HlL3qOt7aMuezmZOX6Xtc_MKbkHWrPSuyk8bdku4ezTxoJv-1VZo0q1PY=w1111-h917-rw-v1",
    "3D Bad XParrots": "https://drive.google.com/drive-viewer/AKGpihbmFwk13czo8620g1bd7BnxjwaWhL_3c_YL9mEknxsMGq7lKs-RQKJGHwcjMMlsL9GKzz1zYpNPXZF0cSW57x1PSXbwvzmUAko=w1111-h917-rw-v1",
    "3D Good XParrots": "https://drive.google.com/drive-viewer/AKGpihbmFwk13czo8620g1bd7BnxjwaWhL_3c_YL9mEknxsMGq7lKs-RQKJGHwcjMMlsL9GKzz1zYpNPXZF0cSW57x1PSXbwvzmUAko=w1111-h917-rw-v1",
    "3D XParrots": "https://drive.google.com/drive-viewer/AKGpihbmFwk13czo8620g1bd7BnxjwaWhL_3c_YL9mEknxsMGq7lKs-RQKJGHwcjMMlsL9GKzz1zYpNPXZF0cSW57x1PSXbwvzmUAko=w1111-h917-rw-v1",
    "OG Genesis Keys": "https://drive.google.com/drive-viewer/AKGpihZ8KgzCsAJ6sATShe3xwMXuWV90NqdFpQ5GeixB4vwg26u13G4Z5nNSO-alJJu4VPsp6leeOUGnwLD_YgYbqImNTrSpiNIMVSM=w1111-h917-rw-v1",
    "XRPL Moonbirds": "https://drive.google.com/drive-viewer/AKGpihYQS43mnX_m3_Z_JcedI_Pd0OoRJWTr6yp-JS3Qz-ubs9ltZTcjfjDwMcfLOSTTzr9f3oMlF6T1U5ZMtXYQOOVMqBUtPETa-wA=w1111-h917",
    "XRPLMoonbirds": "https://drive.google.com/drive-viewer/AKGpihYQS43mnX_m3_Z_JcedI_Pd0OoRJWTr6yp-JS3Qz-ubs9ltZTcjfjDwMcfLOSTTzr9f3oMlF6T1U5ZMtXYQOOVMqBUtPETa-wA=w1111-h917",
    "XChameleons": "https://drive.google.com/drive-viewer/AKGpihZNZl7cb0eP-a3jEDT19ycxxztsJBcXyd-5AsZUyKoKhsM5x9l961FuzghfzfthggvnmHF47Jytg_UsJ3TLO77klPn3ns_sIXE=w1111-h917",
    "Collab XParrots": "https://drive.google.com/drive-viewer/AKGpihZMuhRvrfffWz8hg2QbwDtOtMswvY4d38V8e_PybgHwXHok5MiGlpVYOraFXv_8rn8bUkj21kLplcBbmucFrOkhcvXgaFwu4GQ=w1111-h917",
    "XParrots": "https://drive.google.com/drive-viewer/AKGpihZMuhRvrfffWz8hg2QbwDtOtMswvY4d38V8e_PybgHwXHok5MiGlpVYOraFXv_8rn8bUkj21kLplcBbmucFrOkhcvXgaFwu4GQ=w1111-h917",
}


class BattleRoyaleDB:
    def __init__(self, host, dbName, username, password, verbose):

        #                   username          if empty, do not add :, else :password      host   dbName
        sqlLink = f"mysql+aiomysql://{username}{'' if password in ['', None] else f':{password}'}@{host}/{dbName}"
        loggingInstance.info(f"DB Link: {sqlLink}")
        self.dbEngine = create_async_engine(
            sqlLink, pool_recycle=1800, pool_pre_ping=True, pool_use_lifo=True
        )

        self.asyncSessionMaker = async_sessionmaker(
            bind=self.dbEngine, expire_on_commit=False
        )
        self.verbose = verbose

    # A temporary function that helps with the migration of battle wins from rewards to nfttraitlist
    async def syncBattleWins(self):
        try:
            loggingInstance.info("Starting battle wins synchronization...")
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    query = select(
                        RewardsTable.tokenIdBattleNFT, RewardsTable.battleWins
                    ).filter(RewardsTable.tokenIdBattleNFT != "")
                    query = await session.execute(query)
                    entries = query.all()

                    loggingInstance.info(f"Found {len(entries)} entries to sync")

                    for tokenId, battleWins in entries:
                        try:
                            await session.execute(
                                update(NFTTraitList)
                                .where(NFTTraitList.tokenId == tokenId)
                                .values(battleWins=battleWins)
                            )
                            (
                                loggingInstance.info(
                                    f"syncBattleWins({tokenId}, {battleWins}): Success"
                                )
                                if self.verbose
                                else None
                            )
                        except Exception as e:
                            loggingInstance.error(
                                f"syncBattleWins({tokenId}): Failed - {str(e)}"
                            )
                            raise

            loggingInstance.info("Battle wins synchronization completed successfully")
            print("Done")
        except Exception as e:
            loggingInstance.error(f"syncBattleWins: Critical error - {str(e)}")
            raise

    async def getNFTInfo(self, uniqueId="", npc=False):
        try:
            loggingInstance.info(
                f"getNFTInfo: Fetching info for uniqueId={uniqueId}, npc={npc}"
            )
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
                    loggingInstance.error(f"getNFTInfo({uniqueId}): xrpId not found")
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
                "nftLink": update_nftLink(nftLink, nftGroupName),
                "reserveXrain": reserveXrain,
                "reserveBoosts": reserveBoosts,
                "battleWins": battleWins,
                "battleRank": battleRank,
                "nftGroupName": nftGroupName,
                "taxonId": taxonId,
                "npc": npc,
            }
        except Exception as e:
            loggingInstance.error(f"getNFTInfo({uniqueId}): Error - {str(e)}")
            raise

    async def setNFT(
        self, xrpId, token, nftLink, xrainPower, taxonId, groupName, battleWinArg
    ):
        try:
            loggingInstance.info(
                f"setNFT: Setting NFT for xrpId={xrpId}, token={token}"
            )
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    await session.execute(
                        update(RewardsTable)
                        .where(RewardsTable.xrpId == xrpId)
                        .values(
                            tokenIdBattleNFT=token,
                            nftlink=update_nftLink(nftLink, groupName),
                            xrainPower=xrainPower,
                            taxonId=taxonId,
                            nftGroupName=groupName,
                            battleWins=battleWinArg,
                        )
                    )
                    (
                        loggingInstance.info(f"setNFT({xrpId}, {token}): Success")
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(f"setNFT({xrpId}, {token}): Error - {str(e)}")
            raise

    async def getNFTOption(self, discordID):
        try:
            loggingInstance.info(
                f"getNFTOption: Fetching NFT options for discordID={discordID}"
            )
            async with self.asyncSessionMaker() as session:
                query = (
                    select(
                        NFTTraitList.tokenId,
                        NFTTraitList.nftlink,
                        NFTTraitList.totalXRAIN,
                        NFTTraitList.nftGroupName,
                        NFTTraitList.taxonId,
                        NFTTraitList.battleWins,
                    )
                    .filter(
                        RewardsTable.discordId == discordID, NFTTraitList.nftlink != ""
                    )
                    .order_by(NFTTraitList.nftGroupName)
                    .order_by(NFTTraitList.totalXRAIN.desc())
                    .join(RewardsTable, RewardsTable.xrpId == NFTTraitList.xrpId)
                )
                queryResult = await session.execute(query)
                queryResult = queryResult.all()

                if not queryResult:
                    loggingInstance.error(f"getNFTOption({discordID}): xrpIdNotFound")
                    raise Exception("xrpIdNotFound")

            nftOptions = {}

            for row in queryResult:
                tokenId, nftLink, totalXrain, nftGroupName, taxonId, battleWins = row
                entry = {
                    "tokenId": tokenId,
                    "nftLink": update_nftLink(nftLink, nftGroupName),
                    "totalXrain": totalXrain,
                    "taxonId": taxonId,
                    "label": f"{nftGroupName} *{tokenId[-6:]} | XRAIN {totalXrain}",
                    "battleWins": battleWins,
                }

                if not len(nftGroupName):
                    continue

                if nftGroupName in nftOptions.keys():
                    nftOptions[nftGroupName].append(entry)
                else:
                    nftOptions[nftGroupName] = [entry]

                (
                    loggingInstance.info(
                        f"getNFTOption({discordID}): success - found {len(nftOptions)} groups"
                    )
                    if self.verbose
                    else None
                )

            return nftOptions
        except Exception as e:
            loggingInstance.error(f"getNFTOption({discordID}): Error - {str(e)}")
            raise

    async def addWin(self, xrpId, tokenId, isNPC):
        try:
            loggingInstance.info(
                f"addWin: Adding win for xrpId={xrpId}, tokenId={tokenId}, isNPC={isNPC}"
            )
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    await session.execute(
                        update(RewardsTable)
                        .where(RewardsTable.xrpId == xrpId)
                        .values(battleWins=RewardsTable.battleWins + 1)
                    )
                    (
                        loggingInstance.info(
                            f"Rewards addWin({xrpId, tokenId}): Success"
                        )
                        if self.verbose
                        else None
                    )
                    if not isNPC:
                        await session.execute(
                            update(NFTTraitList)
                            .where(
                                and_(
                                    NFTTraitList.tokenId == tokenId,
                                    NFTTraitList.xrpId == xrpId,
                                )
                            )
                            .values(battleWins=NFTTraitList.battleWins + 1)
                        )
                        (
                            loggingInstance.info(
                                f"NFTTraitList addWin({xrpId, tokenId}): Success"
                            )
                            if self.verbose
                            else None
                        )
        except Exception as e:
            loggingInstance.error(f"addWin({xrpId, tokenId}): Error - {str(e)}")
            raise

    async def addBoost(self, uniqueId, boost):
        try:
            loggingInstance.info(
                f"addBoost: Adding {boost} boosts for uniqueId={uniqueId}"
            )
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
                        loggingInstance.info(f"addBoost({uniqueId}, {boost}): Success")
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(f"addBoost({uniqueId}, {boost}): Error - {str(e)}")
            raise

    async def addXrain(self, uniqueId, xrain):
        try:
            loggingInstance.info(
                f"addXrain: Adding {xrain} XRAIN for uniqueId={uniqueId}"
            )
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
                        loggingInstance.info(f"addXrain({uniqueId}, {xrain}): Success")
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(f"addXrain({uniqueId}, {xrain}): Error - {str(e)}")
            raise

    async def placeWager(self, xrpId, xrain):
        try:
            loggingInstance.info(
                f"placeWager: Wagering {xrain} XRAIN for xrpId={xrpId}"
            )
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    await session.execute(
                        update(RewardsTable)
                        .where(RewardsTable.xrpId == xrpId)
                        .values(reserveXRAIN=RewardsTable.reserveXRAIN - xrain)
                    )
                    (
                        loggingInstance.info(f"placeWager({xrpId}, {xrain}): Success")
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(f"placeWager({xrpId}, {xrain}): Error - {str(e)}")
            raise

    async def claimBoost(self, xrpId):
        try:
            loggingInstance.info(f"claimBoost: Claiming boost for xrpId={xrpId}")
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    await session.execute(
                        update(RewardsTable)
                        .where(RewardsTable.xrpId == xrpId)
                        .values(reserveBoosts=RewardsTable.reserveBoosts - 1)
                    )
                    (
                        loggingInstance.info(f"claimBoost({xrpId}): Success")
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(f"claimBoost({xrpId}): Error - {str(e)}")
            raise

    async def getRandomQuote(self, revival: bool = False):
        try:
            loggingInstance.info(
                f"getRandomQuote: Fetching quote with revival={revival}"
            )
            async with self.asyncSessionMaker() as session:
                query = (
                    select(BattleQuotes.quoteType, BattleQuotes.quoteDesc)
                    .order_by(func.random())
                    .limit(1)
                )
                queryResult = await session.execute(query)
                queryResult = queryResult.first()

                if not queryResult:
                    loggingInstance.error("getRandomQuote: No quotes found in database")
                    raise Exception("RandomQuoteGetError")

                if queryResult[0] == "Revival" and not revival:
                    loggingInstance.info(
                        "getRandomQuote: Got revival quote when not requested, retrying"
                    )
                    return await self.getRandomQuote()

                loggingInstance.info(f"getRandomQuote: Success - type={queryResult[0]}")
                return queryResult
        except Exception as e:
            loggingInstance.error(f"getRandomQuote: Error - {str(e)}")
            raise

    async def checkDiscordId(self, discordId):
        try:
            loggingInstance.info(f"checkDiscordId: Checking discordId={discordId}")
            async with self.asyncSessionMaker() as session:
                query = select(RewardsTable.discordId, RewardsTable.xrpId).filter(
                    RewardsTable.discordId == discordId
                )
                queryResult = await session.execute(query)
                queryResult = queryResult.first()

                if queryResult is None:
                    loggingInstance.error(
                        f"checkDiscordId({discordId}): DiscordIdNotFound"
                    )
                    raise Exception("DiscordIdNotFound")

                (
                    loggingInstance.info(
                        f"checkDiscordId({discordId}): Success - xrpId={queryResult[1]}"
                    )
                    if self.verbose
                    else None
                )
                return queryResult[1]
        except Exception as e:
            loggingInstance.error(f"checkDiscordId({discordId}): Error - {str(e)}")
            raise

    async def setDiscordId(self, discordId, xrpId):
        try:
            loggingInstance.info(
                f"setDiscordId: Setting discordId={discordId} for xrpId={xrpId}"
            )
            async with self.asyncSessionMaker() as session:
                async with session.begin():
                    # Check if there is any xrpId that the discordId is linked to
                    checkQuery = select(
                        RewardsTable.xrpId, RewardsTable.discordId
                    ).filter(RewardsTable.discordId == discordId)

                    checkQuery = await session.execute(checkQuery)
                    checkQueryResult = checkQuery.first()

                    if checkQueryResult is not None:
                        # If there is, remove the link
                        loggingInstance.info(
                            f"setDiscordId: Discord ID found on xrpId={checkQueryResult[0]}, removing link..."
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
                        loggingInstance.info(
                            f"setDiscordId({discordId}, {xrpId}): Success"
                        )
                        if self.verbose
                        else None
                    )
        except Exception as e:
            loggingInstance.error(
                f"setDiscordId({discordId}, {xrpId}): Error - {str(e)}"
            )
            raise

    async def getClaimQuote(self, taxonId) -> dict:
        try:
            loggingInstance.info(
                f"getClaimQuote: Fetching claim quote for taxonId={taxonId}"
            )
            async with self.asyncSessionMaker() as session:
                # Query the rows of taxonId
                query = select(ClaimQuotes.taxonId).group_by(ClaimQuotes.taxonId)
                taxonIdList = await session.execute(query)

                # Get, parse, and put them into a list
                taxonIdList = [row[0] for row in taxonIdList.all()]
                loggingInstance.info(
                    f"getClaimQuote: Found {len(taxonIdList)} unique taxonIds"
                )

                # Retain taxonId if it is in the list, else 0
                originalTaxonId = taxonId
                taxonId = taxonId if taxonId in taxonIdList else 0
                if originalTaxonId != taxonId:
                    loggingInstance.info(
                        f"getClaimQuote: taxonId {originalTaxonId} not found, using default (0)"
                    )

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
                    loggingInstance.error(
                        f"getClaimQuote({taxonId}): ClaimQuoteError - No quotes found"
                    )
                    raise Exception("ClaimQuoteError")

                nftGroupName, description = queryResult

                funcResult["description"] = description
                funcResult["nftGroupName"] = nftGroupName

                (
                    loggingInstance.info(
                        f"getClaimQuote({taxonId}): Success - {nftGroupName}"
                    )
                    if self.verbose
                    else None
                )
                return funcResult
        except Exception as e:
            loggingInstance.error(f"getClaimQuote({taxonId}): Error - {str(e)}")
            raise

    def get_default_nftLink(self, nftGroupName):
        placeholder_image = default_images.get(nftGroupName)
        if placeholder_image is None:
            loggingInstance.error(
                f"get_default_nftLink: No placeholder image available for group={nftGroupName}"
            )
            raise ValueError("No NFT link image available.")
        loggingInstance.info(
            f"get_default_nftLink: Using placeholder for {nftGroupName}"
        )
        return placeholder_image


def update_nftLink(nftLink, nftGroupName=None):
    if not nftLink:
        placeholder_image = default_images.get(nftGroupName)
        if placeholder_image is None:
            raise ValueError("No NFT link image available.")
        return placeholder_image
    if not isinstance(nftLink, str):
        return nftLink
    if "ipfs.bithomp.com" in nftLink:
        return nftLink
    if (
        ".ipfs.w3s.link" in nftLink
        or nftLink.startswith("https://ipfs")
        or "ipfs://" in nftLink
    ):
        return nftLink.replace(".ipfs.w3s.link", "").replace(
            "https://", "https://ipfs.bithomp.com/image/"
        )
    return nftLink
