import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ludo_bot.db')
    
    # Bot Settings
    BOT_USERNAME = ""
    ADMIN_IDS = [123456789]  # Replace with your Telegram ID
    
    # Game Settings
    MAX_PLAYERS = 4
    TURN_TIMEOUT = 60  # seconds
    GAME_TIMEOUT = 1800  # 30 minutes
    
    # Development Settings
    DEBUG = True
    LOG_LEVEL = 'INFO'

config = Config()
