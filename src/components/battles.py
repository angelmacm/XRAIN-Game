from components.players import Players
from random import randint
from database.db import BattleRoyaleDB 

class Battle:
    def __init__(self, dbInstance: BattleRoyaleDB):
        self.players: list[Players] = []
        self.totalWager = 0
        self.dbInstance = dbInstance
        self.reviveBan = []

    def join(self, player: Players):
        self.players.append(player)
        self.totalWager += player.wager
    
    def getNFTList(self) -> list:
        return [players.NFT for players in self.players]
    
    def getBoostedList(self) -> list:
        return [players.name for players in self.players if players.boosts > 0]
    
    # set Alive to true if you only want to return alive players
    def __randomUniqueUser(self, alive = True):
        uniquePlayer = self.__randomUser(alive)
        
        # Reroll if this player has been involved before
        while uniquePlayer in self.cycledPlayers:
            uniquePlayer = self.__randomUser(alive)
            if alive and not uniquePlayer.alive:
                continue
                
        if uniquePlayer.alive:
            self.cycledAlive.append(uniquePlayer)
            
        self.cycledPlayers.append(uniquePlayer)
        return uniquePlayer
    
    def __randomUser(self, alive = True):
        return self.players[randint(0, len(self.players)-1)]
    
    def getAlivePlayers(self):
        return [players for players in self.players if players.alive] 
    
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
        self.currentAlive = self.getAlivePlayers()
        self.cycledAlive = []
        self.cycledPlayers = self.reviveBan
        
        while len(self.cycledPlayers) < len(self.players):
            
            # Pick a player
            playerOne = self.__randomUniqueUser(alive=False)
            
            if playerOne.boosts > 0 and not playerOne.alive:
                if playerOne.reviveNum < 2:
                    quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote(revival=True)
                    if quoteCategory != "Revival":
                        continue
                else:
                    self.reviveBan.append(playerOne)
                    continue

            else:
            # Roll for quotes
                quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote()

            # Sanity check
            if not playerOne.alive and quoteCategory != "Revival":
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
                    playerToKill.kill()
                    
                # Kill the lower power
                case "High XRAIN kill":
                    playerToKill = playerOne if playerOne.xrainPower < playerTwo.xrainPower else playerTwo
                    playerToKill.kill()
                    
                # Kill the higher power 
                case "Low XRAIN kill":
                    playerToKill = playerTwo if playerOne.xrainPower < playerTwo.xrainPower else playerOne
                    playerToKill.kill()
                
                # Kill randomly
                case "Normal Kill":
                    playerToKill = playerOne if randint(0,1) else playerTwo
                    playerToKill.kill()
                
                # No one dies
                case "Neutral":
                    pass      
                
                case "Revival":
                    playerOne.revive()  
        
            quotesList.append(quoteDescription)
            
            
        remainingAlive = self.getAlivePlayers()
        
        returnBody['quotes'] = quotesList
        returnBody['alive'] = remainingAlive
        returnBody['winner'] = remainingAlive[0] if len(remainingAlive) == 1 else None
        returnBody['deadNum'] = len(self.players) - len(remainingAlive)
        returnBody['participantsNum'] = len(self.players)
        returnBody['nftLinks'] = [player.nftLink for player in remainingAlive]
        
        return returnBody
        