import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update

from config import config
from utils.logger import logger
from database.models import init_db
from handlers.start_handler import start_handler, help_handler
from handlers.stats_handler import stats_handler, leaderboard_group_handler, leaderboard_global_handler
from handlers.game_handlers import (
    play_handler, ludotwo_handler, ludothree_handler, ludofour_handler, 
    join_color_handler, begin_game_handler
)

class LudoBot:
    def __init__(self):
        self.application = None
        self.logger = logger
        
    def initialize(self):
        """Initialize the bot with all handlers"""
        try:
            # Initialize database
            init_db()
            self.logger.info("Database initialized successfully")
            
            # Create Application
            self.application = Application.builder().token(config.BOT_TOKEN).build()
            
            # Add handlers
            self._add_handlers()
            
            self.logger.info("Ludo Bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _add_handlers(self):
        """Add all command and message handlers"""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(CommandHandler("stats", stats_handler))
        self.application.add_handler(CommandHandler("leaderboardgroup", leaderboard_group_handler))
        self.application.add_handler(CommandHandler("leaderboard_global", leaderboard_global_handler))
        
        # Game commands
        self.application.add_handler(CommandHandler("play", play_handler))
        self.application.add_handler(CommandHandler("ludotwo", ludotwo_handler))
        self.application.add_handler(CommandHandler("ludothree", ludothree_handler))
        self.application.add_handler(CommandHandler("ludofour", ludofour_handler))
        self.application.add_handler(CommandHandler("begin", begin_game_handler))
        
        # Callback handlers for buttons
        self.application.add_handler(CallbackQueryHandler(join_color_handler, pattern="^join_"))
        
        # Add more handlers here as we build them
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
        
        self.logger.info("All handlers added successfully")
    
    def _error_handler(self, update: Update, context):
        """Log errors caused by updates"""
        self.logger.error(f"Exception while handling an update: {context.error}")
    
    def run(self):
        """Run the bot"""
        if not self.application:
            self.initialize()
        
        self.logger.info("Starting Ludo Bot...")
        
        # Start the Bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function to start the bot"""
    bot = LudoBot()
    bot.run()

if __name__ == "__main__":
    main()
