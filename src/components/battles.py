from components.players import Players
from random import randint
from database.db import BattleRoyaleDB 

class Battle:
    def __init__(self, dbInstance: BattleRoyaleDB):
        self.players: list[Players] = []
        self.totalWager = 0
        self.dbInstance = dbInstance
        self.reviveBan = []
        self.currentAlive = []
        self.currentDead = []

    def join(self, player: Players):
        self.players.append(player)
        self.totalWager += player.wager
        self.currentAlive.append(player)
    
    def getNFTList(self) -> list:
        return [players.NFT for players in self.players]
    
    def getBoostedList(self) -> list:
        return [players.name for players in self.players if players.boosts > 0]
    
    # set Alive to true if you only want to return alive players
    def __randomUniqueUser(self, alive=True) -> Players:
        attempts = 0
        maxAttempts = 100
        while attempts < maxAttempts:
            uniquePlayer = self.__randomUser()
            
            if uniquePlayer not in self.cycledPlayers:
                if alive and not uniquePlayer.alive:
                    continue  # Skip if we need an alive player but got a dead one
                self.cycledPlayers.append(uniquePlayer)
                if uniquePlayer.alive:
                    self.cycledAlive.append(uniquePlayer)
                return uniquePlayer
            attempts += 1
        raise Exception("PickUniquePlayerError")
    
    def __randomUser(self) -> Players:
        return self.players[randint(0, len(self.players)-1)]
    
    def getAlivePlayers(self):
        return [players for players in self.players if players.alive] 
    
    def getDeadPlayers(self):
        return [players for players in self.players if not players.alive] 
    
    async def battle(self) -> dict:
        returnBody = {'quotes': None,
                      'alive': None,
                      'winner': None,
                      'deadNum': None,
                      'participantsNum': None,
                      'nftLinks': None}
        
        # Function that does the battle system
        
        quotesList = []
        
        # List of players that we interacted with
        self.cycledAlive = []
        self.cycledPlayers = []
        
        while len(self.cycledPlayers) < len(self.players):
            
            # Pick a player
            playerOne = self.__randomUniqueUser(alive=False)
            
            # Roll for quote, include revival quotes if player is not alive
            quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote(revival=not playerOne.alive)
            
            if playerOne.alive == False:
                
                if quoteCategory != "Revival":
                    continue
                
                if playerOne.boosts == 0:
                    continue
                
                if playerOne.reviveNum >= 2:
                    continue
                

            # If there's no other players available for player 2, force neutral quote category, skip if revival
            if len(self.cycledAlive) == len(self.currentAlive) and quoteCategory != 'Revival':
                while quoteCategory != 'Neutral':
                    quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote()
                    
            # Replace the player name to the format
            quoteDescription:str = quoteDescription.replace("$Player1", playerOne.name)
            
            if quoteCategory not in ['Neutral', "Revival"]:
                playerTwo = self.__randomUniqueUser()
                quoteDescription = quoteDescription.replace("$Player2",playerTwo.name)
            
            match quoteCategory:
                
                # Kill the lower wins
                case "High RANK kill":
                    playerToKill = playerOne if playerOne.battleWins < playerTwo.battleWins else playerTwo
                    
                # Kill the lower power
                case "High XRAIN kill":
                    playerToKill = playerOne if playerOne.xrainPower < playerTwo.xrainPower else playerTwo
                    
                # Kill the higher power 
                case "Low XRAIN kill":
                    playerToKill = playerTwo if playerOne.xrainPower < playerTwo.xrainPower else playerOne
                
                # Kill randomly
                case "Normal Kill":
                    playerToKill = playerOne
                
                # No one dies
                case "Neutral":
                    pass      
                
                case "Revival":
                    playerOne.revive()  

            if quoteCategory not in ['Neutral', "Revival"]:
                playerOne.addKill() if playerOne != playerToKill else playerOne.kill()
                playerTwo.addKill() if playerTwo != playerToKill else playerTwo.kill()
            
            quotesList.append(quoteDescription)
            
            
        self.currentAlive = remainingAlive = self.getAlivePlayers()
        self.currentDead = self.getDeadPlayers()
        
        returnBody['quotes'] = quotesList
        returnBody['alive'] = remainingAlive
        returnBody['winner'] = remainingAlive[0] if len(remainingAlive) == 1 else None
        returnBody['deadNum'] = len(self.currentDead)
        returnBody['participantsNum'] = len(remainingAlive)
        returnBody['nftLinks'] = [player.nftLink for player in remainingAlive]
        
        return returnBody
        