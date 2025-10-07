from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from services.game_service import GameService
from services.user_service import UserService
from utils.logger import logger

# Store active games temporarily (in production use Redis)
active_games = {}

async def play_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /play command - single player vs computer"""
    try:
        user = update.effective_user
        logger.info(f"Play command received from user: {user.id}")
        
        message = "🎮 *Single Player vs Computer*\n\n"
        message += "This feature is coming soon! 🚀\n\n"
        message += "For now, you can play with friends using:\n"
        message += "/ludotwo - 2 Player Game\n"
        message += "/ludothree - 3 Player Game\n"
        message += "/ludofour - 4 Player Game"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in play_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")

async def ludotwo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludotwo command - create 2 player game"""
    await create_game_lobby(update, context, 'ludotwo', 2)

async def ludothree_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludothree command - create 3 player game"""
    await create_game_lobby(update, context, 'ludothree', 3)

async def ludofour_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludofour command - create 4 player game"""
    await create_game_lobby(update, context, 'ludofour', 4)




async def create_game_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str, max_players: int):
    """Create a game lobby"""
    try:
        user = update.effective_user
        
        # Create user if not exists
        user_service = UserService()
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        user_id = db_user.id  # ✅ User ID store karen
        user_service.close()  # ✅ Pehle service close karen
        
        # Create game
        game_service = GameService()
        game = game_service.create_game(game_type, user_id, max_players)
        
        # ✅ Ab game info get karen
        game_info = game_service.get_game_info(game.game_code)
        
        # Create join board message
        message = format_join_board_message(game_info, game_type)
        keyboard = create_join_keyboard(game.game_code)
        
        sent_message = await update.message.reply_text(
            message, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Store game message info for updates
        active_games[game.game_code] = {
            'message_id': sent_message.message_id,
            'chat_id': update.effective_chat.id,
            'players': game_info['players']
        }
        
        game_service.close()
        logger.info(f"Game lobby created: {game.game_code}")
        
    except Exception as e:
        logger.error(f"Error creating game lobby: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred while creating game.")




async def join_color_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle join color button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        # Parse callback data: "join_red_ABC123"
        parts = data.split('_')
        if len(parts) != 3:
            await query.edit_message_text("❌ Invalid join request.")
            return
        
        color = parts[1]
        game_code = parts[2]
        
        # Join game
        game_service = GameService()
        user_service = UserService()
        
        # Create user if not exists
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        game, message = game_service.join_game(game_code, db_user.id, color)
        
        if game:
            # Update join board
            game_info = game_service.get_game_info(game_code)
            updated_message = format_join_board_message(game_info, game.game_type)
            keyboard = create_join_keyboard(game_code)
            
            await query.edit_message_text(
                updated_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            # Update active games storage
            active_games[game_code] = {
                'message_id': query.message.message_id,
                'chat_id': query.message.chat_id,
                'players': game_info['players']
            }
            
            # Notify user
            await query.answer(f"✅ Joined as {color.title()}!", show_alert=False)
        else:
            await query.answer(f"❌ {message}", show_alert=True)
        
        user_service.close()
        game_service.close()
        
    except Exception as e:
        logger.error(f"Error in join_color_handler: {e}")
        await query.answer("❌ Error joining game.", show_alert=True)

async def begin_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /begin command - start the game"""
    try:
        user = update.effective_user

        # Check if game code is provided or get from active games
        game_code = None
        if context.args:
            game_code = context.args[0].upper()
        else:
            # Find user's active game
            game_service = GameService()
            user_games = game_service.db.query(GamePlayer, Game).join(
                Game, GamePlayer.game_id == Game.id
            ).filter(
                GamePlayer.user_id == user.id,
                Game.status == 'waiting'
            ).first()

            if user_games:
                game_code = user_games.Game.game_code
            game_service.close()

        if not game_code:
            await update.message.reply_text(
                "❌ Please provide game code: `/begin GAMECODE`\n\n"
                "Or create a new game first using:\n"
                "/ludotwo - 2 Player Game\n"
                "/ludothree - 3 Player Game\n"
                "/ludofour - 4 Player Game",
                parse_mode='Markdown'
            )
            return

        game_service = GameService()
        success, message = game_service.start_game(game_code, user.id)

        if success:
            await update.message.reply_text(f"🎮 *Game {game_code} started!* 🎲\n\nGame is now in progress!", parse_mode='Markdown')

            # Update join board to show game started
            if game_code in active_games:
                game_info = active_games[game_code]
                try:
                    await context.bot.edit_message_text(
                        chat_id=game_info['chat_id'],
                        message_id=game_info['message_id'],
                        text=f"🎮 *Game {game_code} Started!* 🎲\n\nGame is now in progress...",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Could not update game message: {e}")
        else:
            await update.message.reply_text(f"❌ {message}")

        game_service.close()

    except Exception as e:
        logger.error(f"Error in begin_game_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")

def format_join_board_message(game_info: dict, game_type: str) -> str:
    """Format join board message"""
    players_display = []
    for player in game_info['players']:
        players_display.append(f"• {player['color'].title()} - {player['username']}")
    
    # Add empty slots
    for i in range(len(game_info['players']), game_info['max_players']):
        players_display.append(f"• {get_color_name(i)} - [Waiting...]")
    
    players_text = "\n".join(players_display)
    
    # ✅ Markdown symbols escape karein
    message = f"""
🎲 *Ludo Game Lobby* 🎲

*Game Code:* `{game_info['game_code']}`
*Type:* {game_type.title()}
*Players:* {game_info['current_players']}/{game_info['max_players']}

*Players Joined:*
{players_text}

*How to Join:*
1. Click on available color buttons below
2. Or use commands:
   /join\\_red {game_info['game_code']}
   /join\\_blue {game_info['game_code']}
   /join\\_green {game_info['game_code']}
   /join\\_yellow {game_info['game_code']}

*Start Game:*
/begin {game_info['game_code']}
"""
    return message


def create_join_keyboard(game_code: str):
    """Create inline keyboard for joining game"""
    keyboard = [
        [
            InlineKeyboardButton("🔴 Join Red", callback_data=f"join_red_{game_code}"),
            InlineKeyboardButton("🔵 Join Blue", callback_data=f"join_blue_{game_code}")
        ],
        [
            InlineKeyboardButton("🟢 Join Green", callback_data=f"join_green_{game_code}"),
            InlineKeyboardButton("🟡 Join Yellow", callback_data=f"join_yellow_{game_code}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_color_name(index: int) -> str:
    """Get color name by index"""
    colors = ['Red', 'Blue', 'Green', 'Yellow']
    return colors[index] if index < len(colors) else 'Unknown'
