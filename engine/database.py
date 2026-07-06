import sqlite3
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st

Base = declarative_base()
engine = create_engine(st.secrets["DATABASE_URL"])
SessionLocal = sessionmaker(bind=engine)

class WeatherReading(Base):
    __tablename__ = "weather_readings"
    id = Column(Integer, primary_key=True)
    location = Column(String)
    temp = Column(Float)
    humidity = Column(Float)
    cape = Column(Float)
    timestamp = Column(DateTime)

def init_db():
    Base.metadata.create_all(engine)

# Implementar aquí funciones CRUD para WeatherReading y Alertas...
