from sqlalchemy import Column, Integer, VARCHAR, Date
from sqlalchemy.orm import column_property
from sqlalchemy.ext.declarative import declarative_base

from components.config import dbConfig

# Define the base class
Base = declarative_base()

class NFTTraitList(Base):
    __tablename__ = dbConfig['nft_trait_list_table_name']

    uri = Column(VARCHAR, primary_key=True)
    tokenId = Column(VARCHAR, index=True)
    nftGroupName = column_property(Column('NFTGroupName', VARCHAR))
    taxonId = Column(Integer)
    xrpId = Column(VARCHAR)
    xrpIdOld = Column(VARCHAR)
    metalink = Column(VARCHAR)
    nftlink = Column(VARCHAR)
    date = Column(Integer)
    dateOld = Column(Integer)
    Background = Column(VARCHAR)
    eyePatch = column_property(Column('eye_patch', VARCHAR))
    headpiece = Column(VARCHAR)
    rfUsLogo = column_property(Column('RF_US_LOGO', VARCHAR))
    weapons  = Column(VARCHAR)
    chains = column_property(Column('chains', VARCHAR))
    eyes = Column(VARCHAR)
    mouth = Column(VARCHAR)
    separateEntities = column_property(Column('separate_entities', VARCHAR))
    clothes = Column(VARCHAR)
    glasses = column_property(Column('Glasses', VARCHAR))
    parrots = column_property(Column('parrots', VARCHAR))
    skin = Column(VARCHAR)
    accessories = Column(VARCHAR)
    eye = Column(VARCHAR)
    body = Column(VARCHAR)
    outfit = Column(VARCHAR)
    backgroundVal = column_property(Column('BackgroundVal', Integer))
    eyePatchVal = column_property(Column('eye_patchVal', Integer))
    headpieceVal = Column(Integer)
    rfUsLogoVal = column_property(Column('RF_US_LOGOVal', Integer))
    weaponsVal = Column(Integer)
    chainsVal = column_property(Column('ChainsVal', Integer))
    eyesVal = Column(Integer)
    mouthVal = Column(Integer)
    separateEntitiesVal = column_property(Column('separate_entitiesVal', Integer))
    clothesVal = Column(Integer)
    glassesVal = column_property(Column('GlassesVal', Integer))
    parrotsVal = column_property(Column('ParrotsVal', Integer))
    skinVal = Column(Integer)
    accessoriesVal = Column(Integer)
    eyeVal = Column(Integer)
    bodyVal = Column(Integer)
    outfitVal = Column(Integer)
    totalXRAIN = Column(Integer)
    grandTotal = column_property(Column('GrandTotal', Integer))
    blockFlag = Column(Integer)
    sellFlag = Column(Integer)
    sellAmt = Column(Integer)
    sellDate = Column(Date)
    reputationFlag = Column(Integer)