import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.game_handlers import format_join_board_message

def test_message_formatting():
    """Test message formatting without markdown issues"""
    test_game_info = {
        'game_code': 'TEST12',
        'game_type': 'ludotwo',
        'status': 'waiting',
        'max_players': 2,
        'current_players': 1,
        'players': [
            {'user_id': 1, 'username': 'testuser', 'color': 'red', 'player_order': 1, 'is_ready': False}
        ],
        'created_at': '2025-10-07'
    }
    
    message = format_join_board_message(test_game_info, 'ludotwo')
    print("=== TEST MESSAGE ===")
    print(message)
    print("=== END ===")
    
    # Check for common markdown issues
    issues = []
    if message.count('*') % 2 != 0:
        issues.append("Unbalanced asterisks")
    if message.count('_') % 2 != 0:
        issues.append("Unbalanced underscores")
    if '`' in message and message.count('`') % 2 != 0:
        issues.append("Unbalanced backticks")
    
    if issues:
        print(f"❌ Markdown issues found: {issues}")
        return False
    else:
        print("✅ No markdown issues found")
        return True

if __name__ == "__main__":
    test_message_formatting()
