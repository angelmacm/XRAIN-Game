from components.players import Players
from components.config import gameConfig
from random import randint
from database.db import BattleRoyaleDB 
from components.logging import loggingInstance

class Battle:
    def __init__(self, dbInstance: BattleRoyaleDB):
        self.players: list[Players] = []
        self.totalWager = 0
        self.dbInstance = dbInstance
        self.reviveBan = []
        self.currentAlive = []
        self.currentDead = []
        self.verbose = gameConfig.getboolean('verbose')

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
                
                if playerOne.reviveNum >= gameConfig.getint('max_revive'):
                    continue
                

            # If there's no other players available for player 2, force neutral quote category, skip if revival
            if len(self.cycledAlive) == len(self.currentAlive) and quoteCategory != 'Revival':
                while quoteCategory != 'Neutral':
                    quoteCategory, quoteDescription = await self.dbInstance.getRandomQuote()
                    
            
            if quoteCategory not in ['Neutral', "Revival"]:
                playerTwo = self.__randomUniqueUser()
            else:
                # Replace the player name to the format if it is Neutral or Revival
                quoteDescription:str = quoteDescription.replace("$Player1", f"**{playerOne.name}**")
            
            loggingInstance.info(f"Matching category: {quoteCategory}")
            
            match str(quoteCategory).lower().strip():
                
                # Kill the lower wins
                case "high rank kill":
                    loggingInstance.info("Matched: High Rank Kill")
                    playerToKill = playerOne if playerOne.battleWins < playerTwo.battleWins else playerTwo
                    
                # Kill the lower power
                case "high xrain kill":
                    loggingInstance.info("Matched: High XRAIN Kill")
                    playerToKill = playerOne if playerOne.xrainPower < playerTwo.xrainPower else playerTwo
                    
                # Kill the higher power 
                case "low xrain kill":
                    loggingInstance.info("Matched: Low XRAIN Kill")
                    playerToKill = playerTwo if playerOne.xrainPower < playerTwo.xrainPower else playerOne
                
                # Kill randomly
                case "normal kill":
                    loggingInstance.info("Matched: Normal Kill")
                    playerToKill = playerOne if randint(0,1) else playerTwo
                
                # No one dies
                case "neutral":
                    loggingInstance.info("Matched: Neutral")
                    quoteDescription += "| :peace:"
                    pass      
                
                case "revival":
                    loggingInstance.info("Matched: Revival")
                    quoteDescription += "| :innocent:"
                    playerOne.revive()  
                
                case _:
                    loggingInstance.error(f"Case Matching failed on [{str(quoteCategory).lower()}]")
                    loggingInstance.error(f"wins: {'playerOne' if playerOne.battleWins < playerTwo.battleWins else 'playerTwo'}")
                    loggingInstance.error(f"High: {'playerOne' if playerOne.xrainPower < playerTwo.xrainPower else 'playerTwo'}")
                    loggingInstance.error(f"Low: {'playerTwo' if playerOne.xrainPower < playerTwo.xrainPower else 'playerOne'}")

            if quoteCategory not in ['Neutral', "Revival"]:
                playerDead = playerOne if playerOne == playerToKill else playerTwo
                playerAlive = playerOne if playerOne != playerToKill else playerTwo
                playerDead.kill()
                playerAlive.addKill()
                quoteDescription = quoteDescription.replace("$Player2",f"**{playerDead.name}**")
                quoteDescription = quoteDescription.replace("$Player1",f"**{playerAlive.name}**")
                quoteDescription += "| :skull_crossbones:"
            
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