from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import logger

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        logger.info(f"Start command received from user: {user.id}")
        
        welcome_message = """
🎲 *Welcome to Ludo Bot!* 🎲

*Available Commands:*
/play - Single player vs Computer
/ludotwo - 2 Player Game  
/ludothree - 3 Player Game
/ludofour - 4 Player Game

/stats - Your Statistics
/leaderboardgroup - Group Leaderboard
/leaderboard_global - Global Leaderboard
/help - All Commands List

Join the fun and play Ludo with friends! 🎯
        """
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in start_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        help_message = """
🆘 *Ludo Bot Help* 🆘

*Basic Commands:*
/start - Start the bot
/help - Show this help message

*Game Commands (Coming Soon):*
/play, /ludotwo, /ludothree, /ludofour

*More features coming soon!*
        """
        
        await update.message.reply_text(help_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")
