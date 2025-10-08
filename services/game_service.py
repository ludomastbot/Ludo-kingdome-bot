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
        self.colors = ['red', 'blue', 'green', 'yellow']

    def generate_game_code(self, length=6):
        """Generate unique game code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=length))
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
                current_players=0,
                status='waiting',
                current_turn=0,
                dice_value=0,
                board_state=self._get_initial_board_state()
            )

            self.db.add(game)
            self.db.commit()
            self.db.refresh(game)

            # Add creator to the game as red color
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

    def get_game_by_code(self, game_code: str):
        """Get game by game code"""
        return self.db.query(Game).filter(Game.game_code == game_code).first()

    def get_game_players(self, game_id: int):
        """Get all players in a game"""
        players = self.db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()

        result = []
        for player in players:
            # Get user details for human players
            if player.user_id > 0:
                user = self.db.query(User).filter(User.id == player.user_id).first()
                if user:
                    username = user.username or user.first_name
                else:
                    username = "Unknown"
            else:
                # Bot players
                bot_names = {
                    -1: "Smart Bot", -2: "Ludo Pro", 
                    -3: "Game Master", -4: "AI Player"
                }
                username = bot_names.get(player.user_id, f"Bot {abs(player.user_id)}")

            result.append({
                'user_id': player.user_id,
                'username': username,
                'color': player.color,
                'player_order': player.player_order,
                'is_ready': player.is_ready,
                'pieces_position': player.pieces_position or [-1, -1, -1, -1]
            })

        return result

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

    def start_game(self, game_code: str, user_id: int):
        """Start a game"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return False, "Game not found"

            if game.status != 'waiting':
                return False, "Game already started"

            # Check if user is in the game
            player = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.user_id == user_id
            ).first()

            if not player:
                return False, "You are not in this game"

            # Check minimum players
            if game.current_players < 2:
                return False, "Need at least 2 players to start"

            # Start the game
            game.status = 'active'
            game.started_at = datetime.utcnow()
            game.current_turn = 0  # Start with first player

            self.db.commit()

            logger.info(f"Game {game_code} started by user {user_id}")
            return True, "Game started successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error starting game: {e}")
            return False, str(e)

    def auto_start_game(self, game_code: str, creator_id: int):
        """Automatically start game when enough players joined or add bots"""
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
            if current_players >= 2:
                return self.start_game(game_code, creator_id)
            else:
                return False, f"Need at least 2 players! Currently {current_players}/{game.max_players}"

        except Exception as e:
            logger.error(f"Error in auto_start_game: {e}")
            return False, f"Error starting game: {str(e)}"

    def _add_bot_players(self, game, num_bots: int):
        """Add bot players to the game"""
        try:
            available_colors = self._get_available_colors(game.id)
            if not available_colors:
                return False

            bot_names = ["Smart Bot", "Ludo Pro", "Game Master", "AI Player"]

            bots_added = 0
            for i in range(min(num_bots, len(available_colors))):
                bot_color = available_colors[i]
                bot_name = bot_names[i] if i < len(bot_names) else f"Bot {i+1}"

                # Create bot player with negative user_id
                bot_player = GamePlayer(
                    game_id=game.id,
                    user_id=-(i + 1),
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

    def get_visual_board(self, game_code: str, user_id: int = None) -> str:
        """Get visual board representation for game - FIXED"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return "❌ Game not found!"

            # Prepare game state for board
            game_state = {
                'players': [],
                'status': game.status,
                'dice_value': game.dice_value or 0,
                'is_user_turn': False
            }

            # Get current player info
            if game.players and game.current_turn < len(game.players):
                current_player = game.players[game.current_turn]
                game_state['current_player'] = current_player.color
                
                # Check if it's user's turn
                if user_id and current_player.user_id == user_id:
                    game_state['is_user_turn'] = True
            else:
                game_state['current_player'] = 'red'

            # Add player data
            for player in game.players:
                player_data = {
                    'color': player.color,
                    'user_id': player.user_id,
                    'tokens': player.pieces_position or [-1, -1, -1, -1]
                }
                game_state['players'].append(player_data)

            # Use board service
            from services.board_service import board_service
            return board_service.create_visual_board(game_state)

        except Exception as e:
            logger.error(f"Error getting visual board: {e}")
            # Fallback to simple board
            return self._get_simple_board(game_code, user_id)

    def _get_simple_board(self, game_code: str, user_id: int = None) -> str:
        """Get simple board as fallback"""
        try:
            game = self.get_game_by_code(game_code)
            if not game:
                return "❌ Game not found!"

            board_text = "🎲 *LUDO GAME* 🎲\n\n"
            board_text += f"*Game Code:* `{game_code}`\n"
            board_text += f"*Status:* {game.status.title()}\n\n"

            # Add players info
            for player in game.players:
                color = player.color
                tokens = player.pieces_position or [-1, -1, -1, -1]
                
                player_type = "👤 Human" if player.user_id > 0 else "🤖 Bot"
                color_emoji = {
                    'red': '🔴', 'blue': '🔵', 
                    'green': '🟢', 'yellow': '🟡'
                }.get(color, '🎯')
                
                board_text += f"{color_emoji} *{color.title()}* ({player_type}):\n"
                
                tokens_home = sum(1 for pos in tokens if pos == -1)
                tokens_board = sum(1 for pos in tokens if 0 <= pos < 52)
                tokens_path = sum(1 for pos in tokens if 52 <= pos < 57)
                tokens_finished = sum(1 for pos in tokens if pos == 57)
                
                board_text += f"   🏠{tokens_home} 🎯{tokens_board} 🛣️{tokens_path} ✅{tokens_finished}\n\n"

            # Add current turn
            if game.players and game.current_turn < len(game.players):
                current_player = game.players[game.current_turn]
                player_type = "👤 Your turn" if user_id and current_player.user_id == user_id else "🤖 Bot's turn"
                color_emoji = {
                    'red': '🔴', 'blue': '🔵', 
                    'green': '🟢', 'yellow': '🟡'
                }.get(current_player.color, '🎯')
                
                board_text += f"🎯 *Current Turn:* {player_type} {color_emoji}\n"

            # Add dice value
            if game.dice_value and game.dice_value > 0:
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
                dice_emoji = dice_emojis.get(game.dice_value, "🎲")
                board_text += f"🎲 *Last Dice:* {dice_emoji} {game.dice_value}\n"

            return board_text

        except Exception as e:
            logger.error(f"Error in _get_simple_board: {e}")
            return "🎲 Ludo Game - Board loading...\n\nClick refresh to try again"

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()
