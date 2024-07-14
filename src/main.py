from database.db import BattleRoyaleDB
from components.config import dbConfig, botConfig, coinsConfig, gameConfig
from components.logging import loggingInstance
from components.xummClient import XummClient

from components.battles import Battle
from components.players import Players

from interactions import Intents, Client, listen, InteractionContext, BaseMessage # General discord Interactions import
from interactions import slash_command, slash_str_option, slash_int_option, File # Slash command imports
from interactions import Embed, StringSelectMenu, StringSelectOption, SlashCommandChoice, User
from interactions.api.events import Component

# Other imports
from datetime import datetime
from random import randint, random
from asyncio import sleep, gather
from PIL import Image
import requests
from io import BytesIO

intents = Intents.DEFAULT | Intents.MESSAGE_CONTENT
client = Client(intents=intents, token=botConfig['token'])

# Initialize DB connection
dbInstance = BattleRoyaleDB(
    host=dbConfig['db_server'],
    dbName=dbConfig['db_name'],
    username=dbConfig['db_username'],
    password=dbConfig['db_password'],
    verbose=dbConfig.getboolean('verbose')
)

xummInstance = XummClient()

botVerbosity = botConfig.getboolean('verbose')

@listen()
async def on_ready():
    # Some function to do when the bot is ready
    loggingInstance.info(f"Discord Bot Ready!")

def escapeMarkdown(text: str) -> str:
    escapeChars = ['*', '_', '~', '`']
    for char in escapeChars:
        text = text.replace(char, f'\\{char}')
    return text

async def xummWaitForCompletion(uuid: str):
    status = xummInstance.checkStatus(uuid)
    while status.hex is None:
        status = xummInstance.checkStatus(uuid)
        await sleep(1)
    return status

async def randomColor():
    randomColorCode = str(hex(randint(0,16777215)))[2:]
    
    for _ in range(abs(len(randomColorCode)-6)):
        randomColorCode += '0'
    
    return f"#{randomColorCode}"

async def verifyAddress(ctx: InteractionContext):
    try:
        xrpId = await dbInstance.checkDiscordId(discordId=ctx.author.id)
        return xrpId
    except Exception as e:
        if str(e) != "DiscordIdNotFound":
            raise e
        else:
            signInData = xummInstance.createSignIn()
            
            embed = Embed(title='Verify your wallet',
                          description="Scan the QR Code to verify your wallet",
                          color="#3052ff")
            embed.add_image(image=signInData.refs.qr_png)

            await ctx.send(embed=embed)
            
            status = await xummWaitForCompletion(signInData.uuid)
            
            await dbInstance.setDiscordId(ctx.author.id, status.account)

async def waitForPayment(ctx: InteractionContext, uuid):
    status = xummInstance.checkStatus(uuid)
    maxWait = 120
    currentWait = 0
    try:
        while status.hex is None:
            if maxWait <= currentWait:
                raise Exception("PaymentTimeout")                
            
            status = xummInstance.checkStatus(uuid)
            await sleep(1)
            currentWait += 1
            
        if status.hex == '':
            raise Exception('PaymentRejected')

        return True
    
    except Exception as e:
        embed = Embed(title="Transaction Failed",
                      timestamp=datetime.now())
        if str(e) == 'PaymentTimeout':
            embed.description = f"Payment timeout, please complete the transaction within {maxWait}s"
            
        if str(e) == 'PaymentRejected':
            embed.description = f"Payment rejected, please try again"
            
        else:
            embed.description = f"{e} error occurred"
            
        await ctx.edit(embed=embed)
        
        return False
            

# Dailies Command:
# Parameters:
#       XRP ID: [Required] XRP Address where the users hold their NFTs and the receipient of the reward
@slash_command(
        name="choose-nft",
        description="Choose which NFT you want to use for the battle",
        options= [
            slash_str_option(
                name = "xrpid",
                description = "XRP Address that will receive the bonus reward",
                required = False
            )
        ])
async def chooseNft(ctx: InteractionContext):
    await ctx.defer(ephemeral=True, suppress_error=True) # Defer the response to wait for the function to run.
    loggingInstance.info(f"/choose-nft called by {ctx.author.display_name}")
    
    xrpId = await verifyAddress(ctx)
    
    try:
        nftOptions = await dbInstance.getNFTOption(ctx.author.id)
    except Exception as e:
        await ctx.send("xrpIdNotFound")
        return
    
    nftMenu = StringSelectMenu(
        list(nftOptions.keys()),
        custom_id='groupSelection',
        placeholder="NFT Group Selection"
    )
    
    groupMenu = StringSelectMenu(
        'placeholder',
        custom_id='nftSelection',
        placeholder="NFT Selection",
        disabled=True
    )
    
    await ctx.send("Select NFT", components=[nftMenu])
    
    def check(component: Component):
        if component.ctx.author_id == ctx.author_id:
            return True
        return False
    
    async def waitComponent(component, ctx:InteractionContext) -> Component | None:
        try:
            componentResult: Component = await client.wait_for_component(components=component, check=check, timeout=30)
            await ctx.defer(ephemeral=True, suppress_error=True)
            await componentResult.ctx.defer(edit_origin=True)
            return componentResult
        except:
            await ctx.send("Timed out in selecting option", ephemeral=True)
            
    componentResult = await waitComponent(nftMenu, ctx)
    
    loggingInstance.info(f"Valid NFT Group Choice: {type(componentResult) == Component}")
    
    if not componentResult:
        return
    
    chosenGroup = componentResult.ctx.values[0]
    # ctx.send(f"Selected {chosenGroup}", ephemeral=True)
    groupOptions = []
    index = 0
    
    for item in nftOptions[chosenGroup]:
        groupOptions.append(StringSelectOption(
            label=item['label'],
            value=index
        ))
        index += 1
        if len(groupOptions) == 25:
            break
    
    groupMenu.options = groupOptions
    groupMenu.disabled = False
        
    await ctx.edit(content=f"Select NFT from {chosenGroup} group",components=groupMenu)
    
    result = await waitComponent(groupMenu, ctx)
    
    loggingInstance.info(f"Valid NFT Choice: {type(result) == Component}")
    
    chosenNFT = int(result.ctx.values[0])
    chosenNFT = nftOptions[chosenGroup][chosenNFT]
    
    await dbInstance.setNFT(xrpId=xrpId,
                            token=chosenNFT['tokenId'],
                            nftLink=chosenNFT['nftLink'],
                            xrainPower=chosenNFT['totalXrain'],
                            taxonId=chosenNFT['taxonId'],
                            groupName=chosenGroup)
    
    embed = Embed(title="Chosen NFT",
                  description=f"{chosenNFT['label']}\n\n[View NFT Details](https://xrp.cafe/nft/{chosenNFT['tokenId']})")
    embed.add_image(chosenNFT['nftLink'])
    await ctx.edit(content=f"", components=[], embed=embed)
    
    loggingInstance.info(f"NFT Choice: {chosenNFT['label']}")
    
@slash_command(
        name="fill-xrain-reserve",
        description="Buy plays for the battle royale!",
        options= [
            slash_int_option(
                description= "Number of XRAIN you want to wager",
                name='xrain-amount',
                choices=[SlashCommandChoice(name='25', value=25),
                         SlashCommandChoice(name='50', value=50),
                         SlashCommandChoice(name='100', value=100),
                         SlashCommandChoice(name='250', value=250),
                         SlashCommandChoice(name='500', value=500),
                         SlashCommandChoice(name='1000', value=1000),
                         ],
                required=True
            )
        ])
async def fillXrainReserves(ctx: InteractionContext):
    await ctx.defer(ephemeral=True)
    discordId = ctx.author_id
    fillAmount = ctx.kwargs['xrain-amount']
    
    # XUMM SDK QR CODE GENERATE AND VALIDATE HERE
    paymentRequest = xummInstance.createXrainPaymentRequest(
        'ravqmjBaeJ59dw9uyHZhJ4UBXQBfHCeHo',
        amount= fillAmount,
        coinHex= coinsConfig['XRAIN']
    )
    
    embed = Embed(title=f"Refill {fillAmount} XRAIN to your Battle Royale reserves",
                  description= f"Pay **__{fillAmount}__** XRAIN to refill your reserves",
                  color="#3052ff")
    
    embed.add_image(image=paymentRequest.refs.qr_png)
    
    await ctx.send(embed=embed)
    
    paymentSuccess = await waitForPayment(ctx, paymentRequest.uuid)
    
    if not paymentSuccess:
        return
    
    await dbInstance.addXrain(discordId, fillAmount)
    
    embed = Embed(title="Transaction Success",
                          description=f"Successfully filled {fillAmount} to your reserves",
                          timestamp=datetime.now())
        
    await ctx.edit(embed=embed)
    
@slash_command(
        name="buy-boost",
        description="Buy boosts for the battle royale!",
        options= [
            slash_int_option(
                description= "Number of XRAIN you want to wager",
                name='boost-amount',
                choices=[SlashCommandChoice(name='3', value=3),
                         SlashCommandChoice(name='10', value=10),
                         SlashCommandChoice(name='20', value=20),
                         ],
                required=True
            )
        ])
async def buyBoosts(ctx: InteractionContext):
    await ctx.defer(ephemeral=True)
    authorId = ctx.author_id
    boostAmount = ctx.kwargs['boost-amount']
    xrainPayment = 50 * boostAmount

    paymentRequest = xummInstance.createXrainPaymentRequest(
        'ravqmjBaeJ59dw9uyHZhJ4UBXQBfHCeHo',
        amount= xrainPayment,
        coinHex= coinsConfig['XRAIN']
    )
    
    embed = Embed(title=f"Refill {xrainPayment} XRAIN to your Battle Royale reserves",
                  description= f"Pay **__{xrainPayment}__** XRAIN to buy {boostAmount} boosts",
                  color="#3052ff")
    
    embed.add_image(image=paymentRequest.refs.qr_png)
    
    await ctx.send(embed=embed)
    
    paymentSuccess = await waitForPayment(ctx, paymentRequest.uuid)
    
    if not paymentSuccess:
        return
    
    await dbInstance.addBoost(uniqueId=authorId, boost=boostAmount)
    
    await ctx.send(f"You have successfully bought {boostAmount} boosts! Now pay {xrainPayment} XRAIN")
    
@slash_command(
        name="nft",
        description="See the NFT that you are using for the battle royale!",
        options= [
            slash_str_option(
                name = "xrpid",
                description = "XRP Address",
                required = True
            )
        ])
async def getNFT(ctx: InteractionContext):
    await ctx.defer(ephemeral=False)
    
    xrpId = ctx.kwargs['xrpid']
    try:
        nftInfo = await dbInstance.getNFTInfo(xrpId)
    except:
        ctx.send("xrpIdNotFound")
        return
    
    embed = Embed(title=f"Battle NFT: {nftInfo['nftGroupName']} ***{nftInfo['nftToken'][-6:]}**",
                  url=f"https://xrp.cafe/nft/{nftInfo['nftToken']}",
                  description=f"You've won **__{nftInfo['battleWins']}__** times!",
                  color=await randomColor())

    embed.add_field(name="XRAIN power",
                    value=str(nftInfo['xrainPower']),
                    inline=True)
    embed.add_field(name="Booster Multiplier",
                    value=f"100%\nEffective XRAIN Power:\n{int(nftInfo['xrainPower'])*2}",
                    inline=True)
    embed.add_field(name="Active Booster",
                    value="Yes" if int(nftInfo['reserveBoosts']) > 0 else "No",
                    inline=True)
    embed.add_field(name="Boosts Remaining",
                    value=str(nftInfo['reserveBoosts']),
                    inline=True)
    embed.add_field(name="XRAIN Reserves",
                    value=str(nftInfo['reserveXrain']),
                    inline=True)
    embed.add_field(name="Battle Royale Rank",
                    value= nftInfo['battleRank'],
                    inline=True)

    embed.set_image(url=nftInfo['nftLink'])

    await ctx.send(embed=embed)
    
@slash_command(
        name="br",
        description="BATTLE IT OUT!!",
        options=[
            slash_int_option(
                description="Waiting time before the game starts",
                name="wait-time",
                choices=[
                    SlashCommandChoice(name="30s", value=30),
                    SlashCommandChoice(name="1 min", value=60),
                    SlashCommandChoice(name="2 min", value=120),
                    SlashCommandChoice(name="3 min", value=180),
                ],
                required=True
            ),
            slash_int_option(
                description="Amount of XRAIN to wager per player",
                name="wager",
                choices=[
                    SlashCommandChoice(name="25", value=25),
                    SlashCommandChoice(name="50", value=50),
                    SlashCommandChoice(name="100", value=100),
                    SlashCommandChoice(name="250", value=250),
                ],
                required=True
            ),
        ])
async def battleRoyale(ctx: InteractionContext):
    await ctx.defer()
    wager = ctx.kwargs['wager']
    loggingInstance.info(f"/br called by {ctx.author.display_name}") if botVerbosity else None
    embed = Embed(title="XRPL Rainforest Battle Royale!!",
                      description=f"The Battle Royale Horn has sounded by XRPLRainforest Warriors!!\n\nClick the emoji below to answer the call for **__{wager} XRAIN.__**",
                      timestamp=datetime.now())

    file = File('./src/images/XRAIN Battle.png', file_name="xrain_battle.png")
    
    embed.add_image("attachment://xrain_battle.png")

    embed.set_footer(text=f"Battle in {ctx.args[0]}s")

    battleCall: BaseMessage = await ctx.send(embed=embed, file=file)
    
    await battleCall.add_reaction(":crossed_swords:")
    
    await sleep(ctx.args[0])
    
    playersReactor = await battleCall.fetch_reaction(':crossed_swords:')
    playersJoined = [users for users in playersReactor if users.id != client.app.id]
    
    battleInstance = Battle(dbInstance)
    
    boostQuotes = ""
    
    async def savePlayers(ctx: InteractionContext, users: User = None, wager = 0, npc = False):
        try:
            if not npc:
                playerInfo = await dbInstance.getNFTInfo(users.id)
                if playerInfo['reserveXrain'] < wager:
                    raise Exception("insufficientCredits")             
                await dbInstance.placeWager(playerInfo['xrpId'], wager)
            else:
                playerInfo = await dbInstance.getNFTInfo(npc=npc)
        except Exception as e:
            match str(e):
                case "xrpIdNotFound":
                    await ctx.channel.send(f"{users.mention}, not found. Please verify your wallet first") if users is not None else None
                case "insufficientCredits":
                    await ctx.channel.send(f"Insufficient  credits for {users.mention}. Please refill your XRAIN reserves") if users is not None else None
            return None    
        
        # Check for xrain for the wager
            
        playerInstance = Players(xrpId=playerInfo['xrpId'],
                                 wager=wager,
                                 name=escapeMarkdown(users.display_name) if not npc else "XRPL Rainforest Warrior",
                                 discordId=users.id if not npc else 0,
                                 boosts=playerInfo['reserveBoosts'],
                                 battleWins=playerInfo['battleWins'],
                                 tokenId=playerInfo['nftToken'],
                                 nftLink=playerInfo['nftLink'],
                                 taxonId=playerInfo['taxonId'],
                                 npc=playerInfo['npc'],
                                 mention=users.mention if not npc else None)
        
        playerInstance.addNFTImage(await fetchImage(playerInstance.nftLink))
        
        battleInstance.join(playerInstance)
        
       
    coros = [savePlayers(ctx, user, wager) for user in playersJoined]
    
    await gather(*coros)
    
    if len(battleInstance.players) == 0:
        await ctx.send("No one answered the call!")
        return
    elif len(battleInstance.players) == 1:
        await savePlayers(ctx, wager=wager, npc=True)
        await ctx.channel.send("A XRPL Rainforest Warrior joined!")
    
    for player in battleInstance.players:
        if player is None:
            continue 
        
        if player.boosts > 0:
            boostQuotes += f"**{player.mention if player.mention is not None else player.name}** is **100% boosted** and ready!\n"
            if not player.npc:
                await dbInstance.claimBoost(player.xrpId)
        else:
            boostQuotes += f"**{player.mention if player.mention is not None else player.name}** is ready for the battle\n"
    
    await ctx.send(boostQuotes)
    roundColor = await randomColor()
    roundNumber = 1
    await preRoundInfo(channel=ctx,
                       playerList=battleInstance.players,
                       roundNumber=roundNumber,
                       participantsNum=len(battleInstance.currentAlive),
                       deadNum=len(battleInstance.currentDead),
                       roundColor = roundColor)
        
    battleResults = await battleInstance.battle()
    
    async def randomWait():
        waitTime = max(random() * gameConfig.getfloat('max_wait'), gameConfig.getfloat('min_wait'))
        await sleep(waitTime)
    
    while battleResults['winner'] is None:
        await randomWait()
        
        await postRoundInfo(ctx.channel, battleResults, roundColor = roundColor)
        roundNumber += 1
        roundColor = await randomColor()
        await preRoundInfo(channel=ctx.channel,
                           playerList=battleResults['alive'],
                           roundNumber=roundNumber,
                           participantsNum=battleResults['participantsNum'],
                           deadNum=battleResults['deadNum'],
                           roundColor = roundColor)
        battleResults = await battleInstance.battle()
        await randomWait()
    
    await postRoundInfo(ctx.channel, battleResults, roundColor = roundColor)
    mostKills, mostDeaths, mostRevives = await prepareStats(battleInstance.players)
    
    winnerEmbedColor = await randomColor()
    
    winnerImageEmbed = Embed(title="XRPLRainforest Battle Royale Winner", color=winnerEmbedColor)
    winnerImageEmbed.set_image(battleResults['winner'].nftLink)
    
    winnerDescription = f"Congratulations **{battleResults['winner'].mention if not battleResults['winner'].npc else battleResults['winner'].name}** your NFT has won this Rainforest Battle."
    winnerDescription += f" **__{battleInstance.totalWager} XRAIN__** has been sent to you!!" if not battleResults['winner'].npc else ""
    winnerTextEmbed = Embed(description=winnerDescription, color=winnerEmbedColor)
    winnerTextEmbed.add_field(name="Kills",value=f":knife:{battleResults['winner'].kills}", inline=True)
    winnerTextEmbed.add_field(name="Revives",value=f":wing:{battleResults['winner'].reviveNum}", inline=True)
    
    claimDescription = await dbInstance.getClaimQuote(battleResults['winner'].taxonId)
    claimEmbed = Embed(description=f"**{claimDescription['description']}**", color=winnerEmbedColor)
    
    statsEmbed = Embed(title="XRPL Rainforest Battle Royale Stats!",timestamp=datetime.now(), color=winnerEmbedColor)
    statsEmbed.add_field(name="**Top 3 Kill**", value=mostKills,inline=True)
    statsEmbed.add_field(name="**Top 3 Deaths**", value=mostDeaths,inline=True)
    statsEmbed.add_field(name="**Top 3 Revives**", value=mostRevives,inline=True)
    statsEmbed.set_footer("XRPLRainforest Battle Royale")    
    
    
    await ctx.send(embeds=[winnerImageEmbed, claimEmbed, winnerTextEmbed, statsEmbed])
    loggingInstance.info(f"/br done") if botVerbosity else None
        
async def prepareStats(players: list[Players]):
    minRank = gameConfig.getint('stat_best_num')
    mostKills = sorted(players, key=lambda players: players.kills, reverse=True)
    killQuotes = ""
    for player in mostKills[:minRank]:
        killQuotes += f"{player.name}: {player.kills}\n"
        
    mostDeaths = sorted(players, key=lambda players: players.deaths, reverse=True)
    deathQuotes = ""
    for player in mostDeaths[:minRank]:
        deathQuotes += f"{player.name}: {player.deaths}\n"
    
    mostRevives = sorted(players, key=lambda players: players.reviveNum, reverse=True)
    reviveQuotes = ""
    for player in mostRevives[:minRank]:
        reviveQuotes += f"{player.name}: {player.reviveNum}\n"
    
    return killQuotes, deathQuotes, reviveQuotes
    
async def preRoundInfo(channel: InteractionContext.channel,
                       playerList: list[Players],
                       roundNumber:int,
                       participantsNum:int,
                       deadNum:int,
                       roundColor: str):
    
    descriptionText = '**Battle has started**\n\nParticipants: '
    nftLinks = []
    for player in playerList:
       descriptionText += f"{player.name}, "
       nftLinks.append(player.nftImage)
        
    preRoundEmbed = Embed(title=f"ROUND {roundNumber}",
                          description=descriptionText, color=roundColor)
    
    preRoundEmbed.add_field(name="Participants", value=participantsNum, inline=True)
    preRoundEmbed.add_field(name="Dead", value=deadNum, inline=True)
    collage = await create_collage(nftLinks)
    
    with BytesIO() as image_binary:
        collage.save(image_binary, 'PNG')
        image_binary.seek(0)
        
        file =File(image_binary, file_name="collage.png")
        preRoundEmbed.set_image(url="attachment://collage.png")
        return await channel.send(embeds=[preRoundEmbed],file=file)
    
async def postRoundInfo(channel:InteractionContext.channel,
                        battleResults,
                        roundColor):
    
    descriptionText = ""
    
    for quote in battleResults['quotes']:
        descriptionText += f"{quote}\n\n"
        
    postRoundEmbed = Embed(description=descriptionText, color=roundColor)
    
    postRoundEmbed.add_field(name="Participants", value=battleResults['participantsNum'], inline=True)
    postRoundEmbed.add_field(name="Dead", value=battleResults['deadNum'], inline=True)
    
    await channel.send(embed=postRoundEmbed )
    
        
async def fetchImage(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content))
    
async def create_collage(images):
    possibleEntryPerRow = [1,2,3,4,5]
    remainderResult = {}
    
    for entry in possibleEntryPerRow:
        currentRemainder = len(images) % entry
        
        # print(f"{currentRemainder} in {remainderResult.keys()}")
        if currentRemainder in remainderResult.keys():
            currentEntry = remainderResult[currentRemainder]
            remainderResult[currentRemainder] = currentEntry if currentEntry > entry else entry
            
            # print(f"{remainderResult[currentRemainder]} = {currentEntry} > {entry}")
            
            continue
        
        remainderResult[currentRemainder] = entry
        
    sortedResultKey = list(remainderResult.keys())
    sortedResultKey.sort()
    minKey = sortedResultKey[0]
    maxImagePerRow = remainderResult[minKey]
    if maxImagePerRow == 1 and not len(images) == 1:
        maxImagePerRow = remainderResult[sortedResultKey[1]]
    # print(remainderResult[minKey], remainderResult)
    
    # Find the minimum width and height among all images
    min_width = min(img.width for img in images)
    min_height = min(img.height for img in images)
    
    # Resize all images to the minimum width and height
    resized_images = [img.resize((min_width, min_height), Image.Resampling.LANCZOS) for img in images]
    
    # Calculate the number of rows
    rows = (len(images) + maxImagePerRow - 1) // maxImagePerRow
    
    collage_width = min_width * maxImagePerRow
    collage_height = min_height * rows
    
    collage = Image.new('RGBA', (collage_width, collage_height), (0, 0, 0, 0))
    
    for idx, img in enumerate(resized_images):
        row = idx // maxImagePerRow
        col = idx % maxImagePerRow
        x_offset = col * min_width
        y_offset = row * min_height
        collage.paste(img, (x_offset, y_offset))
    
    return collage

if __name__ == "__main__":
    client.start()