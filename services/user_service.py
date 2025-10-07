import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime
from database.models import User, Achievement, UserAchievement, SessionLocal
from utils.logger import logger

class UserService:
    def __init__(self):
        self.db = SessionLocal()
    
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = "", last_name: str = None, 
                          language_code: str = "en") -> User:
        """Get existing user or create new one"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"New user created: {user.telegram_id}")
            else:
                # Update last active and profile info
                user.last_active = datetime.utcnow()
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                self.db.commit()
            
            return user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in get_or_create_user: {e}")
            raise
    
    def update_user_stats(self, user_id: int, game_won: bool = False, 
                         pieces_captured: int = 0, moves_made: int = 0):
        """Update user statistics after a game"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return
            
            user.total_games += 1
            user.total_moves += moves_made
            
            if game_won:
                user.games_won += 1
            else:
                user.games_lost += 1
            
            user.pieces_captured += pieces_captured
            
            # Calculate win rate
            if user.total_games > 0:
                user.win_rate = round((user.games_won / user.total_games) * 100, 2)
                user.average_moves_per_game = round(user.total_moves / user.total_games, 2)
            
            # Add experience
            experience_gained = 10  # Base experience
            if game_won:
                experience_gained += 20
            experience_gained += pieces_captured * 2
            
            user.experience += experience_gained
            
            # Level up calculation (100 exp per level)
            new_level = (user.experience // 100) + 1
            if new_level > user.level:
                user.level = new_level
                logger.info(f"User {user_id} leveled up to {new_level}")
            
            # Add coins reward
            coins_gained = 5  # Base coins
            if game_won:
                coins_gained += 10
            coins_gained += pieces_captured
            
            user.coins += coins_gained
            
            self.db.commit()
            logger.info(f"User stats updated for user_id: {user_id}")
            
            # Check for new achievements
            self._check_achievements(user_id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user stats: {e}")
    
    def _check_achievements(self, user_id: int):
        """Check and unlock new achievements for user"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return
            
            achievements = self.db.query(Achievement).all()
            unlocked_achievements = []
            
            for achievement in achievements:
                # Check if user already has this achievement
                existing = self.db.query(UserAchievement).filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement.id
                ).first()
                
                if existing:
                    continue
                
                # Check achievement conditions
                if achievement.condition_type == 'games_played':
                    if user.total_games >= achievement.condition_value:
                        unlocked_achievements.append(achievement)
                
                elif achievement.condition_type == 'games_won':
                    if user.games_won >= achievement.condition_value:
                        unlocked_achievements.append(achievement)
                
                elif achievement.condition_type == 'pieces_captured':
                    if user.pieces_captured >= achievement.condition_value:
                        unlocked_achievements.append(achievement)
            
            # Unlock new achievements
            for achievement in unlocked_achievements:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id
                )
                self.db.add(user_achievement)
                
                # Add reward coins
                user.coins += achievement.reward_coins
                
                logger.info(f"User {user_id} unlocked achievement: {achievement.name}")
            
            if unlocked_achievements:
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    def get_user_stats(self, user_id: int) -> dict:
        """Get comprehensive user statistics"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Get unlocked achievements
            achievements = self.db.query(UserAchievement, Achievement).join(
                Achievement, UserAchievement.achievement_id == Achievement.id
            ).filter(UserAchievement.user_id == user_id).all()
            
            return {
                'user_info': {
                    'username': user.username,
                    'first_name': user.first_name,
                    'level': user.level,
                    'experience': user.experience,
                    'coins': user.coins
                },
                'statistics': {
                    'total_games': user.total_games,
                    'games_won': user.games_won,
                    'games_lost': user.games_lost,
                    'win_rate': user.win_rate,
                    'pieces_captured': user.pieces_captured,
                    'total_moves': user.total_moves,
                    'average_moves_per_game': user.average_moves_per_game
                },
                'achievements': [
                    {
                        'name': ach.Achievement.name,
                        'description': ach.Achievement.description,
                        'icon': ach.Achievement.icon,
                        'unlocked_at': ach.UserAchievement.unlocked_at.strftime('%Y-%m-%d %H:%M')
                    }
                    for ach in achievements
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    def get_leaderboard(self, scope: str = 'global', limit: int = 10) -> list:
        """Get leaderboard data"""
        try:
            if scope == 'global':
                # Global leaderboard - top players by win rate and games played
                users = self.db.query(User).filter(
                    User.total_games >= 5
                ).order_by(
                    User.win_rate.desc(),
                    User.total_games.desc()
                ).limit(limit).all()
            else:
                # Group leaderboard (will be implemented later with group tracking)
                users = self.db.query(User).order_by(
                    User.win_rate.desc(),
                    User.total_games.desc()
                ).limit(limit).all()
            
            leaderboard = []
            for index, user in enumerate(users, 1):
                leaderboard.append({
                    'rank': index,
                    'username': user.username or user.first_name,
                    'level': user.level,
                    'win_rate': user.win_rate,
                    'total_games': user.total_games,
                    'pieces_captured': user.pieces_captured
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        self.db.close()
