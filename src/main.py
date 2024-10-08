from database.db import BattleRoyaleDB
from components.config import dbConfig, botConfig, coinsConfig, gameConfig, xrplConfig
from components.logging import loggingInstance
from components.xummClient import XummClient, XummGetPayloadResponse
from components.xrplCommands import XRPClient

from components.battles import Battle
from components.players import Players

from interactions import Intents, Client, listen, InteractionContext, BaseMessage # General discord Interactions import
from interactions import slash_command, Button, slash_int_option, File, ActionRow # Slash command imports
from interactions import Embed, StringSelectMenu, StringSelectOption, SlashCommandChoice, User, ButtonStyle
from interactions.api.events import Component

# Other imports
from datetime import datetime
from random import randint, random
from asyncio import sleep, gather, CancelledError
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

xrplInstance = XRPClient(xrplConfig)

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

async def verifyAddress(discordId):
    xrpId = await dbInstance.checkDiscordId(discordId=discordId)
    return xrpId
        
async def waitForPayment(ctx: InteractionContext, uuid) -> bool | XummGetPayloadResponse:
    status = xummInstance.checkStatus(uuid)
    maxWait = 120
    currentWait = 0
    try:
        while status.hex is None:
            if maxWait <= currentWait:
                raise Exception("PaymentTimeout")                
            
            status = xummInstance.checkStatus(uuid)
            await sleep(3)
            currentWait += 3
            
        if status.hex == '':
            raise Exception('PaymentRejected')

        return status
    
    except Exception as e:
        embed = Embed(title="Transaction Failed",
                      timestamp=datetime.now())
        if str(e) == 'PaymentTimeout':
            embed.description = f"Transaction timeout, please complete the process within {maxWait}s"
            
        if str(e) == 'PaymentRejected':
            embed.description = f"Transaction rejected, please try again"
            
        else:
            embed.description = f"{e} error occurred"
            
        await ctx.edit(embed=embed)
        
        return False
            

# Battle Verify Command:
@slash_command(
        name="battle-verify",
        description="Verify if you are ready for the battle")
async def register(ctx:InteractionContext):
    await ctx.defer(ephemeral=True, suppress_error=True)
    signInData = xummInstance.createSignIn()
            
    embed = Embed(title='Verify your wallet',
                    description="Scan the QR Code to verify your wallet",
                    color="#3052ff",
                    url=signInData.next.always)
    embed.add_image(image=signInData.refs.qr_png)

    await ctx.send(embed=embed, ephemeral=True)
    
    status = await waitForPayment(ctx, signInData.uuid)
    if not status:
        return False
    
    await dbInstance.setDiscordId(ctx.author.id, status.account)
    
    await ctx.send("You have verified your XRP Wallet", ephemeral=True)

# Choose NFT Command:
@slash_command(
        name="choose-nft",
        description="Choose which NFT you want to use for the battle"
        )
async def chooseNft(ctx: InteractionContext):
    await ctx.defer(ephemeral=True, suppress_error=True) # Defer the response to wait for the function to run.
    loggingInstance.info(f"/choose-nft called by {ctx.author.display_name}")  if botVerbosity else None
    
    try:
        xrpId = await verifyAddress(ctx.author_id)
        
        if not xrpId:
            return
    except Exception as e:
        if str(e) == "DiscordIdNotFound":
            await ctx.send("XRP Wallet not found, use /battle-verify to verify your XRP Wallet")
            return
    
    try:
        nftOptions = await dbInstance.getNFTOption(ctx.author.id)
    except Exception as e:
        loggingInstance.error(f"xrpIdNotFound")  if botVerbosity else None
        await ctx.send("xrpIdNotFound", ephemeral=True)
        return
    
    nftMenu = StringSelectMenu(
        [StringSelectOption(label=key, value=key) for key in nftOptions.keys()],
        custom_id='groupSelection',
        placeholder="NFT Group Selection",
    )
    
    groupMenu = StringSelectMenu(
        [StringSelectOption(label='placeholder', value='placeholder')],
        custom_id='nftSelection',
        placeholder="NFT Selection",
        disabled=True
    )
    
    selectOne = ActionRow()
    selectTwo = ActionRow()
    selectOne.add_component(nftMenu)
    selectTwo.add_component(groupMenu)
    latestMessage = await ctx.send("Select NFT", components=[selectOne, selectTwo], ephemeral=True)
    
    previous_button = Button(style=ButtonStyle.GREEN, label="Previous", custom_id="previous", disabled=True)
    next_button = Button(style=ButtonStyle.GREEN, label="Next", custom_id="next", disabled=True)
    pagination_row = ActionRow()
    pagination_row.add_component(previous_button)
    pagination_row.add_component(next_button)
     
    def check(component: Component):
        return component.ctx.author_id == ctx.author.id
    
    async def wait_component(components, ctx: InteractionContext) -> Component | None:
        try:
            component_result: Component = await client.wait_for_component(components=components, check=check, timeout=900)
            await component_result.ctx.defer(edit_origin=True)
            return component_result
        except Exception as e:
            loggingInstance.info(f"{e} error occurred")
            await ctx.edit(content=f"Timed out in selecting option", components={})
            return None
    
    page = 0
    items_per_page = 25
    
    def update_group_menu_options(nftOptions, chosen_group, page):
        start = page * items_per_page
        end = start + items_per_page
        group_options = [
            StringSelectOption(label=item['label'], value=f"{start+index},{chosen_group}")
            for index, item in enumerate(nftOptions[chosen_group][start:end])
        ]
        return group_options
    
    component_result: Component = await wait_component([nftMenu, groupMenu, pagination_row], ctx)

    while component_result:
        if component_result.ctx.custom_id == 'groupSelection':
            chosen_group = component_result.ctx.values[0]
            groupMenu.options = update_group_menu_options(nftOptions, chosen_group, page)
            groupMenu.disabled = False
            nftMenu.placeholder = chosen_group
            selectOne = ActionRow()
            selectTwo = ActionRow()
            selectOne.add_component(nftMenu)
            selectTwo.add_component(groupMenu)
            previous_button.disabled = True
            next_button.disabled = len(nftOptions[chosen_group]) <= items_per_page
            components = [selectOne, selectTwo]
            components.append(pagination_row) if not next_button.disabled else None
            latestMessage = await ctx.edit(content=f"Select NFT from {chosen_group} group", components=components)
        elif component_result.ctx.custom_id == 'nftSelection':
            chosen_group = None
            for option in nftMenu.options:
                index, groupName = component_result.ctx.values[0].split(",")
                if option.value == groupName:
                    chosen_group = option.value
                    break

            if not chosen_group:
                await ctx.send("Error: Selected group not found", ephemeral=True)
                return

            chosen_nft = nftOptions[chosen_group][int(component_result.ctx.values[0].split(",")[0])]
            await dbInstance.setNFT(
                xrpId=xrpId,
                token=chosen_nft['tokenId'],
                nftLink=chosen_nft['nftLink'],
                xrainPower=chosen_nft['totalXrain'],
                taxonId=chosen_nft['taxonId'],
                groupName=chosen_group,
                battleWinArg=chosen_nft['battleWins']
            )
            embed = Embed(
                title="Chosen NFT",
                description=f"{chosen_nft['label']}\n\n[View NFT Details](https://xrp.cafe/nft/{chosen_nft['tokenId']})"
            )
            embed.set_image(url=chosen_nft['nftLink'])
            latestMessage = await ctx.edit(content="", components=[], embed=embed)
            loggingInstance.info(f"NFT Choice: {chosen_nft['label']}") if botVerbosity else None
            return
        elif component_result.ctx.custom_id == 'previous':
            page -= 1
            groupMenu.options = update_group_menu_options(nftOptions, chosen_group, page)
            groupMenu.disabled = False
            previous_button.disabled = page == 0
            next_button.disabled = False
            
            components = latestMessage.components[0:-2]
            specificNFT = ActionRow()
            specificNFT.add_component(groupMenu)
            components.append(specificNFT)
            pagination_row = ActionRow()
            pagination_row.add_component(previous_button)
            pagination_row.add_component(next_button)
            components.append(pagination_row)
            latestMessage = await ctx.edit(content=f"Select NFT from {chosen_group} group", components=components)
        
        elif component_result.ctx.custom_id == 'next':
            page += 1
            groupMenu.options = update_group_menu_options(nftOptions, chosen_group, page)
            
            groupMenu.disabled = False
            previous_button.disabled = False
            next_button.disabled = (page + 1) * items_per_page >= len(nftOptions[chosen_group])
            
            components = latestMessage.components[0:-2]
            specificNFT = ActionRow()
            specificNFT.add_component(groupMenu)
            components.append(specificNFT)
            pagination_row = ActionRow()
            pagination_row.add_component(previous_button)
            pagination_row.add_component(next_button)
            components.append(pagination_row)
            latestMessage = await ctx.edit(content=f"Select NFT from {chosen_group} group", components=components)
        
        component_result = await wait_component([nftMenu, groupMenu, pagination_row], ctx)
    
@slash_command(
        name="fill-xrain-reserve",
        description="Buy plays for the battle royale!",
        options= [
            slash_int_option(
                description= "Number of XRAIN you want to wager",
                name='xrain-amount',
                choices=[SlashCommandChoice(name='100', value=100),
                         SlashCommandChoice(name='250', value=250),
                         SlashCommandChoice(name='500', value=500),
                         SlashCommandChoice(name='1000', value=1000),
                         SlashCommandChoice(name='3000', value=3000),
                         SlashCommandChoice(name='5000', value=5000),
                         ],
                required=True
            )
        ])
async def fillXrainReserves(ctx: InteractionContext):
    await ctx.defer(ephemeral=True)
    loggingInstance.info(f"/fill-xrain-reserve called by {ctx.author.display_name}") if botVerbosity else None
    
    try:
        await verifyAddress(ctx.author_id)
    except Exception as e:
        if str(e) == "DiscordIdNotFound":
            await ctx.edit(content="XRP Wallet not found, use /battle-verify to verify your XRP Wallet")
            return
    
    discordId = ctx.author_id
    fillAmount = ctx.kwargs['xrain-amount']
    
    # XUMM SDK QR CODE GENERATE AND VALIDATE HERE
    loggingInstance.info(f"Creating payment request for {fillAmount} XRAINS") if botVerbosity else None
    paymentRequest = xummInstance.createXrainPaymentRequest(
        'ravqmjBaeJ59dw9uyHZhJ4UBXQBfHCeHo',
        amount= fillAmount,
        coinHex= coinsConfig['XRAIN']
    )
    loggingInstance.info(f"Payment ID: {paymentRequest.uuid}") if botVerbosity else None
    
    embed = Embed(title=f"Refill {fillAmount} XRAIN to your Battle Royale reserves",
                  description= f"Pay **__{fillAmount}__** XRAIN to refill your reserves",
                  color="#3052ff",
                  url=paymentRequest.next.always)
    
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
    loggingInstance.info(f"/fill-xrain-reserve called of {ctx.author.display_name} success") if botVerbosity else None
    
@slash_command(
        name="buy-boost",
        description="Buy boosts for the battle royale!",
        options= [
            slash_int_option(
                description= "Number of XRAIN you want to wager",
                name='boost-amount',
                choices=[SlashCommandChoice(name='3 Boost = 150 XRAIN', value=3),
                         SlashCommandChoice(name='10 Boost = 500 XRAIN', value=10),
                         SlashCommandChoice(name='20 Boost = 1000 XRAIN', value=20),
                         SlashCommandChoice(name='30 Boost = 1500 XRAIN', value=30),
                         SlashCommandChoice(name='50 Boost = 2500 XRAIN', value=50),
                         ],
                required=True
            )
        ])
async def buyBoosts(ctx: InteractionContext):
    await ctx.defer(ephemeral=True)
    
    loggingInstance.info(f"/buy-boost called by {ctx.author.display_name}") if botVerbosity else None
    
    try:
        await verifyAddress(ctx.author_id)
    except Exception as e:
        if str(e) == "DiscordIdNotFound":
            await ctx.edit(content="XRP Wallet not found, use /battle-verify to verify your XRP Wallet")
            return
    
    authorId = ctx.author_id
    boostAmount = ctx.kwargs['boost-amount']
    xrainPayment = 50 * boostAmount

    loggingInstance.info(f"Creating payment request for {xrainPayment} XRAIN") if botVerbosity else None
    paymentRequest = xummInstance.createXrainPaymentRequest(
        'ravqmjBaeJ59dw9uyHZhJ4UBXQBfHCeHo',
        amount= xrainPayment,
        coinHex= coinsConfig['XRAIN']
    )
    loggingInstance.info(f"Payment ID: {paymentRequest.uuid}") if botVerbosity else None
    
    embed = Embed(title=f"Refill {xrainPayment} XRAIN to your Battle Royale reserves",
                  description= f"Pay **__{xrainPayment}__** XRAIN to buy {boostAmount} boosts",
                  color="#3052ff",
                  url=paymentRequest.next.always)
    
    embed.add_image(image=paymentRequest.refs.qr_png)
    
    await ctx.send(embed=embed)
    
    paymentSuccess = await waitForPayment(ctx, paymentRequest.uuid)
    
    if not paymentSuccess:
        return
    
    await dbInstance.addBoost(uniqueId=authorId, boost=boostAmount)
    
    embed = Embed(title="Transaction Success",
                          description=f"Successfully bought {boostAmount} boosts",
                          timestamp=datetime.now())
        
    await ctx.edit(embed=embed)
    
@slash_command(
        name="nft",
        description="See the NFT that you are using for the battle royale!")
async def getNFT(ctx: InteractionContext):
    await ctx.defer(ephemeral=True, suppress_error=True)
    
    loggingInstance.info(f"/nft called by {ctx.author.display_name}") if botVerbosity else None
    
    try:
        xrpId = await verifyAddress(ctx.author_id)
        if not xrpId:
            return
    except Exception as e:
        if str(e) == 'DiscordIdNotFound':
            await ctx.send("XRP Wallet not found, use /battle-verify to verify your XRP Wallet", ephemeral=True)
            return
        await ctx.send(f"{e} error occurred", ephemeral=True)
        return
    
    await ctx.send("Checking your xrpId settings", ephemeral=True)
    try:
        nftInfo = await dbInstance.getNFTInfo(xrpId)
    except:
        await ctx.send("xrpIdNotFound", ephemeral=True)
        loggingInstance.info(f"xrpIdNotFound") if botVerbosity else None
        return
    
    if nftInfo['nftToken'] == "" or nftInfo['nftLink'] == "":
        await ctx.edit(content="Battle NFT not found, use /choose-nft to choose your Battle NFT")
        return
    
    embed = Embed(title=f"Battle NFT: {nftInfo['nftGroupName']} ***{nftInfo['nftToken'][-6:]}**",
                  url=f"https://xrp.cafe/nft/{nftInfo['nftToken']}",
                  description=f"{ctx.author.display_name} won **__{nftInfo['battleWins']}__** times! :crossed_swords:",
                  color=await randomColor())

    embed.add_field(name="Battle Royale Rank",
                    value= nftInfo['battleRank'],
                    inline=True)
    embed.add_field(name="XRAIN power",
                    value=str(nftInfo['xrainPower']),
                    inline=True)
    embed.add_field(name="Booster Multiplier",
                    value=f"{100 if int(nftInfo['reserveBoosts']) > 0 else 0 }%\nEffective XRAIN Power:\n{int(nftInfo['xrainPower'])*(2 if int(nftInfo['reserveBoosts']) > 0 else 1)}",
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

    embed.set_image(url=nftInfo['nftLink'])

    await ctx.send(embed=embed, ephemeral=False)
    loggingInstance.info(f"/nft called by {ctx.author.display_name} success") if botVerbosity else None
    
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
                ],
                required=True
            ),
        ])
async def battleRoyale(ctx: InteractionContext):
    await ctx.defer()  
    loggingInstance.info(f"/br called by {ctx.author.display_name}") if botVerbosity else None
    
    wager = ctx.kwargs['wager']
    embed = Embed(title="XRPL Rainforest Battle Royale!!",
                      description=f"The Battle Royale Horn has sounded by XRPLRainforest Warriors!!\n\nClick the emoji below to answer the call for **__{wager} XRAIN.__**",
                      timestamp=datetime.now())

    file = File('./src/images/XRAIN Battle.png', file_name="xrain_battle.png")
    
    embed.add_image("attachment://xrain_battle.png")

    embed.set_footer(text=f"Battle in {ctx.args[0]}s")

    battleCall: BaseMessage = await ctx.send(embed=embed, file=file)
    
    await battleCall.add_reaction(":crossed_swords:")
    
    loggingInstance.info(f"Sleeping for {ctx.args[0]}") if botVerbosity else None
    await sleep(ctx.args[0])
    
    playersReactor = await battleCall.fetch_reaction(':crossed_swords:')
    loggingInstance.info(f"{len(playersReactor)} players attempted to join") if botVerbosity else None
    playersJoined = [users for users in playersReactor if users.id != client.app.id]
    
    battleInstance = Battle(dbInstance)
    
    boostQuotes = ""
    
    async def savePlayers(ctx: InteractionContext, users: User = None, wager = 0, npc = False):
        try:
            if not npc:
                playerInfo = await dbInstance.getNFTInfo(users.id)
                
                if playerInfo['nftLink'] == '':
                    raise Exception("BattleNFTNotFound")
                
                if playerInfo['reserveXrain'] < wager:
                    raise Exception("insufficientCredits")             
                await dbInstance.placeWager(playerInfo['xrpId'], wager)
            else:
                playerInfo = await dbInstance.getNFTInfo(npc=npc)
        except Exception as e:
            match str(e):
                case "xrpIdNotFound":
                    loggingInstance.error(f"xrpIdNotFound") if botVerbosity else None
                    await ctx.channel.send(f"{users.mention}, not found. Please verify your wallet first via /battle-verify") if users is not None else None
                case "insufficientCredits":
                    loggingInstance.error(f"{users.id} insufficient credit") if botVerbosity else None
                    await ctx.channel.send(f"Insufficient  credits for {users.mention}. Please refill your XRAIN reserves") if users is not None else None
                case "BattleNFTNotFound":
                    loggingInstance.error(f"{users.id} battle nft not found") if botVerbosity else None
                    await ctx.channel.send(f"Battle NFT not found for {users.mention}. Please set your NFT via /choose-nft") if users is not None else None
            
            return None    
        
        # Check for xrain for the wager
        
        totalBoost  = int(playerInfo['xrainPower']) * (2 if int(playerInfo['reserveBoosts']) > 0 else 1)
            
        playerInstance = Players(xrpId=playerInfo['xrpId'],
                                 wager=wager,
                                 name=escapeMarkdown(users.display_name) if not npc else "XRAIN NPC Warrior",
                                 discordId=users.id if not npc else 0,
                                 boosts=playerInfo['reserveBoosts'],
                                 battleWins=playerInfo['battleWins'],
                                 tokenId=playerInfo['nftToken'],
                                 nftLink=playerInfo['nftLink'],
                                 taxonId=playerInfo['taxonId'],
                                 npc=playerInfo['npc'],
                                 mention=users.mention if not npc else None,
                                 xrainPower=totalBoost)
        
        playerInstance.addNFTImage(await fetchImage(playerInstance.nftLink))
        
        battleInstance.join(playerInstance)
        
       
    coros = [savePlayers(ctx, user, wager) for user in playersJoined]
    
    await gather(*coros)
    
    if len(battleInstance.players) == 0:
        await ctx.send("No one answered the call!")
        return
    elif len(battleInstance.players) == 1:
        loggingInstance.info(f"Lone joiner, creating NPC") if botVerbosity else None
        await savePlayers(ctx, wager=wager, npc=True)
        await ctx.channel.send("A XRAIN NPC Warrior joined!")
    
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
        loggingInstance.info(f"[Round {roundNumber}]: {battleResults['participantsNum']}/{len(battleInstance.players)} alive") if botVerbosity else None
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
        
    loggingInstance.info(f"[Round {roundNumber}]: {battleResults['participantsNum']}/{len(battleInstance.players)} alive") if botVerbosity else None
    await postRoundInfo(ctx.channel, battleResults, roundColor = roundColor)
    await randomWait()
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
    
    await dbInstance.addWin(battleResults['winner'].xrpId, battleResults['winner'].NFT, battleResults['winner'].npc)
    
    await ctx.send(embeds=[winnerImageEmbed, claimEmbed, winnerTextEmbed, statsEmbed])
    
    loggingInstance.info(f"Winner: {battleResults['winner'].mention if not battleResults['winner'].npc else "NPC"}") if botVerbosity else None
    
    if not battleResults['winner'].npc:
        loggingInstance.info(f"Sending {battleInstance.totalWager} XRAIN to {battleResults['winner'].xrpId}") if botVerbosity else None
        await xrplInstance.registerSeed(xrplConfig['seed'])
        await xrplInstance.sendCoin(address=battleResults['winner'].xrpId,
                                    value=battleInstance.totalWager,
                                    coinHex=coinsConfig['XRAIN'],
                                    memos="XRPL Rainforest Battle Royale Winner!")
    
    loggingInstance.info(f"/br success") if botVerbosity else None
        
async def prepareStats(players: list[Players]):
    minRank = gameConfig.getint('stat_best_num')
    mostKills = sorted(players, key=lambda players: players.kills, reverse=True)
    killQuotes = ""
    for player in mostKills[:minRank]:
        killQuotes += f"**{player.name}**: {player.kills}\n"
        
    mostDeaths = sorted(players, key=lambda players: players.deaths, reverse=True)
    deathQuotes = ""
    for player in mostDeaths[:minRank]:
        deathQuotes += f"**{player.name}**: {player.deaths}\n"
    
    mostRevives = sorted(players, key=lambda players: players.reviveNum, reverse=True)
    reviveQuotes = ""
    for player in mostRevives[:minRank]:
        reviveQuotes += f"**{player.name}**: {player.reviveNum}\n"
    
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
