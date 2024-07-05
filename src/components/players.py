class Players:
    def __init__(self, xrpId, wager, name, discordId):
        self.xrpId = xrpId
        self.wager = wager
        self.name = name
        self.discordId = discordId
        self.alive = True
        self.reviveNum = 0
    
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