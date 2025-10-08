import random
from typing import Dict, List, Tuple
from utils.logger import logger

class BoardService:
    def __init__(self):
        self.board_size = 15  # 15x15 grid
        self.colors = ['red', 'blue', 'green', 'yellow']
        self.color_emojis = {
            'red': '🔴',
            'blue': '🔵', 
            'green': '🟢',
            'yellow': '🟡'
        }
        
        # Initialize board paths
        self._initialize_paths()
    
    def _initialize_paths(self):
        """Initialize proper Ludo board paths"""
        # Home positions (start areas)
        self.home_positions = {
            'red': [(1, 1), (1, 2), (2, 1), (2, 2)],
            'blue': [(1, 12), (1, 13), (2, 12), (2, 13)],
            'green': [(12, 1), (12, 2), (13, 1), (13, 2)],
            'yellow': [(12, 12), (12, 13), (13, 12), (13, 13)]
        }
        
        # Main board path (circular path)
        self.main_path = self._create_main_path()
        
        # Starting positions
        self.start_positions = {
            'red': (6, 1),
            'blue': (1, 8), 
            'green': (8, 13),
            'yellow': (13, 6)
        }
        
        # Home paths (winning paths)
        self.home_paths = {
            'red': [(6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (7, 6)],
            'blue': [(2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (6, 7)],
            'green': [(8, 12), (8, 11), (8, 10), (8, 9), (8, 8), (7, 8)],
            'yellow': [(12, 6), (11, 6), (10, 6), (9, 6), (8, 6), (8, 7)]
        }
    
    def _create_main_path(self) -> List[Tuple[int, int]]:
        """Create the main circular path for Ludo board"""
        path = []
        
        # Red to Blue (top)
        for col in range(2, 8):
            path.append((1, col))
        
        # Blue to Green (right)  
        for row in range(2, 8):
            path.append((row, 13))
        
        # Green to Yellow (bottom)
        for col in range(12, 6, -1):
            path.append((13, col))
        
        # Yellow to Red (left)
        for row in range(12, 6, -1):
            path.append((row, 1))
        
        return path
    
    def create_visual_board(self, game_state: Dict) -> str:
        """Create proper visual Ludo board"""
        try:
            # Create empty board grid
            board = [['⬜' for _ in range(15)] for _ in range(15)]
            
            # Draw main path
            for row, col in self.main_path:
                if 0 <= row < 15 and 0 <= col < 15:
                    board[row][col] = '⬛'
            
            # Draw colored home areas
            for color, positions in self.home_positions.items():
                for row, col in positions:
                    if color == 'red':
                        board[row][col] = '🟥'
                    elif color == 'blue':
                        board[row][col] = '🟦' 
                    elif color == 'green':
                        board[row][col] = '🟩'
                    elif color == 'yellow':
                        board[row][col] = '🟨'
            
            # Draw home paths
            for color, path in self.home_paths.items():
                for row, col in path:
                    if color == 'red':
                        board[row][col] = '🟥'
                    elif color == 'blue':
                        board[row][col] = '🟦'
                    elif color == 'green':
                        board[row][col] = '🟩'
                    elif color == 'yellow':
                        board[row][col] = '🟨'
            
            # Draw center star
            for row in range(6, 9):
                for col in range(6, 9):
                    board[row][col] = '⭐'
            
            # Place tokens on board
            if 'players' in game_state:
                for player in game_state['players']:
                    color = player['color']
                    tokens = player.get('tokens', [-1, -1, -1, -1])
                    
                    for i, token_pos in enumerate(tokens):
                        if token_pos >= 0:  # Token on board
                            row, col = self._get_board_position(color, token_pos)
                            if 0 <= row < 15 and 0 <= col < 15:
                                board[row][col] = self.color_emojis[color]
            
            # Convert board to string
            board_text = "🎲 *LUDO GAME BOARD* 🎲\n\n"
            
            # Add column numbers
            board_text += "   "
            for col in range(15):
                board_text += f"{col:2d}"
            board_text += "\n"
            
            # Add board with row numbers
            for row in range(15):
                board_text += f"{row:2d} "
                for col in range(15):
                    board_text += board[row][col]
                board_text += f" {row:2d}\n"
            
            # Add column numbers at bottom
            board_text += "   "
            for col in range(15):
                board_text += f"{col:2d}"
            board_text += "\n\n"
            
            # Add player status
            board_text += self._get_player_status(game_state)
            
            return board_text
            
        except Exception as e:
            logger.error(f"Error creating visual board: {e}")
            return self.create_simple_board(game_state)
    
    def _get_board_position(self, color: str, position: int) -> Tuple[int, int]:
        """Get board coordinates for token position"""
        if position < 0:  # In home
            return (-1, -1)
        
        # Main path positions (0-51)
        if position < 52:
            start_idx = {'red': 0, 'blue': 13, 'green': 26, 'yellow': 39}[color]
            actual_idx = (start_idx + position) % 52
            return self.main_path[actual_idx]
        
        # Home path positions (52-57)
        elif position < 58:
            home_path_idx = position - 52
            if home_path_idx < len(self.home_paths[color]):
                return self.home_paths[color][home_path_idx]
        
        return (-1, -1)
    
    def _get_player_status(self, game_state: Dict) -> str:
        """Get player status text"""
        status_text = ""
        
        if 'players' in game_state:
            for player in game_state['players']:
                color = player['color']
                tokens = player.get('tokens', [-1, -1, -1, -1])
                
                tokens_home = sum(1 for pos in tokens if pos == -1)
                tokens_board = sum(1 for pos in tokens if 0 <= pos < 52)
                tokens_home_path = sum(1 for pos in tokens if 52 <= pos < 57)
                tokens_finished = sum(1 for pos in tokens if pos == 57)
                
                player_type = "👤 Human" if player.get('user_id', 0) > 0 else "🤖 Bot"
                
                status_text += (
                    f"{self.color_emojis[color]} {color.title()} ({player_type}):\n"
                    f"   🏠 Home: {tokens_home} | 🎯 Board: {tokens_board} | "
                    f"🛣️ Path: {tokens_home_path} | ✅ Finished: {tokens_finished}\n\n"
                )
        
        # Add game status
        if 'status' in game_state:
            status_text += f"🎮 Status: {game_state['status'].title()}\n"
        
        # Add current turn
        if 'current_player' in game_state:
            current_color = game_state['current_player']
            player_type = "👤 Your turn" if game_state.get('is_user_turn', False) else "🤖 Bot's turn"
            status_text += f"🎯 Current Turn: {player_type} ({current_color.title()})\n"
        
        # Add dice value
        if 'dice_value' in game_state and game_state['dice_value'] > 0:
            dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
            dice_emoji = dice_emojis.get(game_state['dice_value'], "🎲")
            status_text += f"🎲 Last Dice: {dice_emoji} {game_state['dice_value']}\n"
        
        return status_text
    
    def create_simple_board(self, game_state: Dict) -> str:
        """Create simple board when visual fails"""
        try:
            board_text = "🎲 *LUDO GAME* 🎲\n\n"
            
            if 'players' in game_state:
                for player in game_state['players']:
                    color = player['color']
                    tokens = player.get('tokens', [-1, -1, -1, -1])
                    
                    player_type = "👤 Human" if player.get('user_id', 0) > 0 else "🤖 Bot"
                    board_text += f"{self.color_emojis[color]} {color.title()} ({player_type}):\n"
                    
                    for i, pos in enumerate(tokens):
                        if pos == -1:
                            status = "🏠 Home"
                        elif pos == 57:
                            status = "✅ Finished"
                        elif pos >= 52:
                            status = f"🛣️ Path ({pos-51}/6)"
                        else:
                            status = f"🎯 Position {pos+1}"
                        
                        board_text += f"   Token {i+1}: {status}\n"
                    
                    board_text += "\n"
            
            # Add game info
            if 'status' in game_state:
                board_text += f"🎮 Status: {game_state['status'].title()}\n"
            
            if 'current_player' in game_state:
                current_color = game_state['current_player']
                player_type = "👤 Your turn" if game_state.get('is_user_turn', False) else "🤖 Bot's turn"
                board_text += f"🎯 Current Turn: {player_type} ({current_color.title()})\n"
            
            if 'dice_value' in game_state and game_state['dice_value'] > 0:
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
                dice_emoji = dice_emojis.get(game_state['dice_value'], "🎲")
                board_text += f"🎲 Last Dice: {dice_emoji} {game_state['dice_value']}\n"
            
            return board_text
            
        except Exception as e:
            logger.error(f"Error creating simple board: {e}")
            return "🎲 Ludo Game - Board loading...\n\nUse /board to refresh"

# Singleton instance
board_service = BoardService()
