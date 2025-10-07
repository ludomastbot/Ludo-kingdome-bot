import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import init_db, SessionLocal
from services.game_service import GameService
from services.user_service import UserService

def test_game_creation():
    print("Testing game creation...")

    try:
        # Initialize database
        init_db()
        print("✅ Database initialized")

        # Create test user
        user_service = UserService()
        test_user = user_service.get_or_create_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Test user created: {test_user.id}")

        # Create game
        game_service = GameService()
        game = game_service.create_game("ludotwo", test_user.id, 2)
        print(f"✅ Game created: {game.game_code}")

        # Join user to game
        game, message = game_service.join_game(game.game_code, test_user.id, 'red')
        print(f"✅ User joined game: {message}")

        # Get game info
        game_info = game_service.get_game_info(game.game_code)
        print(f"✅ Game info: {game_info}")

        user_service.close()
        game_service.close()

        print("🎉 All game tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error in game test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_game_creation()
