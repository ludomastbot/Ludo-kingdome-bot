import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime
import random
import string
from database.models import Game, GamePlayer, User, SessionLocal
from utils.logger import logger

class GameService:
    def __init__(self):
        self.db = SessionLocal()
    
    def generate_game_code(self, length=6):
        """Generate unique game code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            existing = self.db.query(Game).filter(Game.game_code == code).first()
            if not existing:
                return code
    
    def create_game(self, game_type: str, created_by: int, max_players: int = 4):
        """Create a new game lobby"""
        try:
            game_code = self.generate_game_code()
            
            game = Game(
                game_code=game_code,
                game_type=game_type,
                max_players=max_players,
                current_players=0,  # Start with 0, we'll add creator separately
                board_state=self._get_initial_board_state()
            )
            
            self.db.add(game)
            self.db.commit()
            self.db.refresh(game)
            
            # Now add creator to the game
            self.join_game(game_code, created_by, 'red')
            
            logger.info(f"New game created: {game_code} by user {created_by}")
            return game
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating game: {e}")
            raise
    
    def join_game(self, game_code: str, user_id: int, color: str = None):
        """Join a player to a game"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return None, "Game not found"
            
            if game.status != 'waiting':
                return None, "Game already started"
            
            # Check if user already in this game
            existing_player = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.user_id == user_id
            ).first()
            
            if existing_player:
                return game, "Already in game"
            
            # Check if game is full
            if game.current_players >= game.max_players:
                return None, "Game is full"
            
            # Get available colors
            available_colors = self._get_available_colors(game.id)
            if not available_colors:
                return None, "No colors available"
            
            # Use requested color if available, otherwise random
            if color and color in available_colors:
                selected_color = color
            else:
                selected_color = random.choice(available_colors)
            
            # Get player order
            player_order = game.current_players + 1
            
            # Create game player
            game_player = GamePlayer(
                game_id=game.id,
                user_id=user_id,
                color=selected_color,
                player_order=player_order,
                pieces_position=[0, 0, 0, 0]  # All pieces at home
            )
            
            self.db.add(game_player)
            
            # Update game player count
            game.current_players += 1
            self.db.commit()
            
            logger.info(f"User {user_id} joined game {game_code} as {selected_color}")
            return game, f"Joined as {selected_color}"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error joining game: {e}")
            return None, str(e)
    
    def _get_available_colors(self, game_id: int):
        """Get available colors for a game"""
        taken_colors = [
            player.color for player in 
            self.db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
        ]
        
        all_colors = ['red', 'blue', 'green', 'yellow']
        available = [color for color in all_colors if color not in taken_colors]
        return available
    
    def _get_initial_board_state(self):
        """Get initial board state"""
        return {
            'red_home': [1, 1, 1, 1],      # 1 = piece at home
            'blue_home': [1, 1, 1, 1],
            'green_home': [1, 1, 1, 1],
            'yellow_home': [1, 1, 1, 1],
            'board_positions': [None] * 52,  # 52 board positions
            'red_start': 0,
            'blue_start': 13,
            'green_start': 26,
            'yellow_start': 39
        }
    
    def get_game_players(self, game_id: int):
        """Get all players in a game"""
        players = self.db.query(GamePlayer, User).join(
            User, GamePlayer.user_id == User.id
        ).filter(GamePlayer.game_id == game_id).all()
        
        return [
            {
                'user_id': player.User.id,
                'username': player.User.username or player.User.first_name,
                'color': player.GamePlayer.color,
                'player_order': player.GamePlayer.player_order,
                'is_ready': player.GamePlayer.is_ready
            }
            for player in players
        ]
    
    def start_game(self, game_code: str, started_by: int):
        """Start the game"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return False, "Game not found"
            
            # Check if user is the game creator or has permission
            players = self.get_game_players(game.id)
            player_ids = [p['user_id'] for p in players]
            
            if started_by not in player_ids:
                return False, "You are not in this game"
            
            # Check if game has enough players
            if game.current_players < 2:
                return False, "Need at least 2 players to start"
            
            # Check if game already started
            if game.status != 'waiting':
                return False, "Game already started"
            
            # Start the game
            game.status = 'active'
            game.started_at = datetime.utcnow()
            game.current_turn = 1  # First player's turn
            
            self.db.commit()
            logger.info(f"Game {game_code} started by user {started_by}")
            return True, "Game started successfully"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error starting game: {e}")
            return False, str(e)
    
    def leave_game(self, game_code: str, user_id: int):
        """Player leaves the game"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return False, "Game not found"
            
            # Find player in game
            player = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.user_id == user_id
            ).first()
            
            if not player:
                return False, "You are not in this game"
            
            # Remove player
            self.db.delete(player)
            game.current_players -= 1
            
            # If no players left, delete game
            if game.current_players == 0:
                self.db.delete(game)
                message = "Game deleted (no players left)"
            else:
                message = "Left the game"
            
            self.db.commit()
            logger.info(f"User {user_id} left game {game_code}")
            return True, message
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error leaving game: {e}")
            return False, str(e)
    
    def get_game_info(self, game_code: str):
        """Get complete game information"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return None
            
            players = self.get_game_players(game.id)
            
            return {
                'game_code': game.game_code,
                'game_type': game.game_type,
                'status': game.status,
                'max_players': game.max_players,
                'current_players': game.current_players,
                'players': players,
                'created_at': game.created_at
            }
            
        except Exception as e:
            logger.error(f"Error getting game info: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        self.db.close()
