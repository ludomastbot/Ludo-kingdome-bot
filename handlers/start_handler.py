from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import logger

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        logger.info(f"Start command received from user: {user.id}")
        
        welcome_message = """
🎲 Welcome to Ludo Bot! 🎲

Available Commands:

🎮 Game Commands:
/play - Single player vs Computer
/ludotwo - 2 Player Game
/ludothree - 3 Player Game
/ludofour - 4 Player Game

🤖 Bot Game Commands:
/ludotwobot - 1 Human vs 1 Bot
/ludo_two_two - 2 Humans vs 2 Bots

📊 Info Commands:
/stats - Your Statistics
/leaderboardgroup - Group Leaderboard  
/leaderboard_global - Global Leaderboard
/help - All Commands List

Join the fun and play Ludo with friends! 🎯
        """
        
        await update.message.reply_text(welcome_message)
        
    except Exception as e:
        logger.error(f"Error in start_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred. Please try again.")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        help_message = """
🆘 Ludo Bot Help 🆘

Basic Commands:
/start - Start the bot
/help - Show this help message

🎮 Game Commands:
/play - Single player vs Computer
/ludotwo - 2 Player Game
/ludothree - 3 Player Game  
/ludofour - 4 Player Game

🤖 Bot Game Commands:
/ludotwobot - 1 Human vs 1 Bot (Auto-start)
/ludo_two_two - 2 Humans vs 2 Bots (Auto-start)

📊 Info Commands:
/stats - Your game statistics
/leaderboardgroup - Group rankings
/leaderboard_global - Global rankings

🎯 How to Play:
1. Use game commands to create a game
2. Players join using color buttons
3. Use /begin GAMECODE to start
4. Click dice to roll and pieces to move

Enjoy playing! 🎲
        """
        
        await update.message.reply_text(help_message)
        
    except Exception as e:
        logger.error(f"Error in help_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")
