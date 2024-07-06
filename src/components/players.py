class Players:
    def __init__(self, xrpId, wager, name, discordId, battleWins):
        self.xrpId = xrpId
        self.wager = wager
        self.name = name
        self.discordId = discordId
        self.alive = True
        self.reviveNum = 0
        self.battleWins = battleWins
    
    def setNFT(self, tokenId):
        self.NFT = tokenId
        
    def setBoost(self, boosts):
        self.boosts = boosts
        
    def setXrainPower(self, xrainPower):
        self.xrainPower = xrainPower
    
    def kill(self):
        self.alive = False
        
    def revive(self):
        self.alive = True
        self.reviveNum += 1