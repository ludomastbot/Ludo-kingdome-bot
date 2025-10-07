from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import logger

async def ludotwobot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludotwobot command - 1 human vs 1 bot"""
    try:
        await update.message.reply_text(
            "🤖 *1 vs 1 Bot Game* 🤖\n\n"
            "This feature will be available in the next update!\n\n"
            "For now, you can:\n"
            "• Play with friends using /ludotwo\n"
            "• Test the game mechanics\n"
            "• Bot AI is being optimized\n\n"
            "Stay tuned! 🚀",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in ludotwobot_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")

async def ludo_two_two_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludo_two_two command - 2 humans vs 2 bots"""
    try:
        await update.message.reply_text(
            "🤖 *2 vs 2 Team Bot Game* 🤖\n\n"
            "This feature will be available in the next update!\n\n"
            "For now, you can:\n"
            "• Play with friends using /ludofour\n"
            "• Test the multiplayer features\n"
            "• Bot AI is being optimized\n\n"
            "Stay tuned! 🚀",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in ludo_two_two_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")
