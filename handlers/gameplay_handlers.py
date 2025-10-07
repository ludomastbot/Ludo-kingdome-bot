from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from services.board_service import BoardService
from services.game_service import GameService
from services.user_service import UserService
from utils.logger import logger

async def begin_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /begin command - start the game"""
    try:
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text("❌ Please provide game code: /begin ABC123")
            return
        
        game_code = context.args[0].upper()
        
        game_service = GameService()
        success, message = game_service.start_game(game_code, user.id)
        
        if success:
            # Get game info for display
            game_info = game_service.get_game_info(game_code)
            
            # Create game board display
            board_message = format_game_board(game_info)
            keyboard = create_game_keyboard(game_code)
            
            await update.message.reply_text(
                board_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            # Notify players
            players = game_info['players']
            current_player = next((p for p in players if p['player_order'] == 1), None)
            
            if current_player:
                await update.message.reply_text(
                    f"🎮 *Game {game_code} Started!* 🎲\n\n"
                    f"🔴 *{current_player['username']}'s turn* ({current_player['color'].title()})\n"
                    f"Click the 🎲 button to roll dice!",
                    parse_mode='Markdown'
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
        
        board_service = BoardService()
        user_service = UserService()
        
        # Get user from database
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Roll dice
        dice_value, possible_moves = board_service.roll_dice(game_code, db_user.id)
        
        if dice_value is None:
            await query.answer(possible_moves, show_alert=True)
            user_service.close()
            board_service.close()
            return
        
        # Get updated game status
        game_status = board_service.get_game_status(game_code)
        game_service = GameService()
        game_info = game_service.get_game_info(game_code)
        
        # Create response message
        current_player = next(
            (p for p in game_status['players'] if p['user_id'] == db_user.id), 
            None
        )
        
        roll_message = f"🎲 *{user.first_name} rolled a {dice_value}!*\n"
        
        if possible_moves:
            roll_message += f"📋 *Available Moves:*\n"
            for i, move in enumerate(possible_moves, 1):
                piece_status = "🏠" if move['current_position'] == 0 else f"#{move['current_position']}"
                roll_message += f"{i}. Piece {piece_status} → "
                if move['new_position'] == 57:
                    roll_message += "🏁 FINISH"
                else:
                    roll_message += f"#{move['new_position']}"
                
                if move['is_capture']:
                    roll_message += " 🎯 (Capture!)"
                roll_message += "\n"
            
            # Create move buttons
            keyboard = create_move_keyboard(game_code, possible_moves)
        else:
            roll_message += "❌ *No valid moves available.*\nTurn passes to next player."
            keyboard = create_game_keyboard(game_code)
        
        # Update game board display
        board_message = format_game_board(game_info)
        
        try:
            await query.edit_message_text(
                board_message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            pass  # Skip if can't edit original message
        
        # Send roll result
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=roll_message,
            parse_mode='Markdown',
            reply_markup=keyboard if possible_moves else None
        )
        
        user_service.close()
        board_service.close()
        game_service.close()
        
    except Exception as e:
        logger.error(f"Error in roll_dice_handler: {e}")
        await query.answer("❌ Error rolling dice.", show_alert=True)

async def move_piece_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle piece move button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        # Parse callback data: "move_ABC123_0" (game_code, piece_index)
        parts = data.split('_')
        if len(parts) != 3:
            await query.answer("❌ Invalid move request.", show_alert=True)
            return
        
        game_code = parts[1]
        piece_index = int(parts[2])
        
        board_service = BoardService()
        user_service = UserService()
        
        # Get user from database
        db_user = user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Execute move
        success, message = board_service.move_piece(game_code, db_user.id, piece_index)
        
        if success:
            # Get updated game status
            game_status = board_service.get_game_status(game_code)
            game_service = GameService()
            game_info = game_service.get_game_info(game_code)
            
            # Check if game ended
            if "won" in message.lower():
                await query.edit_message_text(
                    f"🎉 *GAME OVER!* 🎉\n\n"
                    f"🏆 *Winner: {user.first_name}!* 🏆\n"
                    f"{message}\n\n"
                    f"Game Code: {game_code}\n"
                    f"Thanks for playing! 🎲",
                    parse_mode='Markdown'
                )
                
                # Update user statistics
                user_service.update_user_stats(db_user.id, game_won=True, pieces_captured=0, moves_made=10)
                
                user_service.close()
                board_service.close()
                game_service.close()
                return
            
            # Update board display
            board_message = format_game_board(game_info)
            keyboard = create_game_keyboard(game_code)
            
            try:
                await query.edit_message_text(
                    board_message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                pass
            
            # Send move result
            move_result_message = f"✅ *Move Executed!*\n{message}\n"
            
            # Notify next player
            if "successfully" in message.lower():
                next_player = next((p for p in game_status['players'] if p['player_order'] == game_status['current_turn']), None)
                if next_player:
                    user_service_next = UserService()
                    next_user = user_service_next.get_or_create_user(telegram_id=next_player['user_id'])
                    next_username = next_user.first_name
                    user_service_next.close()
                    
                    color_emojis = {'red': '🔴', 'blue': '🔵', 'green': '🟢', 'yellow': '🟡'}
                    color_emoji = color_emojis.get(next_player['color'], '🎯')
                    
                    turn_message = (
                        f"{color_emoji} *{next_username}'s Turn!* {color_emoji}\n"
                        f"Color: {next_player['color'].title()}\n"
                        f"Click 🎲 to roll dice!"
                    )
                    
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=turn_message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=move_result_message,
                parse_mode='Markdown'
            )
            
        else:
            await query.answer(message, show_alert=True)
        
        user_service.close()
        board_service.close()
        
    except Exception as e:
        logger.error(f"Error in move_piece_handler: {e}")
        await query.answer("❌ Error moving piece.", show_alert=True)

def format_game_board(game_info):
    """Format game board display"""
    players = game_info['players']
    
    board_message = f"🎲 *Ludo Game - {game_info['game_code']}* 🎲\n\n"
    board_message += f"*Status:* {game_info['status'].title()}\n"
    board_message += f"*Players:* {game_info['current_players']}/{game_info['max_players']}\n\n"
    
    board_message += "*Players:*\n"
    for player in players:
        color_emojis = {'red': '🔴', 'blue': '🔵', 'green': '🟢', 'yellow': '🟡'}
        color_emoji = color_emojis.get(player['color'], '🎯')
        
        # Show piece positions
        pieces_display = []
        for pos in player['pieces_position']:
            if pos == 0:
                pieces_display.append("🏠")  # Home
            elif pos == 57:
                pieces_display.append("🏁")  # Finished
            else:
                pieces_display.append(f"#{pos}")
        
        board_message += (
            f"{color_emoji} *{player['username']}* ({player['color'].title()})\n"
            f"   Pieces: {' '.join(pieces_display)}\n\n"
        )
    
    board_message += "*How to Play:*\n"
    board_message += "1. Click 🎲 to roll dice\n"
    board_message += "2. Select piece to move\n"
    board_message += "3. First to finish all pieces wins! 🏆"
    
    return board_message

def create_game_keyboard(game_code):
    """Create game control keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_code}")],
        [
            InlineKeyboardButton("📊 Game Status", callback_data=f"status_{game_code}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{game_code}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_move_keyboard(game_code, possible_moves):
    """Create move selection keyboard"""
    keyboard = []
    
    for i, move in enumerate(possible_moves, 1):
        piece_status = "🏠" if move['current_position'] == 0 else f"#{move['current_position']}"
        button_text = f"Move {piece_status}"
        
        if move['is_capture']:
            button_text += " 🎯"
        
        keyboard.append([
            InlineKeyboardButton(
                button_text, 
                callback_data=f"move_{game_code}_{move['piece_index']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_{game_code}")
    ])
    
    return InlineKeyboardMarkup(keyboard)
