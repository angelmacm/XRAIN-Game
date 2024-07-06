from configparser import ConfigParser

baseConfig = ConfigParser()
baseConfig.read("config.ini")

coinsConfig = baseConfig['COINS']
botConfig = baseConfig['BOT']
xrplConfig = baseConfig['XRPL']
dbConfig = baseConfig['DATABASE']
xummConfig = baseConfig['XUMM']