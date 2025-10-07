import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.board_service import BoardService
from services.game_service import GameService
from services.user_service import UserService
from database.models import init_db

def test_board_functionality():
    print("Testing board functionality...")
    
    try:
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Create test user and game
        user_service = UserService()
        test_user = user_service.get_or_create_user(
            telegram_id=999888777,
            username="boardtest",
            first_name="Board",
            last_name="Test"
        )
        
        game_service = GameService()
        game = game_service.create_game('ludotwo', test_user.id, 2)
        print(f"✅ Game created: {game.game_code}")
        
        # Start the game
        game_service.start_game(game.game_code, test_user.id)
        
        # Test board service
        board_service = BoardService()
        
        # Test dice roll
        dice_value, moves = board_service.roll_dice(game.game_code, test_user.id)
        print(f"✅ Dice rolled: {dice_value}")
        print(f"✅ Possible moves: {moves}")
        
        # Test game status
        status = board_service.get_game_status(game.game_code)
        print(f"✅ Game status: {status['status']}")
        print(f"✅ Current turn: {status['current_turn']}")
        
        user_service.close()
        game_service.close()
        board_service.close()
        
        print("🎉 All board tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Board test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_board_functionality()
