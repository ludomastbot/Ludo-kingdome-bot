import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from services.board_service import BoardService
from services.game_service import GameService
from database.models import SessionLocal
from utils.logger import logger

class BotService:
    def __init__(self):
        self.db = SessionLocal()

    def make_bot_move(self, game_code: str, bot_user_id: int):
        """Make a move for bot player"""
        try:
            board_service = BoardService()

            # Roll dice for bot
            dice_value, possible_moves = board_service.roll_dice(game_code, bot_user_id)

            if dice_value is None or not possible_moves:
                logger.info(f"Bot {bot_user_id} has no valid moves, passing turn")
                board_service.close()
                return False, "No valid moves"

            # Choose best move (simple AI)
            selected_move = self._choose_best_move(possible_moves, dice_value)

            if selected_move:
                # Execute the move
                success, message = board_service.move_piece(game_code, bot_user_id, selected_move['piece_index'])

                if success:
                    logger.info(f"Bot {bot_user_id} moved piece {selected_move['piece_index']} in game {game_code}")
                    board_service.close()
                    return True, f"Bot moved piece from {selected_move['current_position']} to {selected_move['new_position']}"
                else:
                    logger.error(f"Bot move failed: {message}")
                    board_service.close()
                    return False, message
            else:
                board_service.close()
                return False, "No move selected"

        except Exception as e:
            logger.error(f"Error in bot move: {e}")
            return False, str(e)

    def _choose_best_move(self, possible_moves, dice_value):
        """Choose the best move from available options"""
        if not possible_moves:
            return None

        # Priority 1: Capture opponent's piece
        capture_moves = [move for move in possible_moves if move['is_capture']]
        if capture_moves:
            return random.choice(capture_moves)

        # Priority 2: Move piece to finish
        finish_moves = [move for move in possible_moves if move['new_position'] == 57]
        if finish_moves:
            return random.choice(finish_moves)

        # Priority 3: Start a new piece (if 6 rolled)
        if dice_value == 6:
            start_moves = [move for move in possible_moves if move['current_position'] == 0]
            if start_moves:
                return random.choice(start_moves)

        # Priority 4: Move piece that's farthest along
        farthest_move = max(possible_moves, key=lambda x: x['new_position'])
        return farthest_move

    def is_bot_user(self, user_id: int):
        """Check if user is a bot"""
        try:
            from services.user_service import UserService
            user_service = UserService()
            user = user_service.get_or_create_user(telegram_id=user_id)
            is_bot = user.telegram_id < 0  # Negative IDs are bots
            user_service.close()  # Service close karein
            return is_bot
        except:
            return False

    def process_bot_turns(self, game_code: str):
        """Process turns for all bot players in the game"""
        try:
            game_service = GameService()
            game_info = game_service.get_game_info(game_code)

            if not game_info or game_info['status'] != 'active':
                game_service.close()
                return

            # Get current turn player
            board_service = BoardService()
            game_status = board_service.get_game_status(game_code)
            current_player_id = game_status['current_player']

            # Check if current player is bot
            if current_player_id and self.is_bot_user(current_player_id):
                success, message = self.make_bot_move(game_code, current_player_id)
                logger.info(f"Bot turn processed: {success} - {message}")

                # If bot moved successfully, check if next player is also bot
                if success:
                    self._process_next_bot_turn(game_code)

            board_service.close()
            game_service.close()

        except Exception as e:
            logger.error(f"Error processing bot turns: {e}")

    def _process_next_bot_turn(self, game_code: str):
        """Recursively process next bot turns"""
        try:
            # Small delay to make it feel natural
            import time
            time.sleep(2)

            board_service = BoardService()
            game_status = board_service.get_game_status(game_code)

            if game_status['status'] != 'active':
                board_service.close()
                return

            current_player_id = game_status['current_player']

            # Check if next player is also bot
            if current_player_id and self.is_bot_user(current_player_id):
                success, message = self.make_bot_move(game_code, current_player_id)
                logger.info(f"Next bot turn processed: {success} - {message}")

                # Continue if successful
                if success:
                    self._process_next_bot_turn(game_code)

            board_service.close()

        except Exception as e:
            logger.error(f"Error processing next bot turn: {e}")

    def close(self):
        """Close database connection"""
        self.db.close()
