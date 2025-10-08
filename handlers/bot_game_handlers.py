from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.game_service import GameService
from services.user_service import UserService
from services.bot_service import bot_service
from utils.logger import logger

async def ludotwobot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludotwobot - 1 Human vs 1 Bot (Auto-start) - FIXED"""
    try:
        user = update.effective_user
        logger.info(f"🎮 LudoTwoBot command from user: {user.id}")

        # Create user if not exists - PROPERLY HANDLED
        user_service = UserService()
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        user_id = db_user.id  # ✅ Store user ID properly
        user_service.close()  # ✅ Close service immediately

        # Create 2-player game
        game_service = GameService()
        game = game_service.create_game("ludotwobot", user_id, 2)

        # Auto-add bot and start game
        success, message = game_service.auto_start_game(game.game_code, user_id)

        if success:
            # Get updated game info
            game_info = game_service.get_game_info(game.game_code)
            
            # Send success message with board
            board_text = game_service.get_visual_board(game.game_code)

            # Create keyboard based on current turn
            current_player_id = game_info['players'][game_info['current_turn']]['user_id']
            
            if current_player_id == user_id:
                # Human's turn
                keyboard = [
                    [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game.game_code}")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")],
                    [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game.game_code}")]
                ]
            else:
                # Bot's turn - show processing
                keyboard = [
                    [InlineKeyboardButton("🤖 Bot Thinking...", callback_data="waiting")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")]
                ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_message = await update.message.reply_text(
                f"🤖 *1 vs 1 Bot Game Started!* 🎮\n\n"
                f"*Game Code:* `{game.game_code}`\n"
                f"*Players:* You vs Smart Bot\n\n"
                f"{board_text}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # If it's bot's turn, process automatically
            if current_player_id != user_id:
                # Small delay for natural feel
                import asyncio
                await asyncio.sleep(2)
                
                # Process bot turn
                bot_success = bot_service.play_turn(game.game_code)
                
                if bot_success:
                    # Update the message after bot turn
                    updated_board = game_service.get_visual_board(game.game_code)
                    updated_info = game_service.get_game_info(game.game_code)
                    
                    # Check whose turn now
                    new_current_player = updated_info['players'][updated_info['current_turn']]['user_id']
                    
                    if new_current_player == user_id:
                        # Human's turn now
                        keyboard = [
                            [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game.game_code}")],
                            [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")],
                            [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game.game_code}")]
                        ]
                    else:
                        # Still bot's turn (if got 6)
                        keyboard = [
                            [InlineKeyboardButton("🤖 Bot Still Thinking...", callback_data="waiting")],
                            [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")]
                        ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await context.bot.edit_message_text(
                            chat_id=sent_message.chat_id,
                            message_id=sent_message.message_id,
                            text=f"🤖 *1 vs 1 Bot Game* 🎮\n\n"
                                 f"*Game Code:* `{game.game_code}`\n"
                                 f"*Players:* You vs Smart Bot\n\n"
                                 f"{updated_board}",
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception as edit_error:
                        logger.warning(f"Could not update message: {edit_error}")

        else:
            await update.message.reply_text(f"❌ {message}")

        game_service.close()

    except Exception as e:
        logger.error(f"❌ Error in ludotwobot_handler: {e}")
        await update.message.reply_text("❌ Error starting bot game. Please try again.")

async def ludo_two_two_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ludo_two_two - 2 Humans vs 2 Bots (Auto-start) - FIXED"""
    try:
        user = update.effective_user
        logger.info(f"🎮 LudoTwoTwo command from user: {user.id}")

        # Create user if not exists - PROPERLY HANDLED
        user_service = UserService()
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        user_id = db_user.id  # ✅ Store user ID properly
        user_service.close()  # ✅ Close service immediately

        # Create 4-player game
        game_service = GameService()
        game = game_service.create_game("ludo_two_two", user_id, 4)

        # Auto-add bots and start game
        success, message = game_service.auto_start_game(game.game_code, user_id)

        if success:
            # Get updated game info
            game_info = game_service.get_game_info(game.game_code)
            
            # Send success message with board
            board_text = game_service.get_visual_board(game.game_code)

            # Create keyboard based on current turn
            current_player_id = game_info['players'][game_info['current_turn']]['user_id']
            
            if current_player_id == user_id:
                # Human's turn
                keyboard = [
                    [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game.game_code}")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")],
                    [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game.game_code}")]
                ]
            else:
                # Bot's turn - show processing
                keyboard = [
                    [InlineKeyboardButton("🤖 Bot Thinking...", callback_data="waiting")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")]
                ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            sent_message = await update.message.reply_text(
                f"🤖 *2 vs 2 Team Bot Game Started!* 🎮\n\n"
                f"*Game Code:* `{game.game_code}`\n"
                f"*Teams:* You + Bot vs 2 Bots\n\n"
                f"{board_text}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

            # If it's bot's turn, process automatically
            if current_player_id != user_id:
                # Small delay for natural feel
                import asyncio
                await asyncio.sleep(2)
                
                # Process all consecutive bot turns
                bot_success = bot_service.process_all_bot_turns(game.game_code)
                
                if bot_success:
                    # Update the message after bot turns
                    updated_board = game_service.get_visual_board(game.game_code)
                    updated_info = game_service.get_game_info(game.game_code)
                    
                    # Check whose turn now
                    new_current_player = updated_info['players'][updated_info['current_turn']]['user_id']
                    
                    if new_current_player == user_id:
                        # Human's turn now
                        keyboard = [
                            [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game.game_code}")],
                            [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")],
                            [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game.game_code}")]
                        ]
                    else:
                        # Still bot's turn
                        keyboard = [
                            [InlineKeyboardButton("🤖 Bot Thinking...", callback_data="waiting")],
                            [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game.game_code}")]
                        ]
                    
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    try:
                        await context.bot.edit_message_text(
                            chat_id=sent_message.chat_id,
                            message_id=sent_message.message_id,
                            text=f"🤖 *2 vs 2 Team Bot Game* 🎮\n\n"
                                 f"*Game Code:* `{game.game_code}`\n"
                                 f"*Teams:* You + Bot vs 2 Bots\n\n"
                                 f"{updated_board}",
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                    except Exception as edit_error:
                        logger.warning(f"Could not update message: {edit_error}")

        else:
            await update.message.reply_text(f"❌ {message}")

        game_service.close()

    except Exception as e:
        logger.error(f"❌ Error in ludo_two_two_handler: {e}")
        await update.message.reply_text("❌ Error starting team bot game. Please try again.")

# Existing code ke andar _play_bot_turn function ko update karein:

async def _play_bot_turn(update: Update, context: ContextTypes.DEFAULT_TYPE, game_code: str):
    """Handle bot's turn automatically - IMPROVED"""
    try:
        game_service = GameService()
        game = game_service.get_game_by_code(game_code)

        if not game or game.status != 'active':
            game_service.close()
            return

        # Get current player
        current_player = game.players[game.current_turn]
        
        # Check if current player is bot (negative user_id)
        if current_player.user_id < 0:
            # Send "Bot is thinking..." message
            thinking_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🤖 *Bot is thinking...* ⏳",
                parse_mode='Markdown'
            )
            
            # Small delay for natural feel
            import asyncio
            await asyncio.sleep(2)
            
            # Bot plays its turn
            from services.bot_service import bot_service
            result = bot_service.play_turn(game_code)
            
            if result:
                # Delete thinking message
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=thinking_msg.message_id
                    )
                except:
                    pass
                
                # Get updated board
                board_text = game_service.get_visual_board(game_code)
                
                # Send bot move result
                bot_name = bot_service.get_bot_name(current_player.user_id)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🤖 *{bot_name} played its turn!*\n\n{board_text}",
                    parse_mode='Markdown'
                )
                
                # Check if next turn is also bot
                game = game_service.get_game_by_code(game_code)  # Refresh game data
                next_player = game.players[game.current_turn]
                if next_player.user_id < 0:
                    # Continue bot turns
                    await _play_bot_turn(update, context, game_code)

        game_service.close()

    except Exception as e:
        logger.error(f"Error in _play_bot_turn: {e}")

async def refresh_bot_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle refresh button for bot games"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("refresh_board_"):
            game_code = data.replace("refresh_board_", "")
            
            game_service = GameService()
            board_text = game_service.get_visual_board(game_code)
            game_info = game_service.get_game_info(game_code)
            
            # Get current user
            user = query.from_user
            
            # Find user in game players
            current_player_id = None
            for player in game_info['players']:
                user_service = UserService()
                db_user = user_service.get_user(user.id)
                if db_user and player['user_id'] == db_user.id:
                    current_player_id = db_user.id
                    user_service.close()
                    break
                user_service.close()
            
            # Create appropriate keyboard
            if current_player_id and game_info['current_turn'] == current_player_id:
                keyboard = [
                    [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_code}")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game_code}")],
                    [InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_{game_code}")]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton("🤖 Bot's Turn...", callback_data="waiting")],
                    [InlineKeyboardButton("📊 Refresh Board", callback_data=f"refresh_board_{game_code}")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=board_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            game_service.close()
            
    except Exception as e:
        logger.error(f"❌ Error in refresh_bot_game_handler: {e}")
        await query.answer("❌ Error refreshing board.", show_alert=True)
