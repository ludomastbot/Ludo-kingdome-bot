import random
from typing import List, Dict, Tuple
from utils.logger import logger
from services.game_service import GameService
from database.models import SessionLocal

class BotService:
    def __init__(self):
        self.bot_names = {
            -1: "Smart Bot",
            -2: "Ludo Pro", 
            -3: "Game Master",
            -4: "AI Player"
        }
        self.db = SessionLocal()
    
    def play_turn(self, game_code: str) -> bool:
        """Play a turn for bot player - UPDATED VERSION"""
        try:
            game_service = GameService()
            game = game_service.get_game_by_code(game_code)
            
            if not game or game.status != 'active':
                game_service.close()
                return False
            
            current_player = game.players[game.current_turn]
            
            # Only bots can use this (negative user_id)
            if current_player.user_id >= 0:
                game_service.close()
                return False
            
            # Roll dice
            dice_value = random.randint(1, 6)
            game.dice_value = dice_value
            game_service.db.commit()
            
            bot_name = self.bot_names.get(current_player.user_id, "Bot")
            logger.info(f"🤖 {bot_name} rolled {dice_value}")
            
            # Get current token positions
            tokens = current_player.pieces_position or [-1, -1, -1, -1]
            moved = False
            
            # Bot move logic with priorities
            moved_token_index = self._choose_best_move(tokens, dice_value, current_player.color)
            
            if moved_token_index is not None:
                # Move the selected token
                new_position = self._calculate_new_position(tokens[moved_token_index], dice_value, current_player.color)
                tokens[moved_token_index] = new_position
                current_player.pieces_position = tokens
                moved = True
                
                logger.info(f"🤖 {bot_name} moved token {moved_token_index + 1} from {tokens[moved_token_index]} to {new_position}")
            
            game_service.db.commit()
            
            # Move to next turn if no extra turn
            if dice_value != 6 or not moved:
                game.current_turn = (game.current_turn + 1) % len(game.players)
                game_service.db.commit()
                
                logger.info(f"🤖 {bot_name} turn completed. Next player: {game.current_turn}")
            
            game_service.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in bot play_turn: {e}")
            return False

    def _choose_best_move(self, tokens: List[int], dice_value: int, color: str) -> int:
        """Choose the best token to move - SMART BOT LOGIC"""
        available_moves = []
        
        for i, token_pos in enumerate(tokens):
            if self._can_move_token(token_pos, dice_value, color):
                available_moves.append(i)
        
        if not available_moves:
            return None
        
        # SMART MOVE PRIORITIES:
        
        # 1. FINISHING MOVE: If token can reach home
        for i in available_moves:
            if tokens[i] >= 100 and tokens[i] + dice_value >= 106:
                return i
        
        # 2. CAPTURE MOVE: If token can capture opponent (position 1, 9, 14, 22, 27, 35, 40, 48)
        capture_positions = [1, 9, 14, 22, 27, 35, 40, 48]
        for i in available_moves:
            if tokens[i] >= 0 and (tokens[i] + dice_value) in capture_positions:
                return i
        
        # 3. START NEW TOKEN: If rolled 6 and can start new token
        if dice_value == 6:
            for i in available_moves:
                if tokens[i] == -1:
                    return i
        
        # 4. MOVE FARTHEST TOKEN: Move token that's closest to home
        farthest_token = None
        max_position = -2  # Start from -2 to handle -1 positions
        
        for i in available_moves:
            if tokens[i] > max_position:
                max_position = tokens[i]
                farthest_token = i
        
        return farthest_token

    def _can_move_token(self, token_position: int, dice_value: int, color: str) -> bool:
        """Check if bot can move a token - IMPROVED LOGIC"""
        # Token in home and rolled 6
        if token_position == -1 and dice_value == 6:
            return True
        
        # Token on main board
        elif 0 <= token_position < 100:
            return True
        
        # Token in home path
        elif 100 <= token_position < 106:
            new_pos = token_position + dice_value
            return new_pos <= 106  # Can only move if not exceeding home
        
        return False

    def _calculate_new_position(self, current_position: int, dice_value: int, color: str) -> int:
        """Calculate new position after move - IMPROVED LOGIC"""
        # Starting from home
        if current_position == -1 and dice_value == 6:
            return self._get_start_position(color)
        
        # Moving on main board
        elif 0 <= current_position < 100:
            new_pos = current_position + dice_value
            
            # Check if entering home path
            if new_pos >= 52:  # Home path entry point
                home_path_start = 100
                home_path_progress = new_pos - 52
                return home_path_start + home_path_progress
            else:
                return new_pos
        
        # Moving in home path
        elif 100 <= current_position < 106:
            new_pos = current_position + dice_value
            return min(new_pos, 106)  # Max home position
        
        return current_position

    def _get_start_position(self, color: str) -> int:
        """Get starting position based on color"""
        start_positions = {
            'red': 0,
            'blue': 13,
            'green': 26,
            'yellow': 39
        }
        return start_positions.get(color, 0)

    def is_bot_user(self, user_id: int) -> bool:
        """Check if user is a bot (negative user_id)"""
        return user_id < 0

    def process_all_bot_turns(self, game_code: str) -> bool:
        """Process turns for all consecutive bot players - UPDATED"""
        try:
            game_service = GameService()
            game = game_service.get_game_by_code(game_code)
            
            if not game or game.status != 'active':
                game_service.close()
                return False
            
            # Process current bot turn and consecutive bot turns
            processed = False
            
            while True:
                current_player = game.players[game.current_turn]
                
                # Break if current player is human
                if not self.is_bot_user(current_player.user_id):
                    break
                
                # Play bot turn
                success = self.play_turn(game_code)
                processed = processed or success
                
                # Refresh game data
                game = game_service.get_game_by_code(game_code)
                if not game or game.status != 'active':
                    break
            
            game_service.close()
            return processed
            
        except Exception as e:
            logger.error(f"❌ Error processing bot turns: {e}")
            return False

    def get_bot_name(self, user_id: int) -> str:
        """Get bot name from user_id"""
        return self.bot_names.get(user_id, f"Bot {abs(user_id)}")

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()

# Singleton instance
bot_service = BotService()
