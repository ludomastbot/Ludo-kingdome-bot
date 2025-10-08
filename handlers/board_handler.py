from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from database.models import get_db
from services.board_service import BoardService
from utils.logger import logger

async def board_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /board command to show game board"""
    try:
        user = update.effective_user
        
        # Get game code from context or arguments
        game_code = None
        if context.args:
            game_code = context.args[0].upper()
        else:
            # Find user's active game
            db = next(get_db())
            from database.models import Game, GamePlayer
            user_game = db.query(GamePlayer).join(Game).filter(
                GamePlayer.user_id == user.id,
                Game.status.in_(['waiting', 'active'])
            ).first()
            
            if user_game:
                game_code = user_game.game.game_code
            db.close()
        
        if not game_code:
            await update.message.reply_text(
                "❌ No active game found!\n\n"
                "Please provide game code: `/board GAMECODE`\n"
                "Or join a game first using:\n"
                "/ludotwo - 2 Player Game\n"
                "/ludothree - 3 Player Game\n"
                "/ludofour - 4 Player Game",
                parse_mode='Markdown'
            )
            return
        
        # Generate and send board
        await send_game_board(update, context, game_code, user.id)
        
    except Exception as e:
        logger.error(f"Error in board_handler: {e}")
        await update.message.reply_text("❌ Error showing board. Please try again.")

async def send_game_board(update: Update, context: ContextTypes.DEFAULT_TYPE, game_code: str, user_id: int):
    """Send game board to user"""
    try:
        db = next(get_db())
        board_service = BoardService()
        
        # Create visual board
        board_text = board_service.create_visual_board(game_code)
        
        # Create refresh button
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")],
            [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_code}")],
            [InlineKeyboardButton("📊 Game Info", callback_data=f"info_{game_code}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send board
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                board_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                board_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        board_service.close()
        db.close()
        
    except Exception as e:
        logger.error(f"Error sending game board: {e}")
        error_msg = "❌ Could not display board. Please try again."
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def refresh_board_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle board refresh button"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        game_code = data.replace('refresh_board_', '')
        
        await send_game_board(update, context, game_code, query.from_user.id)
        
    except Exception as e:
        logger.error(f"Error in refresh_board_handler: {e}")
        await query.answer("❌ Error refreshing board", show_alert=True)

# Register handlers
def setup_board_handlers(application):
    """Setup board-related handlers"""
    application.add_handler(CommandHandler("board", board_handler))
    application.add_handler(CallbackQueryHandler(refresh_board_handler, pattern="^refresh_board_"))
