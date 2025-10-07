#!/usr/bin/env python3
import os
import logging
import sqlite3
import random
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, request
import threading

# Configure logging
logging.basicConfig(
    format='%(asctime)s - LUDO BOT - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot Token
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8403232282:AAGXrSzIciS5aEQSUJMs-iZ82LuTtEGBa8o')

# Flask app for web server
app = Flask(__name__)

@app.route('/')
def home():
    return "🎲 Ludo Bot is Running!"

@app.route('/ping')
def ping():
    return "pong"

# Database setup
def init_db():
    conn = sqlite3.connect('ludo_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            total_coins INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_sessions (
            session_id TEXT PRIMARY KEY,
            players TEXT,
            game_state TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()



class LudoGame:
    def __init__(self, players):
        self.players = players  # {user_id: {'color': 'red', 'name': 'Player1', 'tokens': [0,0,0,0]}}
        self.colors = ['red', 'blue', 'green', 'yellow']
        self.current_player_index = 0
        self.dice_value = 0
        self.game_state = "waiting"
        self.board = self.initialize_board()
        
    def initialize_board(self):
        # Simple board representation
        return {
            'red': {'tokens': [-1, -1, -1, -1], 'home': 0, 'path': list(range(1, 57))},
            'blue': {'tokens': [-1, -1, -1, -1], 'home': 14, 'path': list(range(15, 57)) + list(range(1, 15))},
            'green': {'tokens': [-1, -1, -1, -1], 'home': 28, 'path': list(range(29, 57)) + list(range(1, 29))},
            'yellow': {'tokens': [-1, -1, -1, -1], 'home': 42, 'path': list(range(43, 57)) + list(range(1, 43))}
        }
    
    def roll_dice(self):
        self.dice_value = random.randint(1, 6)
        return self.dice_value
    
    def can_move_token(self, player_color, token_index):
        if self.dice_value == 6 and self.board[player_color]['tokens'][token_index] == -1:
            return True
        elif self.board[player_color]['tokens'][token_index] >= 0:
            return True
        return False
    
    def move_token(self, player_color, token_index):
        current_pos = self.board[player_color]['tokens'][token_index]
        
        if current_pos == -1 and self.dice_value == 6:
            # Move token out of home
            self.board[player_color]['tokens'][token_index] = self.board[player_color]['home']
        elif current_pos >= 0:
            # Move token on board
            new_pos = (current_pos + self.dice_value) % 56
            self.board[player_color]['tokens'][token_index] = new_pos
            
            # Check if token captures opponent
            self.capture_tokens(player_color, new_pos)
        
        # Check for extra turn
        if self.dice_value == 6:
            return True  # Extra turn
        return False
    
    def capture_tokens(self, player_color, position):
        for color in self.colors:
            if color != player_color:
                for i in range(4):
                    if self.board[color]['tokens'][i] == position:
                        self.board[color]['tokens'][i] = -1  # Send back to home
    
    def next_turn(self):
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        self.dice_value = 0
    
    def get_current_player(self):
        player_ids = list(self.players.keys())
        return player_ids[self.current_player_index]
    
    def check_winner(self):
        for user_id, player_data in self.players.items():
            if all(pos >= 51 for pos in self.board[player_data['color']]['tokens']):
                return user_id
        return None



class GameSessionManager:
    def __init__(self):
        self.active_games = {}
        self.waiting_rooms = {}
    
    def create_waiting_room(self, creator_id, creator_name):
        room_id = f"room_{creator_id}_{datetime.now().timestamp()}"
        self.waiting_rooms[room_id] = {
            'creator': creator_id,
            'players': {creator_id: {'name': creator_name, 'color': 'red', 'ready': False}},
            'created_at': datetime.now(),
            'max_players': 4
        }
        return room_id
    
    def join_waiting_room(self, room_id, user_id, username, color):
        if room_id in self.waiting_rooms:
            room = self.waiting_rooms[room_id]
            if len(room['players']) < room['max_players']:
                room['players'][user_id] = {
                    'name': username, 
                    'color': color, 
                    'ready': False
                }
                return True
        return False
    
    def start_game(self, room_id):
        if room_id in self.waiting_rooms:
            room = self.waiting_rooms[room_id]
            game_id = f"game_{room_id}"
            
            # Create game instance
            game = LudoGame(room['players'])
            self.active_games[game_id] = {
                'game': game,
                'players': room['players'],
                'created_at': datetime.now()
            }
            
            # Remove waiting room
            del self.waiting_rooms[room_id]
            return game_id
        return None
    
    def get_game(self, game_id):
        return self.active_games.get(game_id)
    
    def get_waiting_room(self, room_id):
        return self.waiting_rooms.get(room_id)

game_manager = GameSessionManager()


class AdvancedLudoBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all command handlers"""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ludo", self.ludo_start))
        self.application.add_handler(CommandHandler("play", self.quick_play))
        
        # Game commands
        self.application.add_handler(CommandHandler("roll", self.roll_dice))
        self.application.add_handler(CommandHandler("board", self.show_board))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Message handler for showing available commands
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.show_commands))
    
    def save_user(self, user):
        """Save user to database"""
        conn = sqlite3.connect('ludo_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, total_coins)
            VALUES (?, ?, ?, 1000)
        ''', (user.id, user.username, user.first_name))
        
        cursor.execute('''
            UPDATE users SET username = ?, first_name = ? 
            WHERE user_id = ?
        ''', (user.username, user.first_name, user.id))
        
        conn.commit()
        conn.close()

    async def start_command(self, update: Update, context: CallbackContext):
        """Advanced start command with interactive menu"""
        user = update.effective_user
        self.save_user(user)
        
        keyboard = [
            [InlineKeyboardButton("🎮 Quick Play vs AI", callback_data="quick_play")],
            [InlineKeyboardButton("👥 Create Multiplayer Room", callback_data="create_room")],
            [InlineKeyboardButton("📊 My Profile", callback_data="my_profile")],
            [InlineKeyboardButton("📋 How to Play", callback_data="how_to_play")],
            [InlineKeyboardButton("🎯 Available Commands", callback_data="show_commands")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎲 *Welcome to Advanced Ludo Bot, {user.first_name}!* 👑\n\n"
            "Use the buttons below to start playing or type /help for commands list.\n\n"
            "⚡ *Available Commands:*\n"
            "/start - Main menu\n"
            "/ludo - Create game room\n"  
            "/play - Quick play vs AI\n"
            "/roll - Roll dice\n"
            "/board - Show game board\n"
            "/profile - Your stats\n"
            "/leaderboard - Top players",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )




async def ludo_start(self, update: Update, context: CallbackContext):
    """Create Ludo game room"""
    user = update.effective_user
    
    # Create waiting room
    room_id = game_manager.create_waiting_room(user.id, user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("🔴 Join Red", callback_data=f"join_red_{room_id}"),
         InlineKeyboardButton("🔵 Join Blue", callback_data=f"join_blue_{room_id}")],
        [InlineKeyboardButton("🟡 Join Yellow", callback_data=f"join_yellow_{room_id}"),
         InlineKeyboardButton("🟢 Join Green", callback_data=f"join_green_{room_id}")],
        [InlineKeyboardButton("🎮 Start Game", callback_data=f"start_game_{room_id}"),
         InlineKeyboardButton("🤖 Add AI Players", callback_data=f"add_ai_{room_id}")],
        [InlineKeyboardButton("❌ Leave Room", callback_data=f"leave_room_{room_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎯 *Ludo Game Room Created!*\n\n"
        f"👤 *Room Creator:* {user.first_name}\n"
        f"🔗 *Room ID:* `{room_id}`\n\n"
        f"👥 *Players (1/4):*\n"
        f"🔴 Red: {user.first_name}\n"  
        f"🔵 Blue: Available\n"
        f"🟡 Yellow: Available\n"
        f"🟢 Green: Available\n\n"
        f"Share this room ID with friends: `{room_id}`\n"
        f"Or let them use: /join {room_id}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quick_play(self, update: Update, context: CallbackContext):
    """Quick play with AI opponents"""
    user = update.effective_user
    
    # Create game with AI players
    room_id = game_manager.create_waiting_room(user.id, user.first_name)
    
    # Add AI players
    ai_players = [
        {'id': 'ai_blue', 'name': 'Computer 2', 'color': 'blue'},
        {'id': 'ai_green', 'name': 'Computer 3', 'color': 'green'}, 
        {'id': 'ai_yellow', 'name': 'Computer 4', 'color': 'yellow'}
    ]
    
    for ai in ai_players:
        game_manager.join_waiting_room(room_id, ai['id'], ai['name'], ai['color'])
    
    # Start game immediately
    game_id = game_manager.start_game(room_id)
    
    if game_id:
        game_data = game_manager.get_game(game_id)
        game = game_data['game']
        
        # Show game board
        await self.display_game_board(update, context, game_id, user.id)

async def display_game_board(self, update: Update, context: CallbackContext, game_id: str, user_id: int):
    """Display interactive game board"""
    game_data = game_manager.get_game(game_id)
    if not game_data:
        return
    
    game = game_data['game']
    players = game_data['players']
    
    # Create board visualization
    board_text = self.create_board_visualization(game)
    
    # Show whose turn it is
    current_player_id = game.get_current_player()
    current_player_name = players[current_player_id]['name'] if current_player_id in players else "AI"
    
    # Create action buttons based on turn
    keyboard = []
    if current_player_id == user_id:
        keyboard.append([InlineKeyboardButton("🎲 Roll Dice", callback_data=f"roll_{game_id}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Refresh Board", callback_data=f"refresh_{game_id}")])
    keyboard.append([InlineKeyboardButton("🏃 Leave Game", callback_data=f"leave_game_{game_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"🎲 *LUDO GAME BOARD* 🎲\n\n"
        f"{board_text}\n\n"
        f"🎯 *Current Turn:* {current_player_name}\n"
        f"🎲 *Last Dice:* {game.dice_value if game.dice_value > 0 else 'Not rolled yet'}\n\n"
        f"🕹️ *Controls:*\n"
    )
    
    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )





    def create_board_visualization(self, game):
        """Create visual board representation"""
        # Simple ASCII board - you can enhance this with emojis
        board = """
┌───────── LUDO BOARD ─────────┐
│ 🏠●     ●     ●     ●🏠 │
│   ● 🔴        🟢     ●   │
│ 🏠●           ●     ●🏠 │
│   ●     ●           ●   │
│ 🏠●     ●  🟡     ●🏠 │
│   ●           ●     ●   │
│ 🏠●     ●     ●  🔵●🏠 │
└─────────────────────────┘
"""
        
        # Add player information
        player_info = ""
        for user_id, player_data in game.players.items():
            color_emoji = {
                'red': '🔴', 'blue': '🔵', 
                'green': '🟢', 'yellow': '🟡'
            }
            emoji = color_emoji.get(player_data['color'], '⚫')
            tokens_pos = game.board[player_data['color']]['tokens']
            tokens_status = []
            
            for i, pos in enumerate(tokens_pos):
                if pos == -1:
                    tokens_status.append("HOME")
                elif pos >= 51:
                    tokens_status.append("SAFE")
                else:
                    tokens_status.append(f"POS{pos}")
            
            player_info += f"{emoji} {player_data['name']}: {', '.join(tokens_status[:2])}\n"
        
        return f"```{board}```\n\n*Player Status:*\n{player_info}"
    
    async def roll_dice_command(self, update: Update, context: CallbackContext):
        """Handle roll dice command"""
        user = update.effective_user
        
        # Find active game for user
        game_id = None
        for gid, game_data in game_manager.active_games.items():
            if user.id in game_data['players']:
                game_id = gid
                break
        
        if not game_id:
            await update.message.reply_text("❌ You are not in any active game! Use /ludo to start one.")
            return
        
        await self.roll_dice_in_game(update, context, game_id, user.id)
    
    async def roll_dice_in_game(self, update: Update, context: CallbackContext, game_id: str, user_id: int):
        """Roll dice in specific game"""
        game_data = game_manager.get_game(game_id)
        if not game_data:
            return
        
        game = game_data['game']
        
        # Check if it's user's turn
        if game.get_current_player() != user_id:
            await update.message.reply_text("❌ It's not your turn!")
            return
        
        # Roll dice
        dice_value = game.roll_dice()
        dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        
        # Send dice animation
        if hasattr(update, 'callback_query'):
            msg = update.callback_query.message
            rolling_msg = await msg.edit_text("🎲 Rolling dice...")
        else:
            rolling_msg = await update.message.reply_text("🎲 Rolling dice...")
        
        # Simulate rolling animation
        await asyncio.sleep(1)
        
        # Check for available moves
        player_color = game_data['players'][user_id]['color']
        available_moves = []
        
        for i in range(4):
            if game.can_move_token(player_color, i):
                available_moves.append(i)
        
        # Create move buttons if moves available
        keyboard = []
        if available_moves:
            move_buttons = []
            for move_idx in available_moves:
                move_buttons.append(InlineKeyboardButton(
                    f"Token {move_idx + 1}", 
                    callback_data=f"move_{game_id}_{move_idx}"
                ))
            keyboard.append(move_buttons)
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{game_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            f"🎲 *Dice Rolled!* {dice_emojis[dice_value]} **{dice_value}**\n\n"
        )
        
        if dice_value == 6:
            message_text += "🎉 *Lucky 6!* You get an extra turn!\n\n"
        
        if available_moves:
            message_text += "✅ *Available Moves:* Select a token to move:"
        else:
            message_text += "❌ *No moves available.* Turn passes to next player."
            # Auto proceed to next turn if no moves
            game.next_turn()
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await rolling_msg.edit_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )






    async def button_handler(self, update: Update, context: CallbackContext):
        """Handle all button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        # Join room buttons
        if data.startswith("join_"):
            parts = data.split("_")
            if len(parts) == 3:
                color = parts[1]
                room_id = parts[2]
                
                success = game_manager.join_waiting_room(
                    room_id, user.id, user.first_name, color
                )
                
                if success:
                    room = game_manager.get_waiting_room(room_id)
                    
                    # Update room display
                    players_text = ""
                    for player_id, player_data in room['players'].items():
                        color_emoji = {
                            'red': '🔴', 'blue': '🔵', 
                            'green': '🟢', 'yellow': '🟡'
                        }
                        emoji = color_emoji.get(player_data['color'], '⚫')
                        players_text += f"{emoji} {player_data['name']}\n"
                    
                    keyboard = [
                        [InlineKeyboardButton("🔴 Join Red", callback_data=f"join_red_{room_id}"),
                         InlineKeyboardButton("🔵 Join Blue", callback_data=f"join_blue_{room_id}")],
                        [InlineKeyboardButton("🟡 Join Yellow", callback_data=f"join_yellow_{room_id}"),
                         InlineKeyboardButton("🟢 Join Green", callback_data=f"join_green_{room_id}")],
                        [InlineKeyboardButton("🎮 Start Game", callback_data=f"start_game_{room_id}"),
                         InlineKeyboardButton("🤖 Add AI Players", callback_data=f"add_ai_{room_id}")],
                        [InlineKeyboardButton("❌ Leave Room", callback_data=f"leave_room_{room_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"🎯 *Ludo Game Room*\n\n"
                        f"👥 *Players ({len(room['players'])}/4):*\n{players_text}\n"
                        f"Share room ID: `{room_id}`",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text("❌ Could not join room. It might be full!")
        
        # Start game button
        elif data.startswith("start_game_"):
            room_id = data.split("_")[2]
            room = game_manager.get_waiting_room(room_id)
            
            if room and room['creator'] == user.id:
                game_id = game_manager.start_game(room_id)
                if game_id:
                    await self.display_game_board(query, context, game_id, user.id)
        
        # Roll dice button
        elif data.startswith("roll_"):
            game_id = data.split("_")[1]
            await self.roll_dice_in_game(query, context, game_id, user.id)
        
        # Move token button
        elif data.startswith("move_"):
            parts = data.split("_")
            game_id = parts[1]
            token_index = int(parts[2])
            
            game_data = game_manager.get_game(game_id)
            if game_data and user.id in game_data['players']:
                game = game_data['game']
                player_color = game_data['players'][user.id]['color']
                
                # Move token
                extra_turn = game.move_token(player_color, token_index)
                
                # Check for winner
                winner_id = game.check_winner()
                if winner_id:
                    winner_name = game_data['players'][winner_id]['name']
                    await query.edit_message_text(
                        f"🎉 *GAME OVER!* 🎉\n\n"
                        f"🏆 **{winner_name} WINS!** 🏆\n\n"
                        f"Thanks for playing! Use /ludo to start a new game.",
                        parse_mode='Markdown'
                    )
                    # Clean up game
                    if game_id in game_manager.active_games:
                        del game_manager.active_games[game_id]
                    return
                
                # Move to next turn if no extra turn
                if not extra_turn:
                    game.next_turn()
                
                # Refresh board
                await self.display_game_board(query, context, game_id, user.id)
        
        # Refresh board button
        elif data.startswith("refresh_"):
            game_id = data.split("_")[1]
            await self.display_game_board(query, context, game_id, user.id)
        
        # Quick play button
        elif data == "quick_play":
            await self.quick_play(query, context)
        
        # Show commands button
        elif data == "show_commands":
            await self.show_commands(query, context)
        
        # How to play button
        elif data == "how_to_play":
            await query.edit_message_text(
                "📋 *Ludo Game Rules:*\n\n"
                "🎯 *Objective:*\nGet all 4 tokens to home first!\n\n"
                "🎲 *Gameplay:*\n"
                "• Roll dice with /roll or button\n"
                "• Move tokens around board\n"
                "• Get 6 for extra turn\n"
                "• Capture opponent tokens\n"
                "• Reach home path to win\n\n"
                "🏆 *Winning:*\nFirst to get all tokens home wins!\n\n"
                "💡 *Tips:*\n"
                "• Use 6 to bring out new tokens\n"
                "• Block opponents when possible\n"
                "• Safe zones protect your tokens",
                parse_mode='Markdown'
            )
    
    async def show_commands(self, update: Update, context: CallbackContext):
        """Show available commands"""
        commands_text = """
🎲 *LUDO BOT COMMANDS* 🎲

*🎮 Game Commands:*
/start - Main menu with buttons
/ludo - Create multiplayer room  
/play - Quick play vs AI
/roll - Roll dice (in game)
/board - Show game board
/profile - Your player stats
/leaderboard - Top players

*👥 Multiplayer:*
• Use /ludo to create room
• Share room ID with friends
• Join via buttons or /join <room_id>

*🕹️ How to Play:*
1. Use /ludo or /play to start
2. Roll dice when it's your turn
3. Move tokens around board
4. Capture opponent tokens
5. First to home all tokens wins!

*⚡ Features:*
• Interactive board
• Real-time gameplay
• AI opponents  
• Player statistics
• Multiplayer rooms
        """
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                commands_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                commands_text,
                parse_mode='Markdown'
            )





    async def show_board(self, update: Update, context: CallbackContext):
        """Show game board command"""
        user = update.effective_user
        
        # Find active game for user
        game_id = None
        for gid, game_data in game_manager.active_games.items():
            if user.id in game_data['players']:
                game_id = gid
                break
        
        if game_id:
            await self.display_game_board(update, context, game_id, user.id)
        else:
            await update.message.reply_text("❌ You are not in any active game! Use /ludo to start one.")

    async def profile_command(self, update: Update, context: CallbackContext):
        """Show user profile with stats"""
        user = update.effective_user
        conn = sqlite3.connect('ludo_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT games_played, games_won, total_coins FROM users WHERE user_id = ?
        ''', (user.id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            games_played, games_won, total_coins = result
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
            
            profile_text = f"""
📊 *Player Profile:* {user.first_name}

🎮 *Statistics:*
• Games Played: {games_played}
• Games Won: {games_won}
• Win Rate: {win_rate:.1f}%
• Total Coins: 🪙 {total_coins}

🏆 *Achievements:*
{'🥇 Ludo Master' if games_won >= 10 else '🎯 Beginner'}
{'💰 Rich Player' if total_coins >= 5000 else '💸 New Player'}

🌟 *Keep playing to unlock more features!*
            """
        else:
            profile_text = "📊 *Profile not found!* Use /start to create your profile."
        
        await update.message.reply_text(profile_text, parse_mode='Markdown')
    
    async def leaderboard_command(self, update: Update, context: CallbackContext):
        """Show global leaderboard"""
        conn = sqlite3.connect('ludo_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, games_won, total_coins 
            FROM users 
            WHERE games_played > 0 
            ORDER BY games_won DESC, total_coins DESC 
            LIMIT 10
        ''')
        
        top_players = cursor.fetchall()
        conn.close()
        
        leaderboard_text = "🏆 *Global Leaderboard*\n\n"
        
        for idx, (username, wins, coins) in enumerate(top_players, 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            name = username if username else "Anonymous"
            leaderboard_text += f"{medal} {name}\n   🏅 {wins} wins | 🪙 {coins} coins\n\n"
        
        if not top_players:
            leaderboard_text += "No players yet! Be the first to play! 🎮"
        
        await update.message.reply_text(leaderboard_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Help command"""
        await self.show_commands(update, context)
    
    def run(self):
        """Start the bot"""
        print("🤖 Advanced Ludo Bot Starting...")
        print("🎲 Features: Interactive Board, Multiplayer, AI Opponents")
        print("🚀 Bot is ready!")
        self.application.run_polling()

def run_flask():
    """Run Flask server in separate thread"""
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# Start Flask server
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Start the bot
if __name__ == "__main__":
    bot = AdvancedLudoBot(BOT_TOKEN)
    bot.run()
