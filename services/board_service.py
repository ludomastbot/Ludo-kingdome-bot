import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
import random
from database.models import Game, GamePlayer, SessionLocal
from utils.logger import logger

class BoardService:
    def __init__(self):
        self.db = SessionLocal()
    
    def get_board_state(self, game_code: str):
        """Get current board state for a game"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return None
            
            return game.board_state
            
        except Exception as e:
            logger.error(f"Error getting board state: {e}")
            return None
    
    def roll_dice(self, game_code: str, user_id: int):
        """Roll dice for a player's turn"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return None, "Game not found"
            
            if game.status != 'active':
                return None, "Game not started or finished"
            
            # Check if it's user's turn
            current_player = self._get_current_player(game)
            if not current_player or current_player.user_id != user_id:
                return None, "Not your turn"
            
            # Roll dice (1-6)
            dice_value = random.randint(1, 6)
            game.dice_value = dice_value
            
            # Get possible moves
            possible_moves = self._get_possible_moves(game, current_player, dice_value)
            
            self.db.commit()
            
            logger.info(f"User {user_id} rolled {dice_value} in game {game_code}")
            return dice_value, possible_moves
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rolling dice: {e}")
            return None, str(e)
    
    def _get_current_player(self, game: Game):
        """Get current player based on turn order"""
        if game.status != 'active':
            return None
            
        players = self.db.query(GamePlayer).filter(
            GamePlayer.game_id == game.id
        ).order_by(GamePlayer.player_order).all()
        
        if not players:
            return None
        
        current_index = (game.current_turn - 1) % len(players)
        return players[current_index]
    
    def _get_possible_moves(self, game: Game, player: GamePlayer, dice_value: int):
        """Get possible moves for a player"""
        possible_moves = []
        pieces_position = player.pieces_position
        
        for i, position in enumerate(pieces_position):
            if self._is_valid_move(position, dice_value, player.color):
                possible_moves.append({
                    'piece_index': i,
                    'current_position': position,
                    'new_position': self._calculate_new_position(position, dice_value, player.color),
                    'is_capture': self._is_capture_move(position, dice_value, player.color, game)
                })
        
        return possible_moves
    
    def _is_valid_move(self, current_position: int, dice_value: int, color: str):
        """Check if move is valid"""
        # Piece at home, need 6 to start
        if current_position == 0:
            return dice_value == 6
        
        # Piece on board, check if move is within bounds
        new_position = self._calculate_new_position(current_position, dice_value, color)
        return new_position <= 57  # 57 is finish position
    
    def _calculate_new_position(self, current_position: int, dice_value: int, color: str):
        """Calculate new position after move"""
        if current_position == 0:  # At home
            # Starting positions for each color
            start_positions = {'red': 1, 'blue': 14, 'green': 27, 'yellow': 40}
            return start_positions.get(color, 1)
        
        # Normal move on board
        new_position = current_position + dice_value
        
        # Handle home stretch for each color
        color_ranges = {
            'red': (52, 57),    # Positions 52-57 are red home stretch
            'blue': (13, 18),   # Positions 13-18 are blue home stretch  
            'green': (26, 31),  # Positions 26-31 are green home stretch
            'yellow': (39, 44)  # Positions 39-44 are yellow home stretch
        }
        
        start, end = color_ranges.get(color, (0, 0))
        if start <= current_position < end:
            # In home stretch, can only move forward
            return min(new_position, 57)  # Max 57 is finish
        
        # Handle board wrapping (52 positions total)
        if new_position > 52:
            new_position = new_position - 52
        
        return new_position
    
    def _is_capture_move(self, current_position: int, dice_value: int, color: str, game: Game):
        """Check if move will capture opponent's piece"""
        if current_position == 0:  # Can't capture from home
            return False
            
        new_position = self._calculate_new_position(current_position, dice_value, color)
        
        # Check all opponent pieces at new position
        players = self.db.query(GamePlayer).filter(
            GamePlayer.game_id == game.id,
            GamePlayer.color != color
        ).all()
        
        for player in players:
            if new_position in player.pieces_position:
                # Check if it's not a safe position
                safe_positions = [1, 9, 14, 22, 27, 35, 40, 48]  # Starting positions are safe
                if new_position not in safe_positions:
                    return True
        
        return False
    
    def move_piece(self, game_code: str, user_id: int, piece_index: int):
        """Move a piece on the board"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return False, "Game not found"
            
            # Check if it's user's turn
            current_player = self._get_current_player(game)
            if not current_player or current_player.user_id != user_id:
                return False, "Not your turn"
            
            # Check if dice was rolled
            if game.dice_value == 0:
                return False, "Roll dice first"
            
            # Get possible moves
            possible_moves = self._get_possible_moves(game, current_player, game.dice_value)
            move_to_execute = None
            
            for move in possible_moves:
                if move['piece_index'] == piece_index:
                    move_to_execute = move
                    break
            
            if not move_to_execute:
                return False, "Invalid move"
            
            # Execute the move
            self._execute_move(game, current_player, move_to_execute)
            
            # Check for win condition
            if self._check_win_condition(current_player):
                game.status = 'finished'
                self.db.commit()
                return True, "You won the game! 🎉"
            
            # Move to next turn if not 6
            if game.dice_value != 6:
                game.current_turn += 1
                players_count = len(self.db.query(GamePlayer).filter(GamePlayer.game_id == game.id).all())
                if game.current_turn > players_count:
                    game.current_turn = 1
            
            game.dice_value = 0  # Reset dice
            self.db.commit()
            
            return True, f"Moved piece to position {move_to_execute['new_position']}"
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error moving piece: {e}")
            return False, str(e)
    
    def _execute_move(self, game: Game, player: GamePlayer, move: dict):
        """Execute a move on the board"""
        pieces_position = player.pieces_position
        old_position = pieces_position[move['piece_index']]
        new_position = move['new_position']
        
        # Update piece position
        pieces_position[move['piece_index']] = new_position
        player.pieces_position = pieces_position
        
        # Handle capture
        if move['is_capture']:
            self._handle_capture(game, new_position, player.color)
    
    def _handle_capture(self, game: Game, position: int, capturing_color: str):
        """Handle piece capture - send opponent's piece back to home"""
        try:
            # Find opponent players
            opponents = self.db.query(GamePlayer).filter(
                GamePlayer.game_id == game.id,
                GamePlayer.color != capturing_color
            ).all()
            
            for opponent in opponents:
                pieces = opponent.pieces_position
                for i, piece_pos in enumerate(pieces):
                    if piece_pos == position:
                        # Send piece back to home
                        pieces[i] = 0
                        opponent.pieces_position = pieces
                        logger.info(f"Piece captured: {opponent.color} piece at position {position}")
                        break
                        
        except Exception as e:
            logger.error(f"Error handling capture: {e}")
    
    def _check_win_condition(self, player: GamePlayer):
        """Check if player has won - all pieces at finish"""
        return all(pos == 57 for pos in player.pieces_position)
    
    def get_game_status(self, game_code: str):
        """Get complete game status"""
        try:
            game = self.db.query(Game).filter(Game.game_code == game_code).first()
            if not game:
                return None
            
            players = self.db.query(GamePlayer).filter(GamePlayer.game_id == game.id).all()
            current_player = self._get_current_player(game)
            
            return {
                'game_code': game.game_code,
                'status': game.status,
                'current_turn': game.current_turn,
                'dice_value': game.dice_value,
                'current_player': current_player.user_id if current_player else None,
                'players': [
                    {
                        'user_id': p.user_id,
                        'color': p.color,
                        'pieces_position': p.pieces_position,
                        'player_order': p.player_order
                    }
                    for p in players
                ],
                'board_state': game.board_state
            }
            
        except Exception as e:
            logger.error(f"Error getting game status: {e}")
            return None
    
    def close(self):
        """Close database connection"""
        self.db.close()
