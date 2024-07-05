class Players:
    def __init__(self, xrpId, wager):
        self.xrpId = xrpId
        self.wager = wager
    
    def setNFT(self, tokenId):
        self.NFT = tokenId
        
    def setBoost(self, boosts):
        self.boosts = boosts
        
    def setXrainPower(self, xrainPower):
        self.xrainPower = xrainPower