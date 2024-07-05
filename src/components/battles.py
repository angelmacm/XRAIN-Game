from components.players import Players
from random import randint

class Battle:
    def __init__(self):
        self.players: list[Players] = []
        self.totalWager = 0
        pass

    def join(self, player: Players):
        self.players.append(player)
        self.totalWager += player.wager
    
    def getNFTList(self) -> list:
        return [players.NFT for players in self.players]
    
    def getBoostedList(self) -> list:
        return [players.name for players in self.players if players.boosts > 0]
    
    def battle(self) -> list[str]:
        # Function that does the battle system
        
        quotesList = []
        
        # List of all current alive players
        self.currentPlayers = [players for players in self.players if players.alive]
        
        playerOne = self.currentPlayers[randint(0, len(self.currentPlayers)-1)]
        
        # Roll for quotes
        
        # if cases category
        
        
        
        return quotesList + self.reviveRoll()
        
    
    def reviveRoll(self):        
        quotesList = []
        # List of all current dead players that can be revived
        for players in self.players:
            if players.boosts > 0 and not players.alive:
                # roll function
                # if revived:
                    # self.players.append(revived)
                pass
            else:
                continue
            
        return quotesList