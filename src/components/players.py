class Players:
    def __init__(self, xrpId, wager, name, discordId, battleWins, tokenId, boosts:int = 0, xrainPower:int = 0, nftLink = ""):
        self.xrpId = xrpId
        self.wager = wager
        self.name = name
        self.discordId = discordId
        self.alive = True
        self.reviveNum = 0
        self.battleWins = battleWins
        self.NFT = tokenId
        self.boosts = boosts
        self.xrainPower = xrainPower
        self.kills = 0
        self.nftLink = nftLink
    
    def kill(self):
        self.alive = False
        
    def revive(self):
        self.alive = True
        self.reviveNum += 1
        
    def addKill(self):
        self.kills += 1