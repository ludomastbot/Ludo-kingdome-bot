from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.game_service import GameService
from services.user_service import UserService
from services.bot_service import bot_service
from utils.logger import logger

async def show_board_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /board command to show game board"""
    try:
        user = update.effective_user
        
        # Find user's active game
        game_service = GameService()
        user_game = game_service.get_user_active_game(user.id)
        
        if not user_game:
            await update.message.reply_text(
                "❌ You are not in any active game!\n\n"
                "Join a game using:\n"
                "/ludotwo - 2 Player Game\n"
                "/ludothree - 3 Player Game\n" 
                "/ludofour - 4 Player Game\n"
                "/ludotwobot - 1 vs 1 Bot Game\n"
                "/ludo_two_two - 2 vs 2 Bot Game"
            )
            return
        
        # Get visual board
        board_text = game_service.get_visual_board(user_game.game_code)
        
        # Get game info for keyboard
        game_info = game_service.get_game_info(user_game.game_code)
        
        # Create action buttons based on turn
        keyboard = []
        current_player_id = game_info['players'][game_info['current_turn']]['user_id']
        
        # Check if current user is the active player
        user_service = UserService()
        db_user = user_service.get_user(user.id)
        
        if db_user and current_player_id == db_user.id:
            # User's turn
            keyboard = [
                [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{user_game.game_code}")],
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{user_game.game_code}")],
                [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{user_game.game_code}")]
            ]
        elif current_player_id < 0:  # Bot's turn
            keyboard = [
                [InlineKeyboardButton("🤖 Bot's Turn...", callback_data="waiting")],
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{user_game.game_code}")]
            ]
        else:
            # Other player's turn
            keyboard = [
                [InlineKeyboardButton("⏳ Waiting for turn...", callback_data="waiting")],
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{user_game.game_code}")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            board_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        user_service.close()
        game_service.close()
        
    except Exception as e:
        logger.error(f"Error in show_board_handler: {e}")
        await update.message.reply_text("❌ Error displaying board.")

async def refresh_board_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle board refresh button"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        game_code = data.replace("refresh_board_", "")
        
        game_service = GameService()
        board_text = game_service.get_visual_board(game_code)
        game_info = game_service.get_game_info(game_code)
        
        # Create appropriate keyboard
        keyboard = []
        
        if game_info and game_info['status'] == 'active':
            current_player_id = game_info['players'][game_info['current_turn']]['user_id']
            
            # Check if current user is the active player
            user = query.from_user
            user_service = UserService()
            db_user = user_service.get_user(user.id)
            
            if db_user and current_player_id == db_user.id:
                # It's user's turn
                keyboard = [
                    [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_code}")],
                    [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")],
                    [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game_code}")]
                ]
            else:
                # Not user's turn - check if it's bot's turn
                if current_player_id < 0:  # Bot's turn
                    keyboard = [
                        [InlineKeyboardButton("🤖 Bot's Turn...", callback_data="waiting")],
                        [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")]
                    ]
                else:
                    # Other human player's turn
                    keyboard = [
                        [InlineKeyboardButton("⏳ Waiting for turn...", callback_data="waiting")],
                        [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")]
                    ]
            
            user_service.close()
        else:
            # Game not active or waiting
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")],
                [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game_code}")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=board_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        game_service.close()
        
    except Exception as e:
        logger.error(f"Error in refresh_board_handler: {e}")
        await query.answer("❌ Error refreshing board.", show_alert=True)

async def begin_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /begin command - start the game"""
    try:
        user = update.effective_user

        # Check if game code is provided
        game_code = None
        if context.args:
            game_code = context.args[0].upper()
        else:
            # Find user's active game
            game_service = GameService()
            user_game = game_service.get_user_active_game(user.id)
            
            if user_game:
                game_code = user_game.game_code
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

            # Show the game board
            board_text = game_service.get_visual_board(game_code)
            game_info = game_service.get_game_info(game_code)
            
            # Create keyboard
            keyboard = [
                [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_code}")],
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                board_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(f"❌ {message}")

        game_service.close()

    except Exception as e:
        logger.error(f"Error in begin_game_handler: {e}")
        await update.message.reply_text("❌ Sorry, an error occurred.")

async def roll_dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dice roll button clicks"""
    try:
        query = update.callback_query
        await query.answer()

        data = query.data
        user = query.from_user

        # Parse callback data: "roll_ABC123"
        game_code = data.replace('roll_', '')

        game_service = GameService()
        user_service = UserService()

        # Get user from database
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        # Simple dice roll logic
        import random
        dice_value = random.randint(1, 6)
        
        # Update game with dice value
        game = game_service.get_game_by_code(game_code)
        if game:
            game.dice_value = dice_value
            game_service.db.commit()
            
            # Create response message
            dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
            dice_emoji = dice_emojis.get(dice_value, "🎲")
            
            roll_message = f"🎲 *{user.first_name} rolled a {dice_value}!* {dice_emoji}\n"
            
            if dice_value == 6:
                roll_message += "🎉 *Lucky 6!* You get an extra turn!\n"
            
            # For now, just show the roll result
            # In next part, we'll implement actual move logic
            
            # Update board
            board_text = game_service.get_visual_board(game_code)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_board_{game_code}")],
                [InlineKeyboardButton("🎲 Roll Again", callback_data=f"roll_{game_code}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message
            await query.edit_message_text(
                text=board_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Send roll result
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=roll_message,
                parse_mode='Markdown'
            )
            
            # Process bot turns if any
            game_info = game_service.get_game_info(game_code)
            next_player_id = game_info['players'][game_info['current_turn']]['user_id']
            
            if next_player_id < 0:  # Bot's turn
                bot_success = bot_service.process_all_bot_turns(game_code)
                if bot_success:
                    logger.info("🤖 Bot turns processed after human roll")

        user_service.close()
        game_service.close()

    except Exception as e:
        logger.error(f"Error in roll_dice_handler: {e}")
        await query.answer("❌ Error rolling dice.", show_alert=True)

async def move_piece_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle piece move button clicks - SIMPLIFIED FOR NOW"""
    try:
        query = update.callback_query
        await query.answer("🎯 Move feature coming in next update!", show_alert=True)
        
        # This will be implemented in Part 3 (Game Logic)
        # For now, just acknowledge the click
        
    except Exception as e:
        logger.error(f"Error in move_piece_handler: {e}")
        await query.answer("❌ Move feature coming soon!", show_alert=True)

async def leave_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leave game button"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        game_code = data.replace("leave_", "")
        
        game_service = GameService()
        user_service = UserService()
        
        user = query.from_user
        db_user = user_service.get_user(user.id)
        
        if db_user:
            # Remove player from game
            success = game_service.leave_game(game_code, db_user.id)
            
            if success:
                await query.edit_message_text(
                    f"🏃 *You left the game {game_code}*\n\n"
                    f"Use /ludotwo or /ludotwobot to start a new game!",
                    parse_mode='Markdown'
                )
            else:
                await query.answer("❌ Error leaving game.", show_alert=True)
        
        user_service.close()
        game_service.close()
        
    except Exception as e:
        logger.error(f"Error in leave_game_handler: {e}")
        await query.answer("❌ Error leaving game.", show_alert=True)
