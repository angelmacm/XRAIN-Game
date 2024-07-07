from database.db import BattleRoyaleDB
from components.config import dbConfig, botConfig
from components.logging import loggingInstance


from interactions import Intents, Client, listen, InteractionContext # General discord Interactions import
from interactions import slash_command, slash_str_option, slash_int_option # Slash command imports
from interactions import Embed, StringSelectMenu, ComponentContext, component_callback, StringSelectOption, SlashCommandChoice
from interactions.api.events import Component

# Other imports
from datetime import datetime

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


botVerbosity = botConfig.getboolean('verbose')

@listen()
async def on_ready():
    # Some function to do when the bot is ready
    loggingInstance.info(f"Discord Bot Ready!")

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
                required = True
            )
        ])
async def chooseNft(ctx: InteractionContext):
    await ctx.defer(ephemeral=True, suppress_error=True) # Defer the response to wait for the function to run.
    loggingInstance.info(f"/choose-nft called by {ctx.author.display_name}")
    nftOptions = await dbInstance.getNFTOption(ctx.args[0])
    
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
    
    await dbInstance.setNFT(xrpId=ctx.args[0],
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
            slash_str_option(
                name = "xrpid",
                description = "XRP Address that will receive the bonus reward",
                required = True
            ),
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
async def buyPlays(ctx: InteractionContext):
    await ctx.defer(ephemeral=True)
    xrpId = ctx.kwargs['xrpid']
    wagerAmount = ctx.kwargs['xrain-amount']
    
    # XUMM SDK QR CODE GENERATE AND VALIDATE HERE
    
    await ctx.send(f"You have successfully filled your XRAIN Reserves for {wagerAmount}")
    
@slash_command(
        name="buy-boost",
        description="Buy boosts for the battle royale!",
        options= [
            slash_str_option(
                name = "xrpid",
                description = "XRP Address that will receive the bonus reward",
                required = True
            ),
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
    xrpId = ctx.kwargs['xrpid']
    boostAmount = ctx.kwargs['boost-amount']
    xrainPayment = 50 * boostAmount
    

    # XUMM SDK QR CODE GENERATE AND VALIDATE HERE
    
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
    await ctx.defer(ephemeral=True)
    
    xrpId = ctx.kwargs['xrpid']
    nftInfo = await dbInstance.getNFTInfo(xrpId)
    
    embed = Embed(title="Current NFT",
                      description=f"Your chosen NFT is **__[*{nftInfo['nftToken'][-6:]}](https://xrp.cafe/nft/{nftInfo['nftToken']})__**")

    embed.add_field(name="Base power",
                    value=str(nftInfo['xrainPower']),
                    inline=True)
    embed.add_field(name="Booster Multiplier",
                    value=f"0.5\nEffective Power:\n{int(nftInfo['xrainPower'])*1.5}",
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

    await ctx.send(embed=embed)
    

if __name__ == "__main__":
    client.start()