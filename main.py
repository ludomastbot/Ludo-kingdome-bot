import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update

from config import config
from utils.logger import logger
from database.models import init_db

# Import all handlers
from handlers.start_handler import start_handler, help_handler
from handlers.stats_handler import stats_handler, leaderboard_group_handler, leaderboard_global_handler
from handlers.game_handlers import (
    play_handler, ludotwo_handler, ludothree_handler, ludofour_handler,
    join_color_handler
)
from handlers.gameplay_handlers import (
    begin_game_handler, roll_dice_handler, move_piece_handler,
    show_board_handler, refresh_board_handler
)
from handlers.bot_game_handlers import (
    ludotwobot_handler, ludo_two_two_handler, refresh_bot_game_handler
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
            self.logger.info("🎲 Bot Features: Multiplayer Ludo, Visual Board, AI Players, Real-time Gameplay")

        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise

    def _add_handlers(self):
        """Add all command and message handlers"""

        # Basic command handlers
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(CommandHandler("stats", stats_handler))
        self.application.add_handler(CommandHandler("leaderboardgroup", leaderboard_group_handler))
        self.application.add_handler(CommandHandler("leaderboard_global", leaderboard_global_handler))

        # Game creation commands
        self.application.add_handler(CommandHandler("play", play_handler))
        self.application.add_handler(CommandHandler("ludotwo", ludotwo_handler))
        self.application.add_handler(CommandHandler("ludothree", ludothree_handler))
        self.application.add_handler(CommandHandler("ludofour", ludofour_handler))
        self.application.add_handler(CommandHandler("begin", begin_game_handler))

        # Bot game commands
        self.application.add_handler(CommandHandler("ludotwobot", ludotwobot_handler))
        self.application.add_handler(CommandHandler("ludo_two_two", ludo_two_two_handler))

        # Board command
        self.application.add_handler(CommandHandler("board", show_board_handler))

        # Callback handlers for buttons
        self.application.add_handler(CallbackQueryHandler(join_color_handler, pattern="^join_"))
        self.application.add_handler(CallbackQueryHandler(roll_dice_handler, pattern="^roll_"))
        self.application.add_handler(CallbackQueryHandler(move_piece_handler, pattern="^move_"))
        self.application.add_handler(CallbackQueryHandler(refresh_board_handler, pattern="^refresh_board_"))
        self.application.add_handler(CallbackQueryHandler(refresh_bot_game_handler, pattern="^refresh_bot_board_"))
        # leave_game_handler temporarily commented out

        # Message handler for any text (show available commands)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._show_available_commands))

        # Error handler
        self.application.add_error_handler(self._error_handler)

        self.logger.info("All handlers added successfully")

    async def _show_available_commands(self, update: Update, context):
        """Show available commands when user sends any text message"""
        try:
            user = update.effective_user
            commands_message = """
🎲 *Ludo Bot Commands* 🎲

*Basic Commands:*
/start - Start the bot with menu
/help - Show detailed help message
/stats - Your game statistics
/leaderboardgroup - Group leaderboard
/leaderboard_global - Global leaderboard

*Game Creation:*
/play - Single player vs Computer
/ludotwo - 2 Player Game
/ludothree - 3 Player Game
/ludofour - 4 Player Game
/begin GAMECODE - Start a game

*🤖 Bot Game Commands:*
/ludotwobot - 1 Human vs 1 Bot (Auto-start)
/ludo_two_two - 2 Humans vs 2 Bots (Auto-start)

*🎮 Game Controls:*
/board - Show your current game board
Click 🎲 Roll Dice to play your turn
Click color buttons to join games

*How to Play:*
1. Create a game using game commands
2. Players join using color buttons
3. Game auto-starts when ready
4. Roll dice and move pieces to win!
5. First to get all tokens home wins!

*🎯 Features:*
• Real Ludo board with visuals
• Smart AI bot opponents
• Multiplayer with friends
• Player statistics & rankings
• Real-time game updates
            """

            await update.message.reply_text(commands_message, parse_mode='Markdown')

        except Exception as e:
            self.logger.error(f"Error in show_available_commands: {e}")
            await update.message.reply_text(
                "🎲 Welcome to Ludo Bot! 🎮\n\n"
                "Use /start for main menu\n"
                "Use /help for commands list\n"
                "Use /ludotwobot to play vs AI"
            )

    def _error_handler(self, update: Update, context):
        """Log errors caused by updates - IMPROVED"""
        error_msg = str(context.error) if context.error else "Unknown error"
        self.logger.error(f"Exception while handling an update: {error_msg}")

        # Try to send helpful error message to user
        try:
            if update and update.effective_message:
                error_response = "❌ An error occurred. "

                if "connection" in error_msg.lower() or "network" in error_msg.lower():
                    error_response += "Please check your internet connection and try again."
                elif "token" in error_msg.lower():
                    error_response += "Bot configuration error. Please contact admin."
                elif "not found" in error_msg.lower():
                    error_response += "Game not found. Please create a new game."
                else:
                    error_response += "Please try again or use /help for commands."

                update.effective_message.reply_text(error_response)

        except Exception as e:
            self.logger.error(f"Error sending error message: {e}")

    def run(self):
        """Run the bot"""
        if not self.application:
            self.initialize()

        self.logger.info("🚀 Starting Ludo Bot...")
        self.logger.info("🎯 Bot Features: Multiplayer Ludo, Visual Board, AI Players, Real-time Gameplay")
        self.logger.info("📱 Ready to accept commands...")

        # Start the Bot
        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=30
            )
        except KeyboardInterrupt:
            self.logger.info("🛑 Bot stopped by user (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"❌ Error running bot: {e}")
            # Try to restart on error
            import time
            time.sleep(5)
            self.logger.info("🔄 Attempting to restart bot...")
            self.run()

def main():
    """Main function to start the bot"""
    try:
        logger.info("🎲 Ludo Bot Starting...")
        logger.info("💾 Database: SQLite")
        logger.info("🤖 AI: Smart Bot Players")
        logger.info("🎮 Games: Multiplayer & Single Player")

        bot = LudoBot()
        bot.run()

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        logger.info("🔄 Restarting in 10 seconds...")
        import time
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
