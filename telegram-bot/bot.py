#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forex Trading Journal Telegram Bot
Author: AI Assistant
Date: 2026-06-23
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token
BOT_TOKEN = "8269807517:AAGmyZ4qkK2P3mVeDqeg8ItgpmMM9CimgMo"

# Database
DB_FILE = "forex_journal.db"

# Conversation states
PAIR, TYPE, ENTRY, EXIT, STOPLOSS, TAKEPROFIT, LOT, NOTES = range(8)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pair TEXT NOT NULL,
            type TEXT NOT NULL,
            entry REAL NOT NULL,
            exit_price REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            lot_size REAL NOT NULL,
            pips REAL,
            profit_usd REAL,
            notes TEXT,
            open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            close_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()



# Helper functions
def calculate_pips(entry, exit_price, trade_type, pair):
    """Calculate pips based on pair"""
    multiplier = 10000 if 'JPY' not in pair else 100
    if trade_type.upper() == 'BUY':
        pips = (exit_price - entry) * multiplier
    else:
        pips = (entry - exit_price) * multiplier
    return round(pips, 1)

def calculate_profit_usd(pips, lot_size, pair):
    """Calculate profit in USD"""
    pip_value = 10 if 'JPY' not in pair else 1000
    profit = (pips / 10) * pip_value * lot_size
    return round(profit, 2)

def get_user_stats(user_id):
    """Get user trading statistics"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Total trades
    c.execute("SELECT COUNT(*) FROM trades WHERE user_id = ?", (user_id,))
    total_trades = c.fetchone()[0]
    
    if total_trades == 0:
        conn.close()
        return None
    
    # Win/Loss trades
    c.execute("SELECT COUNT(*) FROM trades WHERE user_id = ? AND profit_usd > 0", (user_id,))
    win_trades = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM trades WHERE user_id = ? AND profit_usd < 0", (user_id,))
    loss_trades = c.fetchone()[0]
    
    # Profit stats
    c.execute("SELECT SUM(profit_usd) FROM trades WHERE user_id = ? AND profit_usd > 0", (user_id,))
    total_profit = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(ABS(profit_usd)) FROM trades WHERE user_id = ? AND profit_usd < 0", (user_id,))
    total_loss = c.fetchone()[0] or 0
    
    net_profit = total_profit - total_loss
    
    # Best/Worst trades
    c.execute("SELECT MAX(profit_usd) FROM trades WHERE user_id = ?", (user_id,))
    best_trade = c.fetchone()[0] or 0
    
    c.execute("SELECT MIN(profit_usd) FROM trades WHERE user_id = ?", (user_id,))
    worst_trade = c.fetchone()[0] or 0
    
    conn.close()
    
    win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else total_profit
    
    return {
        'total_trades': total_trades,
        'win_trades': win_trades,
        'loss_trades': loss_trades,
        'win_rate': round(win_rate, 1),
        'total_profit': round(total_profit, 2),
        'total_loss': round(total_loss, 2),
        'net_profit': round(net_profit, 2),
        'profit_factor': round(profit_factor, 2),
        'best_trade': round(best_trade, 2),
        'worst_trade': round(worst_trade, 2)
    }



# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Yangi Trade", callback_data='add_trade'),
            InlineKeyboardButton("📊 Statistika", callback_data='stats')
        ],
        [
            InlineKeyboardButton("📋 Tradelar", callback_data='list_trades'),
            InlineKeyboardButton("📅 Bugun", callback_data='today')
        ],
        [
            InlineKeyboardButton("❓ Yordam", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
👋 Assalomu alaykum, {user.first_name}!

🤖 **Forex Trading Journal** botiga xush kelibsiz!

Bu bot orqali siz:
✅ Tradelaringizni oson qo'shishingiz
✅ Statistikani real-time ko'rishingiz
✅ Tahlil qilishingiz mumkin

📊 Quyidagi tugmalardan birini tanlang:
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics command"""
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    if not stats:
        keyboard = [[InlineKeyboardButton("➕ Birinchi Trade", callback_data='add_trade')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "❌ Hali tradelar yo'q!\n\nBirinchi tradeni qo'shing 👇",
            reply_markup=reply_markup
        )
        return
    
    stats_text = f"""
📊 **STATISTIKA**
{'━' * 25}

📈 Jami tradelar: **{stats['total_trades']}**
✅ Yutish: **{stats['win_trades']}** ({stats['win_rate']}%)
❌ Zarar: **{stats['loss_trades']}**

💰 **FOYDA/ZARAR:**
Jami Foyda: **${stats['total_profit']}**
Jami Zarar: **${stats['total_loss']}**
Net Profit: **${stats['net_profit']}**

📊 Profit Factor: **{stats['profit_factor']}**

🏆 **ENG YAXSHI/YOMON:**
Eng Yaxshi: **${stats['best_trade']}**
Eng Yomon: **${stats['worst_trade']}**
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Tradelar", callback_data='list_trades'),
            InlineKeyboardButton("📅 Bugun", callback_data='today')
        ],
        [InlineKeyboardButton("➕ Yangi Trade", callback_data='add_trade')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')



async def list_trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List recent trades"""
    user_id = update.effective_user.id
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT pair, type, entry, exit_price, pips, profit_usd, close_time 
        FROM trades 
        WHERE user_id = ? 
        ORDER BY close_time DESC 
        LIMIT 10
    """, (user_id,))
    
    trades = c.fetchall()
    conn.close()
    
    if not trades:
        await update.message.reply_text("❌ Hali tradelar yo'q!")
        return
    
    text = "📋 **OXIRGI TRADELAR:**\n" + "━" * 25 + "\n\n"
    
    for trade in trades:
        pair, trade_type, entry, exit_p, pips, profit, close_time = trade
        profit_emoji = "✅" if profit > 0 else "❌"
        date = datetime.fromisoformat(close_time).strftime("%d.%m %H:%M")
        
        text += f"{date} | **{pair}** {trade_type}\n"
        text += f"↗️ {entry} → {exit_p}\n"
        text += f"{profit_emoji} {pips:+.1f} pips | ${profit:+.2f}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Statistika", callback_data='stats')],
        [InlineKeyboardButton("➕ Yangi Trade", callback_data='add_trade')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today's trades"""
    user_id = update.effective_user.id
    today = datetime.now().date()
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT pair, type, pips, profit_usd, close_time 
        FROM trades 
        WHERE user_id = ? AND DATE(close_time) = ?
        ORDER BY close_time DESC
    """, (user_id, today))
    
    trades = c.fetchall()
    conn.close()
    
    if not trades:
        await update.message.reply_text("❌ Bugun hali tradelar yo'q!")
        return
    
    total_profit = sum(t[3] for t in trades)
    wins = sum(1 for t in trades if t[3] > 0)
    losses = len(trades) - wins
    
    text = f"📅 **BUGUNGI TRADELAR:**\n{'━' * 25}\n\n"
    
    for trade in trades:
        pair, trade_type, pips, profit, close_time = trade
        profit_emoji = "✅" if profit > 0 else "❌"
        time = datetime.fromisoformat(close_time).strftime("%H:%M")
        
        text += f"{time} | {pair} {trade_type}\n"
        text += f"{profit_emoji} {pips:+.1f} pips (${profit:+.2f})\n\n"
    
    text += f"{'━' * 25}\n"
    text += f"📊 Jami: {len(trades)} | ✅ {wins} | ❌ {losses}\n"
    text += f"💰 Bugun: **${total_profit:+.2f}**"
    
    await update.message.reply_text(text, parse_mode='Markdown')



# Conversation handler for adding trade
async def add_trade_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a trade"""
    query = update.callback_query
    await query.answer()
    
    pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'NZD/USD', 'USD/CAD']
    
    keyboard = [[InlineKeyboardButton(pair, callback_data=f'pair_{pair}')] for pair in pairs]
    keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📊 **YANGI TRADE QO'SHISH**\n\n1️⃣ Valyuta juftini tanlang:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return PAIR

async def pair_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pair selected"""
    query = update.callback_query
    await query.answer()
    
    pair = query.data.replace('pair_', '')
    context.user_data['pair'] = pair
    
    keyboard = [
        [InlineKeyboardButton("📈 BUY", callback_data='type_BUY')],
        [InlineKeyboardButton("📉 SELL", callback_data='type_SELL')],
        [InlineKeyboardButton("◀️ Orqaga", callback_data='add_trade')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 **YANGI TRADE**\n\nValyuta: **{pair}**\n\n2️⃣ Buy yoki Sell?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return TYPE

async def type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Type selected"""
    query = update.callback_query
    await query.answer()
    
    trade_type = query.data.replace('type_', '')
    context.user_data['type'] = trade_type
    
    pair = context.user_data['pair']
    
    await query.edit_message_text(
        f"📊 **YANGI TRADE**\n\nValyuta: **{pair}**\nTuri: **{trade_type}**\n\n3️⃣ Entry narxni yuboring:\n\n_Masalan: 1.0850_",
        parse_mode='Markdown'
    )
    
    return ENTRY

async def entry_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry price received"""
    try:
        entry = float(update.message.text.strip())
        context.user_data['entry'] = entry
        
        pair = context.user_data['pair']
        trade_type = context.user_data['type']
        
        await update.message.reply_text(
            f"📊 **YANGI TRADE**\n\nValyuta: **{pair}**\nTuri: **{trade_type}**\nEntry: **{entry}**\n\n4️⃣ Exit narxni yuboring:\n\n_Masalan: 1.0890_",
            parse_mode='Markdown'
        )
        
        return EXIT
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Raqam kiriting, masalan: 1.0850")
        return ENTRY

async def exit_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exit price received"""
    try:
        exit_price = float(update.message.text.strip())
        context.user_data['exit'] = exit_price
        
        # Skip SL/TP for simplicity, ask for lot
        await update.message.reply_text(
            "5️⃣ Lot hajmini yuboring:\n\n_Masalan: 0.1_",
            parse_mode='Markdown'
        )
        
        return LOT
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Raqam kiriting, masalan: 1.0890")
        return EXIT



async def lot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lot size received"""
    try:
        lot_size = float(update.message.text.strip())
        context.user_data['lot'] = lot_size
        
        await update.message.reply_text(
            "6️⃣ Izoh yozing (yoki /skip):\n\n_Masalan: Yaxshi trend, support dan sakradi_",
            parse_mode='Markdown'
        )
        
        return NOTES
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri format! Raqam kiriting, masalan: 0.1")
        return LOT

async def notes_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notes received - save trade"""
    notes = update.message.text.strip() if update.message.text != '/skip' else ''
    
    # Get all data
    user_id = update.effective_user.id
    pair = context.user_data['pair']
    trade_type = context.user_data['type']
    entry = context.user_data['entry']
    exit_price = context.user_data['exit']
    lot_size = context.user_data['lot']
    
    # Calculate
    pips = calculate_pips(entry, exit_price, trade_type, pair)
    profit_usd = calculate_profit_usd(pips, lot_size, pair)
    
    # Save to database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO trades (
            user_id, pair, type, entry, exit_price, lot_size, 
            pips, profit_usd, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, pair, trade_type, entry, exit_price, lot_size, pips, profit_usd, notes))
    conn.commit()
    conn.close()
    
    # Get updated stats
    stats = get_user_stats(user_id)
    
    profit_emoji = "✅" if profit_usd > 0 else "❌"
    
    result_text = f"""
{profit_emoji} **TRADE SAQLANDI!**
{'━' * 25}

📊 **{pair}** {trade_type}
↗️ {entry} → {exit_price}
{profit_emoji} **{pips:+.1f} pips | ${profit_usd:+.2f}**

📈 **YANGI STATISTIKA:**
Jami: {stats['total_trades']} | Win Rate: {stats['win_rate']}%
Net Profit: ${stats['net_profit']}
"""
    
    keyboard = [
        [
            InlineKeyboardButton("➕ Yana qo'shish", callback_data='add_trade'),
            InlineKeyboardButton("📊 Statistika", callback_data='stats')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Bekor qilindi.")
    context.user_data.clear()
    return ConversationHandler.END



# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'stats':
        user_id = update.effective_user.id
        stats = get_user_stats(user_id)
        
        if not stats:
            keyboard = [[InlineKeyboardButton("➕ Birinchi Trade", callback_data='add_trade')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Hali tradelar yo'q!\n\nBirinchi tradeni qo'shing 👇",
                reply_markup=reply_markup
            )
            return
        
        stats_text = f"""
📊 **STATISTIKA**
{'━' * 25}

📈 Jami: **{stats['total_trades']}**
✅ Yutish: **{stats['win_trades']}** ({stats['win_rate']}%)
❌ Zarar: **{stats['loss_trades']}**

💰 Net Profit: **${stats['net_profit']}**
📊 Profit Factor: **{stats['profit_factor']}**

🏆 Eng Yaxshi: **${stats['best_trade']}**
📉 Eng Yomon: **${stats['worst_trade']}**
"""
        
        keyboard = [
            [InlineKeyboardButton("◀️ Orqaga", callback_data='start')],
            [InlineKeyboardButton("➕ Yangi Trade", callback_data='add_trade')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'list_trades':
        user_id = update.effective_user.id
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT pair, type, pips, profit_usd, close_time 
            FROM trades 
            WHERE user_id = ? 
            ORDER BY close_time DESC 
            LIMIT 5
        """, (user_id,))
        
        trades = c.fetchall()
        conn.close()
        
        if not trades:
            await query.edit_message_text("❌ Hali tradelar yo'q!")
            return
        
        text = "📋 **OXIRGI TRADELAR:**\n" + "━" * 25 + "\n\n"
        
        for trade in trades:
            pair, trade_type, pips, profit, close_time = trade
            profit_emoji = "✅" if profit > 0 else "❌"
            date = datetime.fromisoformat(close_time).strftime("%d.%m %H:%M")
            
            text += f"{date} | **{pair}** {trade_type}\n"
            text += f"{profit_emoji} {pips:+.1f} pips (${profit:+.2f})\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'today':
        user_id = update.effective_user.id
        today = datetime.now().date()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT pair, type, pips, profit_usd 
            FROM trades 
            WHERE user_id = ? AND DATE(close_time) = ?
        """, (user_id, today))
        
        trades = c.fetchall()
        conn.close()
        
        if not trades:
            await query.edit_message_text("❌ Bugun hali tradelar yo'q!")
            return
        
        total = sum(t[3] for t in trades)
        text = f"📅 **BUGUN:**\n{'━' * 25}\n\n"
        text += f"📊 Jami: {len(trades)} tradelar\n"
        text += f"💰 Profit: **${total:+.2f}**"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'help':
        help_text = """
❓ **YORDAM**
{'━' * 25}

**Buyruqlar:**
/start - Boshlanish
/add - Yangi trade
/stats - Statistika
/list - Tradelar ro'yxati
/today - Bugungi tradelar

**Qanday foydalanish:**
1. /add ni bosing
2. Savollarga javob bering
3. Trade avtomatik saqlanadi!

📊 Statistika real-time yangilanadi!
"""
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'start':
        keyboard = [
            [
                InlineKeyboardButton("➕ Yangi Trade", callback_data='add_trade'),
                InlineKeyboardButton("📊 Statistika", callback_data='stats')
            ],
            [
                InlineKeyboardButton("📋 Tradelar", callback_data='list_trades'),
                InlineKeyboardButton("📅 Bugun", callback_data='today')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 **Forex Trading Journal**\n\n📊 Quyidagi tugmalardan birini tanlang:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )



# Main function
def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for adding trade
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_trade_start, pattern='^add_trade$')],
        states={
            PAIR: [CallbackQueryHandler(pair_selected, pattern='^pair_')],
            TYPE: [CallbackQueryHandler(type_selected, pattern='^type_')],
            ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, entry_received)],
            EXIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exit_received)],
            LOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, lot_received)],
            NOTES: [MessageHandler(filters.TEXT, notes_received)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel$')],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("list", list_trades_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
