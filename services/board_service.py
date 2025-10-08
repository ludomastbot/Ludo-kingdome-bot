import random
from typing import Dict, List, Tuple
from utils.logger import logger

class BoardService:
    def __init__(self):
        self.colors = ['red', 'blue', 'green', 'yellow']
        self.color_emojis = {
            'red': '🔴',
            'blue': '🔵', 
            'green': '🟢',
            'yellow': '🟡'
        }
        self.color_symbols = {
            'red': 'R',
            'blue': 'B', 
            'green': 'G',
            'yellow': 'Y'
        }
    
    def create_visual_board(self, game_state: Dict) -> str:
        """Create beautiful ASCII Ludo board"""
        try:
            board_text = "🎲 *LUDO GAME BOARD* 🎲\n\n"
            
            # Create the Ludo board using better ASCII art
            board_text += self._create_ascii_board(game_state)
            board_text += "\n" + self._get_player_status(game_state)
            
            return board_text
            
        except Exception as e:
            logger.error(f"Error creating visual board: {e}")
            return self.create_simple_board(game_state)

    def _create_ascii_board(self, game_state: Dict) -> str:
        """Create beautiful ASCII Ludo board"""
        board = """
    ┌─────────┬─────────┬─────────┐
    │ 🟥🟥     │ 🟦🟦     │         │
    │ 🟥🟥  R  │ 🟦🟦  B  │         │
    │         │         │         │
    ├─────────┼─────────┼─────────┤
    │ 🟩🟩     │  🏁    │ 🟨🟨     │
    │ 🟩🟩  G  │  HOME  │ 🟨🟨  Y  │
    │         │         │         │
    └─────────┴─────────┴─────────┘
"""
        
        # Add token positions
        if 'players' in game_state:
            token_positions = self._get_token_positions(game_state)
            board = self._place_tokens_on_board(board, token_positions)
        
        return "```" + board + "```"

    def _get_token_positions(self, game_state: Dict) -> Dict:
        """Get token positions for all players"""
        positions = {}
        
        for player in game_state['players']:
            color = player['color']
            tokens = player.get('tokens', [-1, -1, -1, -1])
            
            positions[color] = []
            for i, pos in enumerate(tokens):
                if pos == -1:
                    positions[color].append('home')
                elif 0 <= pos < 52:
                    positions[color].append(f'path_{pos}')
                elif pos >= 52:
                    positions[color].append(f'home_path_{pos-52}')
                else:
                    positions[color].append('home')
        
        return positions

    def _place_tokens_on_board(self, board: str, positions: Dict) -> str:
        """Place tokens on the ASCII board"""
        # This is simplified - in real implementation, we'd map positions to board coordinates
        # For now, just show tokens in home areas
        
        board_lines = board.split('\n')
        
        # Red tokens (top-left)
        if 'red' in positions:
            red_tokens = positions['red']
            home_count = sum(1 for pos in red_tokens if pos == 'home')
            if home_count > 0:
                board_lines[1] = board_lines[1].replace('🟥🟥', '🔴🔴' if home_count >= 2 else '🔴🟥')
                board_lines[2] = board_lines[2].replace('R', f'R({home_count})')
        
        # Blue tokens (top-right)  
        if 'blue' in positions:
            blue_tokens = positions['blue']
            home_count = sum(1 for pos in blue_tokens if pos == 'home')
            if home_count > 0:
                board_lines[1] = board_lines[1].replace('🟦🟦', '🔵🔵' if home_count >= 2 else '🔵🟦')
                board_lines[2] = board_lines[2].replace('B', f'B({home_count})')
        
        # Green tokens (bottom-left)
        if 'green' in positions:
            green_tokens = positions['green']
            home_count = sum(1 for pos in green_tokens if pos == 'home')
            if home_count > 0:
                board_lines[4] = board_lines[4].replace('🟩🟩', '🟢🟢' if home_count >= 2 else '🟢🟩')
                board_lines[5] = board_lines[5].replace('G', f'G({home_count})')
        
        # Yellow tokens (bottom-right)
        if 'yellow' in positions:
            yellow_tokens = positions['yellow']
            home_count = sum(1 for pos in yellow_tokens if pos == 'home')
            if home_count > 0:
                board_lines[4] = board_lines[4].replace('🟨🟨', '🟡🟡' if home_count >= 2 else '🟡🟨')
                board_lines[5] = board_lines[5].replace('Y', f'Y({home_count})')
        
        return '\n'.join(board_lines)

    def _get_player_status(self, game_state: Dict) -> str:
        """Get detailed player status"""
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
                    f"{self.color_emojis[color]} *{color.title()}* ({player_type}):\n"
                    f"   🏠 Home: {tokens_home} | 🎯 Board: {tokens_board} | "
                    f"🛣️ Path: {tokens_home_path} | ✅ Finished: {tokens_finished}\n\n"
                )
        
        # Add game info
        if 'status' in game_state:
            status_text += f"🎮 *Status:* {game_state['status'].title()}\n"
        
        if 'current_player' in game_state:
            current_color = game_state['current_player']
            player_type = "👤 Your turn" if game_state.get('is_user_turn', False) else "🤖 Bot's turn"
            color_emoji = self.color_emojis.get(current_color, '🎯')
            status_text += f"🎯 *Current Turn:* {player_type} {color_emoji}\n"
        
        if 'dice_value' in game_state and game_state['dice_value'] > 0:
            dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
            dice_emoji = dice_emojis.get(game_state['dice_value'], "🎲")
            status_text += f"🎲 *Last Dice:* {dice_emoji} {game_state['dice_value']}\n"
        
        return status_text

    def create_simple_board(self, game_state: Dict) -> str:
        """Create simple but beautiful board"""
        try:
            board_text = "🎲 *LUDO GAME* 🎲\n\n"
            
            # Create a simple grid representation
            board_text += "```\n"
            board_text += "┌───┬───┬───┬───┐\n"
            board_text += "│R🏠│B🏠│   │   │\n"
            board_text += "├───┼───┼───┼───┤\n"
            board_text += "│G🏠│🏁 │Y🏠│   │\n"
            board_text += "└───┴───┴───┴───┘\n"
            board_text += "```\n\n"
            
            # Add player status
            board_text += self._get_player_status(game_state)
            
            return board_text
            
        except Exception as e:
            logger.error(f"Error creating simple board: {e}")
            return "🎲 *Ludo Game*\n\nBoard loading... 🎯"

    def create_detailed_board(self, game_state: Dict) -> str:
        """Create detailed board with path positions"""
        try:
            board_text = "🎲 *DETAILED LUDO BOARD* 🎲\n\n"
            
            if 'players' in game_state:
                for player in game_state['players']:
                    color = player['color']
                    tokens = player.get('tokens', [-1, -1, -1, -1])
                    
                    player_type = "👤 Human" if player.get('user_id', 0) > 0 else "🤖 Bot"
                    board_text += f"{self.color_emojis[color]} *{color.title()}* ({player_type}):\n"
                    
                    for i, pos in enumerate(tokens):
                        token_num = i + 1
                        if pos == -1:
                            status = "🏠 Home"
                        elif pos == 57:
                            status = "✅ FINISHED!"
                        elif pos >= 52:
                            path_pos = pos - 51
                            status = f"🛣️ Home Path ({path_pos}/6)"
                        else:
                            status = f"🎯 Position {pos + 1}"
                        
                        board_text += f"   Token {token_num}: {status}\n"
                    
                    board_text += "\n"
            
            # Add game info
            if 'status' in game_state:
                board_text += f"🎮 *Status:* {game_state['status'].title()}\n"
            
            if 'current_player' in game_state:
                current_color = game_state['current_player']
                player_type = "👤 Your turn" if game_state.get('is_user_turn', False) else "🤖 Bot's turn"
                color_emoji = self.color_emojis.get(current_color, '🎯')
                board_text += f"🎯 *Current Turn:* {player_type} {color_emoji}\n"
            
            if 'dice_value' in game_state and game_state['dice_value'] > 0:
                dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
                dice_emoji = dice_emojis.get(game_state['dice_value'], "🎲")
                board_text += f"🎲 *Last Dice:* {dice_emoji} {game_state['dice_value']}\n"
            
            return board_text
            
        except Exception as e:
            logger.error(f"Error creating detailed board: {e}")
            return self.create_simple_board(game_state)

# Singleton instance
board_service = BoardService()
