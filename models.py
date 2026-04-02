# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, BigInteger
from database import Base # Импортируем только Base

class User(Base):
    __tablename__ = 'users'
    tg_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    balance = Column(Float, default=100.0)
    cases_count = Column(Integer, default=0)
    total_earned = Column(Float, default=0.0)

class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.tg_id'))
    item_name = Column(String)
    item_price = Column(Float)

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.tg_id'))
    text = Column(String)

class Promo(Base):
    __tablename__ = 'promos'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    reward = Column(Float)
    uses = Column(Integer, default=1)