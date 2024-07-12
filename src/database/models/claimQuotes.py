from sqlalchemy import Column, Integer, VARCHAR
from sqlalchemy.orm import column_property
from sqlalchemy.ext.declarative import declarative_base

from components.config import dbConfig

# Define the base class
Base = declarative_base()

class ClaimQuotes(Base):
    __tablename__ = dbConfig['claim_quotes_table_name']

    quoteId = Column(Integer, index=True, primary_key=True)
    nftGroupName = column_property(Column('NFTGroupName', VARCHAR))
    taxonId = Column(Integer)
    description = Column(VARCHAR)