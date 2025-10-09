import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8403232282:AAGXrSzIciS5aEQSUJMs-iZ82LuTtEGBa8o')

class LudoGame:
    def __init__(self, chat_id, players, is_bot_game=False):
        self.chat_id = chat_id
        self.players = players
        self.is_bot_game = is_bot_game
        self.current_turn = 0
        self.dice_value = 0
        self.winner = None
        self.last_roll_was_six = False
        
        # Initialize positions: -1 means in home, 0-51 on board, 52+ finished
        self.positions = {}
        for player in players:
            self.positions[player] = [-1, -1, -1, -1]
        
        # Player colors
        self.colors = {
            players[0]: '🔴',
            players[1]: '🟢' if len(players) > 1 else '',
            players[2]: '🟡' if len(players) > 2 else '',
            players[3]: '🔵' if len(players) > 3 else ''
        }
        
        # Starting positions for each player
        self.start_pos = {
            players[0]: 0,
            players[1]: 13 if len(players) > 1 else 0,
            players[2]: 26 if len(players) > 2 else 0,
            players[3]: 39 if len(players) > 3 else 0
        }
        
        # Safe spots where pieces can't be captured
        self.safe_spots = [0, 8, 13, 21, 26, 34, 39, 47]
    
    def roll_dice(self):
        self.dice_value = random.randint(1, 6)
        self.last_roll_was_six = (self.dice_value == 6)
        return self.dice_value
    
    def get_current_player(self):
        return self.players[self.current_turn]
    
    def can_move_out(self):
        return self.dice_value == 6
    
    def get_movable_pieces(self, player):
        movable = []
        positions = self.positions[player]
        
        for i, pos in enumerate(positions):
            # Piece in home - can only move out with 6
            if pos == -1:
                if self.dice_value == 6:
                    movable.append(i)
            # Piece on board - check if can move
            elif pos >= 0 and pos < 51:
                new_pos = pos + self.dice_value
                # Can't move past finish
                if new_pos <= 56:  # Home stretch is 51-56
                    movable.append(i)
            # Piece in home stretch (51-56)
            elif 51 <= pos < 56:
                if pos + self.dice_value <= 56:
                    movable.append(i)
        
        return movable
    
    def move_piece(self, player, piece_idx):
        current_pos = self.positions[player][piece_idx]
        
        # Moving out from home
        if current_pos == -1:
            start = self.start_pos[player]
            self.positions[player][piece_idx] = start
            self.check_capture(player, start)
            return True
        
        # Calculate new position
        new_pos = current_pos + self.dice_value
        
        # Can't move past finish
        if new_pos > 56:
            return False
        
        self.positions[player][piece_idx] = new_pos
        
        # Check for capture (only if not in home stretch and not finished)
        if new_pos < 51:
            self.check_capture(player, new_pos)
        
        # Check win condition
        self.check_win(player)
        
        return True
    
    def check_capture(self, moving_player, position):
        # Can't capture on safe spots
        if position in self.safe_spots:
            return
        
        # Check all other players
        for player in self.players:
            if player != moving_player:
                for i, pos in enumerate(self.positions[player]):
                    if pos == position:
                        # Send piece back home
                        self.positions[player][i] = -1
    
    def check_win(self, player):
        # Win if all pieces are at position 56 (finished)
        if all(pos == 56 for pos in self.positions[player]):
            self.winner = player
    
    def next_turn(self):
        # Keep turn if rolled 6, otherwise move to next player
        if not self.last_roll_was_six:
            self.current_turn = (self.current_turn + 1) % len(self.players)
    
    def get_board_display(self):
        current_player = self.get_current_player()
        text = f"🎲 *LUDO GAME*\n\n"
        text += f"🎯 Turn: {self.colors[current_player]} {current_player}\n"
        text += f"🎲 Dice: {self.dice_value if self.dice_value > 0 else '❓'}\n\n"
        
        for player in self.players:
            text += f"{self.colors[player]} *{player}*\n"
            positions = self.positions[player]
            for i, pos in enumerate(positions):
                if pos == -1:
                    text += f"  🔹 Piece {i+1}: 🏠 Home\n"
                elif pos == 56:
                    text += f"  🔹 Piece {i+1}: 🏁 Finished\n"
                elif pos > 51:
                    text += f"  🔹 Piece {i+1}: 🎯 Home Stretch ({pos-51}/5)\n"
                else:
                    text += f"  🔹 Piece {i+1}: 📍 Position {pos}\n"
            text += "\n"
        
        return text
    
    def bot_make_move(self):
        """Smart bot AI for making moves"""
        movable = self.get_movable_pieces(self.get_current_player())
        
        if not movable:
            return None
        
        # Smart decision making
        best_move = None
        best_score = -1000
        
        for piece_idx in movable:
            score = 0
            current_pos = self.positions[self.get_current_player()][piece_idx]
            
            if current_pos == -1:
                # Moving out of home
                new_pos = self.start_pos[self.get_current_player()]
            else:
                new_pos = current_pos + self.dice_value
            
            # Prioritize capturing opponent pieces
            for player in self.players:
                if player != self.get_current_player():
                    for opp_pos in self.positions[player]:
                        if opp_pos == new_pos and new_pos not in self.safe_spots:
                            score += 200  # High priority for captures
            
            # Prefer moving pieces closer to finish
            if current_pos >= 0:
                score += new_pos * 2
            
            # Prefer moving pieces out of home
            if current_pos == -1:
                score += 100
            
            # Avoid positions where opponents can capture
            risk = 0
            for player in self.players:
                if player != self.get_current_player():
                    for opp_pos in self.positions[player]:
                        if opp_pos >= 0 and abs(opp_pos - new_pos) <= 6:
                            risk += 20
            score -= risk
            
            if score > best_score:
                best_score = score
                best_move = piece_idx
        
        return best_move

# Global storage for active games
games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    keyboard = [
        [InlineKeyboardButton("🤖 Play vs Bot", callback_data='mode_bot')],
        [InlineKeyboardButton("👥 2 Players", callback_data='mode_2p')],
        [InlineKeyboardButton("👥 4 Players", callback_data='mode_4p')],
        [InlineKeyboardButton("📖 Rules", callback_data='rules')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎲 *Welcome to Advanced LUDO!*\n\n"
        "Choose your game mode to start playing!\n\n"
        "Features:\n"
        "✅ Smart AI Bot\n"
        "✅ Multiplayer Support\n"
        "✅ Piece Capturing\n"
        "✅ Safe Spots\n"
        "✅ Extra Turn on 6",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    
    # Rules
    if data == 'rules':
        rules = (
            "📖 *LUDO RULES*\n\n"
            "🎯 *Objective:* Move all 4 pieces to finish line\n\n"
            "🎲 *How to Play:*\n"
            "• Roll 🎲 6 to move piece out of home\n"
            "• Move pieces according to dice value\n"
            "• Capture opponents by landing on them\n"
            "• Safe spots 🛡️ protect from capture\n"
            "• Roll 6 to get extra turn\n"
            "• First to finish all pieces wins!\n\n"
            "Good luck! 🍀"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back_to_menu')]]
        await query.edit_message_text(rules, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    # Back to menu
    if data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("🤖 Play vs Bot", callback_data='mode_bot')],
            [InlineKeyboardButton("👥 2 Players", callback_data='mode_2p')],
            [InlineKeyboardButton("👥 4 Players", callback_data='mode_4p')],
            [InlineKeyboardButton("📖 Rules", callback_data='rules')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎲 *Welcome to Advanced LUDO!*\n\nChoose your game mode:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Start new game
    if data.startswith('mode_'):
        user = query.from_user.first_name
        
        if data == 'mode_bot':
            games[chat_id] = LudoGame(chat_id, [user, "🤖 Bot"], is_bot_game=True)
        elif data == 'mode_2p':
            games[chat_id] = LudoGame(chat_id, [user, "Player 2"])
        elif data == 'mode_4p':
            games[chat_id] = LudoGame(chat_id, [user, "Player 2", "Player 3", "Player 4"])
        
        await show_game_board(query, chat_id)
        return
    
    # Game actions
    if chat_id not in games:
        await query.edit_message_text("❌ No active game! Use /start to begin.")
        return
    
    game = games[chat_id]
    
    # Roll dice
    if data == 'roll':
        await handle_roll(query, chat_id)
    
    # Move piece
    elif data.startswith('move_'):
        piece_idx = int(data.split('_')[1])
        await handle_move(query, chat_id, piece_idx)
    
    # End turn
    elif data == 'end_turn':
        await handle_end_turn(query, chat_id)

async def show_game_board(query, chat_id):
    """Display the game board"""
    game = games[chat_id]
    keyboard = [[InlineKeyboardButton("🎲 Roll Dice", callback_data='roll')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = game.get_board_display()
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_roll(query, chat_id):
    """Handle dice roll"""
    game = games[chat_id]
    current_player = game.get_current_player()
    
    # Bot's turn
    if game.is_bot_game and current_player == "🤖 Bot":
        await bot_turn(query, chat_id)
        return
    
    # Player rolls
    dice = game.roll_dice()
    movable = game.get_movable_pieces(current_player)
    
    text = game.get_board_display()
    
    # No moves available
    if not movable:
        text += f"\n❌ No valid moves! Turn passes."
        keyboard = [[InlineKeyboardButton("➡️ Next Turn", callback_data='end_turn')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    # Show movable pieces
    keyboard = []
    for piece_idx in movable:
        pos = game.positions[current_player][piece_idx]
        if pos == -1:
            label = f"🏠 Move Piece {piece_idx+1} Out"
        else:
            label = f"📍 Move Piece {piece_idx+1} ({pos}→{pos+dice})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f'move_{piece_idx}')])
    
    text += f"\n✅ Choose a piece to move:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_move(query, chat_id, piece_idx):
    """Handle piece movement"""
    game = games[chat_id]
    current_player = game.get_current_player()
    
    if game.move_piece(current_player, piece_idx):
        # Check for winner
        if game.winner:
            text = f"🎉🎉🎉 *{game.winner} WINS!* 🎉🎉🎉\n\n{game.get_board_display()}"
            keyboard = [[InlineKeyboardButton("🔄 New Game", callback_data='back_to_menu')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            del games[chat_id]
            return
        
        # Extra turn on 6
        if game.last_roll_was_six:
            text = game.get_board_display() + "\n🎉 You rolled 6! Roll again!"
            keyboard = [[InlineKeyboardButton("🎲 Roll Again", callback_data='roll')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await handle_end_turn(query, chat_id)

async def handle_end_turn(query, chat_id):
    """End current turn and move to next player"""
    game = games[chat_id]
    game.next_turn()
    
    # Bot's turn
    if game.is_bot_game and game.get_current_player() == "🤖 Bot":
        await bot_turn(query, chat_id)
    else:
        await show_game_board(query, chat_id)

async def bot_turn(query, chat_id):
    """Handle bot's turn"""
    game = games[chat_id]
    
    # Bot rolls
    await asyncio.sleep(1)
    dice = game.roll_dice()
    
    text = game.get_board_display() + f"\n🤖 Bot rolled {dice}..."
    await query.edit_message_text(text, parse_mode='Markdown')
    await asyncio.sleep(1.5)
    
    # Bot makes move
    piece_idx = game.bot_make_move()
    
    if piece_idx is None:
        text = game.get_board_display() + "\n🤖 Bot has no valid moves!"
        await query.edit_message_text(text, parse_mode='Markdown')
        await asyncio.sleep(1)
        game.next_turn()
        await show_game_board(query, chat_id)
        return
    
    game.move_piece("🤖 Bot", piece_idx)
    
    # Check winner
    if game.winner:
        text = f"🎉 *{game.winner} WINS!*\n\n{game.get_board_display()}"
        keyboard = [[InlineKeyboardButton("🔄 New Game", callback_data='back_to_menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        del games[chat_id]
        return
    
    # Bot got 6, rolls again
    if game.last_roll_was_six:
        text = game.get_board_display() + "\n🤖 Bot rolled 6! Rolling again..."
        await query.edit_message_text(text, parse_mode='Markdown')
        await asyncio.sleep(1)
        await bot_turn(query, chat_id)
    else:
        game.next_turn()
        await show_game_board(query, chat_id)

def main():
    """Start the bot"""
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🎲 Ludo Bot Started Successfully!")
    print(f"✅ Bot Token: {TOKEN[:20]}...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
