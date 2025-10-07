from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

from config import config

Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    language_code = Column(String, default='en')

    # Statistics
    total_games = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    games_lost = Column(Integer, default=0)
    pieces_captured = Column(Integer, default=0)
    total_moves = Column(Integer, default=0)

    # Calculated stats
    win_rate = Column(Float, default=0.0)
    average_moves_per_game = Column(Float, default=0.0)

    # Player level and experience
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    coins = Column(Integer, default=100)

    # Preferences
    preferred_color = Column(String, default='red')
    sound_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    # Relationships
    games = relationship("GamePlayer", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    game_code = Column(String, unique=True, index=True)
    game_type = Column(String)
    status = Column(String, default='waiting')
    max_players = Column(Integer, default=4)
    current_players = Column(Integer, default=0)
    current_turn = Column(Integer, default=0)

    # New fields
    dice_value = Column(Integer, default=0)
    board_state = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    players = relationship("GamePlayer", back_populates="game")

class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    color = Column(String)
    player_order = Column(Integer)
    is_ready = Column(Boolean, default=False)

    # Game progress
    pieces_position = Column(JSON)
    has_started = Column(Boolean, default=False)
    final_position = Column(Integer, nullable=True)

    # Relationships
    game = relationship("Game", back_populates="players")
    user = relationship("User", back_populates="games")

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    icon = Column(String)
    condition_type = Column(String)
    condition_value = Column(Integer)
    reward_coins = Column(Integer, default=0)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

def init_db():
    Base.metadata.create_all(bind=engine)
    _create_sample_achievements()

def _create_sample_achievements():
    """Create sample achievements when database is initialized"""
    db = SessionLocal()
    try:
        achievements_data = [
            {'name': 'First Game', 'description': 'Play your first game', 'icon': '🎮', 'condition_type': 'games_played', 'condition_value': 1, 'reward_coins': 10},
            {'name': 'First Win', 'description': 'Win your first game', 'icon': '🏆', 'condition_type': 'games_won', 'condition_value': 1, 'reward_coins': 20},
            {'name': 'Piece Hunter', 'description': 'Capture 10 pieces', 'icon': '🎯', 'condition_type': 'pieces_captured', 'condition_value': 10, 'reward_coins': 15},
        ]

        for achievement_data in achievements_data:
            existing = db.query(Achievement).filter_by(name=achievement_data['name']).first()
            if not existing:
                achievement = Achievement(**achievement_data)
                db.add(achievement)

        db.commit()
        print("✅ Sample achievements created!")

    except Exception as e:
        print(f"❌ Error creating achievements: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
