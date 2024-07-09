from components.players import Players
from random import randint
from database.db import BattleRoyaleDB 

class Battle:
    def __init__(self, dbInstance: BattleRoyaleDB):
        self.players: list[Players] = []
        self.totalWager = 0
        self.dbInstance = dbInstance
        pass

    def join(self, player: Players):
        self.players.append(player)
        self.totalWager += player.wager
    
    def getNFTList(self) -> list:
        return [players.NFT for players in self.players]
    
    def getBoostedList(self) -> list:
        return [players.name for players in self.players if players.boosts > 0]
    
    def __randomUniqueUser(self):
        
        uniquePlayer = self.__randomUser()
        
        # Reroll if this player has been involved before
        while uniquePlayer in self.cycledPlayers:
            uniquePlayer = self.__randomUser()
            
        self.cycledPlayers.append(uniquePlayer)
        return uniquePlayer
    
    def __randomUser(self):
        return self.currentPlayers[randint(0, len(self.currentPlayers)-1)]
    
    async def battle(self) -> list[str]:
        # Function that does the battle system
        
        quotesList = []
        
        # List of all current alive players
        self.currentPlayers = [players for players in self.players if players.alive]
        self.cycledPlayers = []
        
        while self.cycledPlayers != self.currentPlayers:
            
            # Pick a player
            playerOne = self.__randomUniqueUser()
            self.cycledPlayers.append(playerOne)
            
            # Roll for quotes
            quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote()
            
            # If there's no other players available for player 2, force neutral quote category
            if self.cycledPlayers == self.currentPlayers:
                while quoteCategory != 'Neutral':
                    quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote()
                    
            # Replace the player name to the format
            quoteDescription:str = quoteDescription.replace("$Player1", playerOne.name)
            
            match quoteCategory:
                
                # Kill the lower wins
                case "High RANK kill":
                    playerTwo = self.__randomUniqueUser()
                    quoteCategory.replace("$Player2",playerTwo.name)
                    playerToKill = playerOne if playerOne.battleWins < playerTwo.battleWins else playerTwo
                    playerToKill.kill()
                    
                # Kill the lower power
                case "High XRAIN kill":
                    playerTwo = self.__randomUniqueUser()
                    quoteCategory.replace("$Player2",playerTwo.name)
                    playerToKill = playerOne if playerOne.xrainPower < playerTwo.xrainPower else playerTwo
                    playerToKill.kill()
                    
                # Kill the higher power 
                case "Low XRAIN kill":
                    playerTwo = self.__randomUniqueUser()
                    quoteCategory.replace("$Player2",playerTwo.name)
                    playerToKill = playerTwo if playerOne.xrainPower < playerTwo.xrainPower else playerOne
                    playerToKill.kill()
                
                # Kill randomly
                case "Normal Kill":
                    playerTwo = self.__randomUniqueUser()
                    quoteCategory.replace("$Player2",playerTwo.name)
                    playerToKill = playerOne if randint(0,1) else playerTwo
                    playerToKill.kill()
                
                # No one dies
                case "Neutral":
                    pass        
        
        return quotesList + await self.reviveRoll()
        
    
    async def reviveRoll(self):        
        quotesList = []
        # List of all current dead players that can be revived
        for players in self.players:
            if players.boosts > 0 and not players.alive:
                # roll function
                quoteType, quoteDescription = await self.dbInstance.getRandomQuote(revival=True)
                
                if quoteType == 'Revival':
                    players.revive()
                    quoteDescription: str = quoteDescription.replace("$Player1", players.name)
                    quotesList.append(quoteDescription)
            else:
                continue
            
        return quotesList