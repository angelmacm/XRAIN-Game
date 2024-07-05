from sqlalchemy import Column, Integer, DateTime, VARCHAR, Date
from sqlalchemy.orm import column_property
from sqlalchemy.ext.declarative import declarative_base

from components.config import dbConfig

# Define the base class
Base = declarative_base()

class BattleQuotes(Base):
    __tablename__ = dbConfig['quotes_table_name']

    quoteId = Column(Integer, primary_key=True)
    quoteType = Column(VARCHAR)
    quoteDesc = Column(VARCHAR)