from telegram import Update
from telegram.ext import ContextTypes
from services.user_service import UserService
from utils.logger import logger

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show user statistics"""
    try:
        user = update.effective_user
        logger.info(f"Stats command received from user: {user.id}")

        user_service = UserService()

        # Get or create user
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )

        # Get user statistics
        stats = user_service.get_user_stats(db_user.id)

        if not stats:
            await update.message.reply_text("❌ Could not retrieve your statistics.")
            user_service.close()
            return

        # Format the statistics message
        stats_message = format_stats_message(stats, user.first_name)

        user_service.close()
        await update.message.reply_text(stats_message)

    except Exception as e:
        logger.error(f"Error in stats_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while fetching your statistics.")

async def leaderboard_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboardgroup command - show group leaderboard"""
    try:
        user_service = UserService()
        leaderboard = user_service.get_leaderboard(scope='group', limit=10)

        leaderboard_message = format_leaderboard_message(leaderboard, "Group")

        user_service.close()
        await update.message.reply_text(leaderboard_message)

    except Exception as e:
        logger.error(f"Error in leaderboard_group_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while fetching leaderboard.")

async def leaderboard_global_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard_global command - show global leaderboard"""
    try:
        user_service = UserService()
        leaderboard = user_service.get_leaderboard(scope='global', limit=10)

        leaderboard_message = format_leaderboard_message(leaderboard, "Global")

        user_service.close()
        await update.message.reply_text(leaderboard_message)

    except Exception as e:
        logger.error(f"Error in leaderboard_global_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while fetching global leaderboard.")


def format_stats_message(stats: dict, username: str) -> str:
    """Format user statistics into a readable message"""
    user_info = stats['user_info']
    statistics = stats['statistics']
    achievements = stats['achievements']

    message = f"""
📊 {username}'s Statistics 📊

Player Info:
• Level: {user_info['level']} 🎯
• Experience: {user_info['experience']} XP
• Coins: {user_info['coins']} 🪙

Game Statistics:
• Total Games: {statistics['total_games']}
• Games Won: {statistics['games_won']} 🏆
• Games Lost: {statistics['games_lost']}
• Win Rate: {statistics['win_rate']}%
• Pieces Captured: {statistics['pieces_captured']} 🎯
• Total Moves: {statistics['total_moves']}
• Avg Moves/Game: {statistics['average_moves_per_game']}

"""

    if achievements:
        message += "Achievements Unlocked:\n"
        for achievement in achievements[:5]:
            message += f"• {achievement['icon']} {achievement['name']}\n"

        if len(achievements) > 5:
            message += f"• ... and {len(achievements) - 5} more!\n"
    else:
        message += "No achievements unlocked yet. Keep playing! 🎮\n"

    message += "\nUse /leaderboardgroup or /leaderboard_global to see rankings!"

    return message


def format_leaderboard_message(leaderboard: list, scope: str) -> str:
    """Format leaderboard into a readable message"""
    if not leaderboard:
        return f"📊 {scope} Leaderboard\n\nNo players found in the leaderboard yet. Be the first to play! 🎮"

    message = f"🏆 {scope} Leaderboard 🏆\n\n"

    for player in leaderboard:
        medal = ""
        if player['rank'] == 1:
            medal = "🥇"
        elif player['rank'] == 2:
            medal = "🥈"
        elif player['rank'] == 3:
            medal = "🥉"
        else:
            medal = "🔸"

        message += f"{medal} {player['rank']}. {player['username']}\n"
        message += f"   Level: {player['level']} | Win Rate: {player['win_rate']}% | Games: {player['total_games']}\n\n"

    message += "Play more games to climb the leaderboard! 🎯"

    return message
