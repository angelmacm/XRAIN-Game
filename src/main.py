from database.db import BattleRoyaleDB
from components.config import dbConfig, botConfig
from components.logging import loggingInstance


from interactions import Intents, Client, listen, InteractionContext # General discord Interactions import
from interactions import slash_command, slash_str_option # Slash command imports
from interactions import Embed, StringSelectMenu, ComponentContext, component_callback, StringSelectOption
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
    embed = Embed(title="Chosen NFT",
                  description=f"{chosenNFT['label']}\n\n[View NFT Details](https://xrp.cafe/nft/{chosenNFT['tokenId']})")
    embed.add_image(chosenNFT['nftLink'])
    await ctx.edit(content=f"", components=[], embed=embed)
    
    loggingInstance.info(f"NFT Choice: {chosenNFT['label']}")
    
        
if __name__ == "__main__":
    client.start()