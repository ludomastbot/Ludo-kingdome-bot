#!/usr/bin/env python3
import os
import logging
import sqlite3
import random
import json
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

# Bot Token (Render environment variable se ayega)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8403232282:AAGXrSzIciS5aEQSUJMs-iZ82LuTtEGBa8o')

# Flask app for web server
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>🎲 Ludo Kingdom</title></head>
        <body style="text-align: center; padding: 50px; font-family: Arial;">
            <h1>🎲 Ludo Kingdom Bot</h1>
            <p>🤖 Advanced Ludo Gaming Bot</p>
            <p>🚀 24/7 Online on Render.com</p>
            <p>👉 <a href="https://t.me/Ludomastbot">Play Now</a></p>
        </body>
    </html>
    """

@app.route('/ping')
def ping():
    return "pong"

@app.route('/status')
def status():
    return {
        "status": "online",
        "bot": "Ludo Kingdom Advanced",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    }

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

class AdvancedLudoBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.active_games = {}
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
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def save_user(self, user):
        """Save user to database"""
        conn = sqlite3.connect('ludo_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, total_coins)
            VALUES (?, ?, ?, COALESCE((SELECT total_coins FROM users WHERE user_id = ?), 1000))
        ''', (user.id, user.username, user.first_name, user.id))
        
        conn.commit()
        conn.close()

    async def start_command(self, update: Update, context: CallbackContext):
        """Advanced start command with interactive menu"""
        user = update.effective_user
        self.save_user(user)
        
        keyboard = [
            [InlineKeyboardButton("🎮 Quick Play", callback_data="quick_play"),
             InlineKeyboardButton("👥 Multiplayer", callback_data="multiplayer")],
            [InlineKeyboardButton("🏆 Tournament", callback_data="tournament"),
             InlineKeyboardButton("🤖 VS AI", callback_data="vs_ai")],
            [InlineKeyboardButton("📊 My Profile", callback_data="my_profile"),
             InlineKeyboardButton("📋 How to Play", callback_data="how_to_play")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎲 *Welcome to Ludo Kingdom, {user.first_name}!* 👑\n\n"
            "⚡ *Advanced Features:*\n"
            "• Multiple Game Modes\n"
            "• Real-time Multiplayer\n"  
            "• AI Opponents\n"
            "• Player Profiles\n"
            "• Tournament System\n\n"
            "🚀 *24/7 Online on Render Cloud*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def ludo_start(self, update: Update, context: CallbackContext):
        """Ludo game lobby with color selection"""
        keyboard = [
            [InlineKeyboardButton("🔴 Join Red", callback_data="join_red"),
             InlineKeyboardButton("🔵 Join Blue", callback_data="join_blue")],
            [InlineKeyboardButton("🟡 Join Yellow", callback_data="join_yellow"),
             InlineKeyboardButton("🟢 Join Green", callback_data="join_green")],
            [InlineKeyboardButton("🎮 Start Game", callback_data="start_game"),
             InlineKeyboardButton("🤖 Add Bots", callback_data="add_bots")],
            [InlineKeyboardButton("⚙️ Game Settings", callback_data="game_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 *Ludo Game Lobby* 🎯\n\n"
            "👥 *Players (1/4):*\n"
            "🔴 Red: Available\n"  
            "🔵 Blue: Available\n"
            "🟡 Yellow: Available\n"
            "🟢 Green: Available\n\n"
            "🎮 *Game Mode:* Classic\n"
            "⏱️ *Turn Time:* 30 seconds\n\n"
            "Choose your color or add AI players:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def quick_play(self, update: Update, context: CallbackContext):
        """Quick play with AI"""
        user = update.effective_user
        
        # Update user stats
        conn = sqlite3.connect('ludo_bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET games_played = games_played + 1 WHERE user_id = ?", (user.id,))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("🎲 Roll Dice", callback_data="roll_dice_quick")],
            [InlineKeyboardButton("📊 View Board", callback_data="view_board")],
            [InlineKeyboardButton("🏃 Leave Game", callback_data="leave_game")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚀 *Quick Game Started!*\n\n"
            "🎮 *Mode:* Classic Ludo\n"
            "👥 *Players:* You + 3 AI\n"
            "🔴 *Your Color:* Red\n"
            "🎲 *First Turn:* You\n\n"
            "Tap below to roll dice:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def roll_dice(self, update: Update, context: CallbackContext):
        """Roll dice with animations"""
        dice_value = random.randint(1, 6)
        
        # Dice animations
        dice_emojis = {
            1: "⚀", 2: "⚁", 3: "⚂", 
            4: "⚃", 5: "⚄", 6: "⚅"
        }
        
        if dice_value == 6:
            message = "🎉 *Lucky 6!* Extra turn! Roll again!"
            bonus = " +100 coins bonus!"
        else:
            message = f"Move your token {dice_value} spaces!"
            bonus = ""
        
        # Send rolling animation
        rolling_msg = await update.message.reply_text("🎲 Rolling dice...")
        
        # Simulate rolling
        import time
        time.sleep(1)
        
        keyboard = [[InlineKeyboardButton("🎲 Roll Again", callback_data="roll_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await rolling_msg.edit_text(
            f"🎲 *Dice Roll Result:*\n\n"
            f"{dice_emojis[dice_value]} **{dice_value}**\n\n"
            f"{message}{bonus}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def show_board(self, update: Update, context: CallbackContext):
        """Show advanced game board"""
        board = """
┌───────── LUDO BOARD ─────────┐
│ 🏠 ●     ●     ●     ● 🏠 │
│   ● 🔴1        🟢3     ●   │
│ 🏠 ●           ●     ● 🏠 │
│   ●     ●           ●   │
│ 🏠 ●     ●  🟡2    ● 🏠 │
│   ●           ●     ●   │
│ 🏠 ●     ●     ●  🔵4 ● 🏠 │
└─────────────────────────┘

🎮 *Game Info:*
🔴 You (Red) - Token 1: START
🟢 AI (Green) - Token 3: Position 15
🟡 AI (Yellow) - Token 2: Position 8  
🔵 AI (Blue) - Token 4: HOME

🎲 Current Turn: 🔴 You
        """
        await update.message.reply_text(f"```{board}```", parse_mode='MarkdownV2')
    
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
    
    async def admin_command(self, update: Update, context: CallbackContext):
        """Admin panel"""
        user = update.effective_user
        
        # Simple admin check (you can add proper admin system)
        if user.id == 123456789:  # Replace with your user ID
            keyboard = [
                [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats"),
                 InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
                [InlineKeyboardButton("🎮 Game Management", callback_data="admin_games"),
                 InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚙️ *Admin Panel*\n\n"
                "Welcome to bot administration!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ *Access Denied*\nAdmin privileges required.", parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Advanced help command"""
        help_text = """
🎲 *LUDO KINGDOM - ADVANCED BOT* 🚀

*🎮 GAME COMMANDS:*
/start - Advanced menu
/ludo - Create game room  
/play - Quick play vs AI
/roll - Roll dice with animations
/board - View game board
/profile - Your player profile
/leaderboard - Global rankings

*👥 SOCIAL FEATURES:*
• Player profiles with stats
• Global leaderboard
• Win/loss tracking
• Coin system

*⚡ ADVANCED FEATURES:*
• Multiple game modes
• AI opponents (3 difficulty levels)
• Real-time multiplayer ready
• Tournament system
• 24/7 cloud hosting

*🔧 TECHNICAL:*
• SQLite database
• Flask web server
• Render.com hosting
• Always online!
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def button_handler(self, update: Update, context: CallbackContext):
        """Handle all button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Game lobby buttons
        if data.startswith("join_"):
            color = data.split("_")[1]
            color_emoji = {"red": "🔴", "blue": "🔵", "yellow": "🟡", "green": "🟢"}
            await query.edit_message_text(
                f"✅ *Joined as {color_emoji[color]} {color.upper()} Team!*\n\n"
                f"🟢 Waiting for other players...\n\n"
                f"Share bot with friends:\n*t.me/Ludomastbot*",
                parse_mode='Markdown'
            )
        
        elif data == "start_game":
            await query.edit_message_text(
                "🚀 *Game Started!*\n\n"
                "🎮 Mode: 4 Player Ludo\n"
                "👥 Players: You + 3 AI\n"
                "🔴 Your Color: Red\n"
                "🎲 First Turn: You\n\n"
                "Use /roll to roll dice!",
                parse_mode='Markdown'
            )
        
        elif data == "quick_play":
            await self.quick_play(query, context)
        
        elif data == "roll_dice_quick" or data == "roll_again":
            await self.roll_dice(query, context)
        
        elif data == "my_profile":
            await self.profile_command(query, context)
        
        elif data == "how_to_play":
            await query.edit_message_text(
                "📋 *Ludo Game Rules:*\n\n"
                "🎯 *Objective:*\nGet all 4 tokens to home first!\n\n"
                "🎲 *Gameplay:*\n"
                "• Roll dice with /roll\n"
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
        
        elif data == "multiplayer":
            await query.edit_message_text(
                "👥 *Multiplayer Mode*\n\n"
                "Invite friends to play:\n"
                "1. Share bot link with friends\n"
                "2. Use /ludo to create room\n"
                "3. Friends choose colors\n"
                "4. Start playing together!\n\n"
                "🔗 *Bot Link:* t.me/Ludomastbot\n\n"
                "Real-time gameplay coming soon!",
                parse_mode='Markdown'
            )
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle non-command messages"""
        user_message = update.message.text.lower()
        
        if any(word in user_message for word in ['hello', 'hi', 'hey', 'namaste']):
            await update.message.reply_text(
                f"👋 Hello {update.effective_user.first_name}! Ready to play Ludo? Use /start to begin!",
                parse_mode='Markdown'
            )
    
    def run(self):
        """Start the bot"""
        print("🤖 Advanced Ludo Bot Starting...")
        print("🌐 Flask server running on port 8080")
        print("🚀 Bot will be deployed to Render.com")
        self.application.run_polling()

def run_flask():
    """Run Flask server in separate thread"""
    app.run(host='0.0.0.0', port=8080, debug=False)

# Start Flask server
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Start the bot
if __name__ == "__main__":
    bot = AdvancedLudoBot(BOT_TOKEN)
    bot.run()
