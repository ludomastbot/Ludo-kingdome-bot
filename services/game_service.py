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
            code = ''.join(random.choices(string.ascii_uppercase, k=length))
            existing = self.db.query(Game).filter(Game.game_code == code).first()
            if not existing:
                return code

    def create_game(self, game_type: str, created_by: int, max_players: int = 4):
        """Create a new game lobby - FIXED VERSION"""
        try:
            game_code = self.generate_game_code()

            game = Game(
                game_code=game_code,
                game_type=game_type,
                max_players=max_players,
                current_players=0,
                status='waiting',
                current_turn=0,
                dice_value=0,
                board_state=self._get_initial_board_state()
            )

            self.db.add(game)
            self.db.commit()
            self.db.refresh(game)

            # Now add creator to the game as red color
            creator_player = GamePlayer(
                game_id=game.id,
                user_id=created_by,
                color='red',
                player_order=0,
                pieces_position=[-1, -1, -1, -1],
                is_ready=True
            )

            self.db.add(creator_player)
            game.current_players = 1
            self.db.commit()

            logger.info(f"New game created: {game_code} by user {created_by}")
            return game

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating game: {e}")
            raise

    def join_game(self, game_code: str, user_id: int, color: str = None):
        """Join a player to a game"""
        try:
            game = self.get_game_by_code(game_code)
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
            player_order = game.current_players

            # Create game player
            game_player = GamePlayer(
                game_id=game.id,
                user_id=user_id,
                color=selected_color,
                player_order=player_order,
                pieces_position=[-1, -1, -1, -1],
                is_ready=True
            )

            self.db.add(game_player)
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
            'red_home': [1, 1, 1, 1],
            'blue_home': [1, 1, 1, 1],
            'green_home': [1, 1, 1, 1],
            'yellow_home': [1, 1, 1, 1],
            'board_positions': [None] * 52,
            'red_start': 0,
            'blue_start': 13,
            'green_start': 26,
            'yellow_start': 39
        }

    def get_game_players(self, game_id: int):
        """Get all players in a game"""
        players = self.db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()
        
        result = []
        for player in players:
            # Get user details
            user = self.db.query(User).filter(User.id == player.user_id).first()
            if user:
                result.append({
                    'user_id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username or user.first_name,
                    'color': player.color,
                    'player_order': player.player_order,
                    'is_ready': player.is_ready,
                    'pieces_position': player.pieces_position or [-1, -1, -1, -1]
                })
        
        return result

    def start_game(self, game_code: str, started_by: int):
        """Start the game"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return False, "Game not found"

            # Check if user is in this game
            player_exists = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.user_id == started_by
            ).first()

            if not player_exists:
                return False, "You are not in this game"

            if game.current_players < 2:
                return False, "Need at least 2 players to start"

            if game.status != 'waiting':
                return False, "Game already started"

            game.status = 'active'
            game.started_at = datetime.utcnow()
            game.current_turn = 0  # Start with first player

            self.db.commit()
            logger.info(f"Game {game_code} started by user {started_by}")
            return True, "Game started successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error starting game: {e}")
            return False, str(e)

    def get_game_info(self, game_code: str):
        """Get complete game information"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return None

            players = self.get_game_players(game.id)

            return {
                'game_code': game.game_code,
                'game_type': game.game_type,
                'status': game.status,
                'max_players': game.max_players,
                'current_players': game.current_players,
                'current_turn': game.current_turn,
                'dice_value': game.dice_value,
                'players': players,
                'created_at': game.created_at
            }

        except Exception as e:
            logger.error(f"Error getting game info: {e}")
            return None

    def get_game_by_code(self, game_code: str):
        """Get game by code"""
        return self.db.query(Game).filter(Game.game_code == game_code).first()

    def auto_start_game(self, game_code: str, creator_id: int):
        """Automatically start game when enough players joined or add bots - FIXED"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return False, "Game not found!"

            # Check if user is in this game
            creator_player = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.user_id == creator_id
            ).first()

            if not creator_player:
                return False, "Only game players can start the game!"

            current_players = game.current_players

            # If not enough players, add bot players automatically
            if current_players < game.max_players:
                bots_added = self._add_bot_players(game, game.max_players - current_players)
                if bots_added:
                    current_players = game.current_players

            # Check if we have enough players now
            if current_players >= 2:  # Minimum 2 players required
                return self.start_game(game_code, creator_id)
            else:
                return False, f"Need at least 2 players! Currently {current_players}/{game.max_players}"

        except Exception as e:
            logger.error(f"Error in auto_start_game: {e}")
            return False, f"Error starting game: {str(e)}"

    def _add_bot_players(self, game, num_bots: int):
        """Add bot players to the game - FIXED"""
        try:
            available_colors = self._get_available_colors(game.id)
            if not available_colors:
                return False

            bot_names = ["Smart Bot", "Ludo Pro", "Game Master", "AI Player"]

            bots_added = 0
            for i in range(min(num_bots, len(available_colors))):
                bot_color = available_colors[i]
                bot_name = bot_names[i] if i < len(bot_names) else f"Bot {i+1}"

                # Create bot player with negative user_id directly in GamePlayer
                # No need to create User record for bots
                bot_player = GamePlayer(
                    game_id=game.id,
                    user_id=-(i + 1),  # Negative ID for bots
                    color=bot_color,
                    player_order=game.current_players,
                    pieces_position=[-1, -1, -1, -1],
                    is_ready=True
                )

                self.db.add(bot_player)
                game.current_players += 1
                bots_added += 1
                logger.info(f"Added bot player: {bot_name} as {bot_color}")

            if bots_added > 0:
                self.db.commit()
                return True
            return False

        except Exception as e:
            logger.error(f"Error adding bot players: {e}")
            self.db.rollback()
            return False

    def get_user_active_game(self, user_id: int):
        """Get user's active game"""
        return self.db.query(Game).join(GamePlayer).filter(
            GamePlayer.user_id == user_id,
            Game.status.in_(['waiting', 'active'])
        ).first()

    def create_bot_game(self, game_type: str, created_by: int, human_players: int, bot_players: int):
        """Create a game with bot players (for bot commands) - FIXED"""
        try:
            total_players = human_players + bot_players

            if total_players > 4:
                return None, "Maximum 4 players allowed"

            if human_players < 1:
                return None, "At least one human player required"

            # Create game
            game = self.create_game(game_type, created_by, total_players)

            # Add additional human players if needed (for testing)
            # For now, just add bots
            if bot_players > 0:
                success = self._add_bot_players(game, bot_players)
                if not success:
                    return None, "Failed to add bot players"

            # Auto-start the game
            success, message = self.auto_start_game(game.game_code, created_by)
            if not success:
                return None, message

            logger.info(f"Bot game created: {game.game_code} with {human_players} humans and {bot_players} bots")
            return game, "Game created and started with bot players"

        except Exception as e:
            logger.error(f"Error creating bot game: {e}")
            return None, str(e)

    def get_visual_board(self, game_code: str, user_id: int = None) -> str:
        """Get visual board representation for game - IMPROVED"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return "❌ Game not found!"
            
            # Prepare game state for board
            game_state = {
                'players': [],
                'status': game.status,
                'current_player': self.colors[game.current_turn] if game.current_turn < len(self.colors) else 'red',
                'dice_value': game.dice_value or 0,
                'is_user_turn': False
            }
            
            # Add player data
            for player in game.players:
                player_data = {
                    'color': player.color,
                    'user_id': player.user_id,
                    'tokens': player.pieces_position or [-1, -1, -1, -1]
                }
                game_state['players'].append(player_data)
                
                # Check if it's user's turn
                if user_id and player.user_id == user_id and game.current_turn == player.player_order:
                    game_state['is_user_turn'] = True
            
            # Choose board type
            from services.board_service import board_service
            
            # Always use visual board for now
            return board_service.create_visual_board(game_state)
                
        except Exception as e:
            logger.error(f"Error getting visual board: {e}")
            return "❌ Error loading board."

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
