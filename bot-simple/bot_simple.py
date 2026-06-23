#!/usr/bin/env python3
"""
ODDIY TELEGRAM BOT - Forex Journal
Webhook kerak emas, polling ishlatadi
"""

import requests
import json
import time
from datetime import datetime

BOT_TOKEN = "8269807517:AAGmyZ4qkK2P3mVeDqeg8ItgpmMM9CimgMo"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory storage
trades = {}
user_states = {}

def send_message(chat_id, text, keyboard=None):
    """Send message to user"""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    
    response = requests.post(f"{API_URL}/sendMessage", json=data)
    return response.json()

def get_updates(offset=None):
    """Get updates from Telegram"""
    params = {"timeout": 30, "offset": offset}
    response = requests.get(f"{API_URL}/getUpdates", params=params)
    return response.json()

def calculate_pips(entry, exit_price, trade_type, pair):
    """Calculate pips"""
    multiplier = 100 if 'JPY' in pair else 10000
    if trade_type == 'BUY':
        pips = (exit_price - entry) * multiplier
    else:
        pips = (entry - exit_price) * multiplier
    return round(pips, 1)

def calculate_profit(pips, lot_size, pair):
    """Calculate profit in USD"""
    pip_value = 1000 if 'JPY' in pair else 10
    profit = (pips / 10) * pip_value * lot_size
    return round(profit, 2)

def get_stats(user_id):
    """Get user statistics"""
    user_trades = trades.get(user_id, [])
    if not user_trades:
        return None
    
    wins = [t for t in user_trades if t['profit'] > 0]
    losses = [t for t in user_trades if t['profit'] < 0]
    
    total_profit = sum(t['profit'] for t in wins)
    total_loss = abs(sum(t['profit'] for t in losses))
    net = total_profit - total_loss
    
    return {
        'total': len(user_trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(len(wins) / len(user_trades) * 100, 1),
        'net_profit': round(net, 2),
        'total_profit': round(total_profit, 2),
        'total_loss': round(total_loss, 2)
    }

def main_keyboard():
    """Main menu keyboard"""
    return {
        "inline_keyboard": [
            [
                {"text": "➕ Yangi Trade", "callback_data": "add"},
                {"text": "📊 Statistika", "callback_data": "stats"}
            ],
            [
                {"text": "📋 Tradelar", "callback_data": "list"}
            ]
        ]
    }

def handle_start(chat_id, name):
    """Handle /start command"""
    text = f"👋 Assalomu alaykum, {name}!\n\n"
    text += "🤖 **Forex Trading Journal** botiga xush kelibsiz!\n\n"
    text += "📊 Tugmalardan birini tanlang:"
    send_message(chat_id, text, main_keyboard())

def handle_stats(chat_id):
    """Handle statistics"""
    stats = get_stats(chat_id)
    if not stats:
        send_message(chat_id, "❌ Hali tradelar yo'q!", main_keyboard())
        return
    
    text = f"📊 **STATISTIKA**\n"
    text += f"{'━' * 25}\n\n"
    text += f"📈 Jami: **{stats['total']}**\n"
    text += f"✅ Yutish: **{stats['wins']}** ({stats['win_rate']}%)\n"
    text += f"❌ Zarar: **{stats['losses']}**\n\n"
    text += f"💰 Net Profit: **${stats['net_profit']}**\n"
    text += f"📊 Total Profit: **${stats['total_profit']}**\n"
    text += f"📉 Total Loss: **${stats['total_loss']}**"
    
    send_message(chat_id, text, main_keyboard())

def handle_list(chat_id):
    """Handle list trades"""
    user_trades = trades.get(chat_id, [])
    if not user_trades:
        send_message(chat_id, "❌ Hali tradelar yo'q!", main_keyboard())
        return
    
    recent = user_trades[-5:][::-1]
    
    text = "📋 **OXIRGI TRADELAR:**\n" + "━" * 25 + "\n\n"
    for t in recent:
        emoji = "✅" if t['profit'] > 0 else "❌"
        text += f"{emoji} **{t['pair']}** {t['type']}\n"
        text += f"{t['pips']:+.1f} pips | ${t['profit']:+.2f}\n\n"
    
    send_message(chat_id, text, main_keyboard())

def handle_add_start(chat_id):
    """Start adding trade"""
    pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF']
    keyboard = {
        "inline_keyboard": [[{"text": p, "callback_data": f"pair_{p}"}] for p in pairs]
    }
    send_message(chat_id, "1️⃣ Valyuta juftini tanlang:", keyboard)

def handle_text(chat_id, text):
    """Handle text messages"""
    state = user_states.get(chat_id, {})
    
    if not state:
        send_message(chat_id, "Iltimos /start dan boshlang!")
        return
    
    try:
        value = float(text.strip())
    except:
        send_message(chat_id, "❌ Raqam kiriting!")
        return
    
    if state.get('step') == 'entry':
        state['entry'] = value
        state['step'] = 'exit'
        user_states[chat_id] = state
        send_message(chat_id, "4️⃣ Exit narxni yuboring:")
    
    elif state.get('step') == 'exit':
        state['exit'] = value
        state['step'] = 'lot'
        user_states[chat_id] = state
        send_message(chat_id, "5️⃣ Lot hajmini yuboring:")
    
    elif state.get('step') == 'lot':
        # Save trade
        pips = calculate_pips(state['entry'], value, state['type'], state['pair'])
        profit = calculate_profit(pips, value, state['pair'])
        
        trade = {
            'pair': state['pair'],
            'type': state['type'],
            'entry': state['entry'],
            'exit': state['exit'],
            'lot': value,
            'pips': pips,
            'profit': profit,
            'date': datetime.now().isoformat()
        }
        
        if chat_id not in trades:
            trades[chat_id] = []
        trades[chat_id].append(trade)
        
        emoji = "✅" if profit > 0 else "❌"
        text = f"{emoji} **TRADE SAQLANDI!**\n\n"
        text += f"📊 {state['pair']} {state['type']}\n"
        text += f"{emoji} {pips:+.1f} pips | ${profit:+.2f}"
        
        user_states.pop(chat_id, None)
        send_message(chat_id, text, main_keyboard())

def main():
    """Main bot loop"""
    print("🤖 Bot ishga tushdi!")
    offset = None
    
    while True:
        try:
            updates = get_updates(offset)
            
            if not updates.get('ok'):
                print("❌ Xato:", updates)
                time.sleep(5)
                continue
            
            for update in updates.get('result', []):
                offset = update['update_id'] + 1
                
                # Handle callback query (button)
                if 'callback_query' in update:
                    query = update['callback_query']
                    chat_id = query['message']['chat']['id']
                    data = query['data']
                    
                    if data == 'stats':
                        handle_stats(chat_id)
                    elif data == 'list':
                        handle_list(chat_id)
                    elif data == 'add':
                        handle_add_start(chat_id)
                    elif data.startswith('pair_'):
                        pair = data.replace('pair_', '')
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "📈 BUY", "callback_data": "type_BUY"}],
                                [{"text": "📉 SELL", "callback_data": "type_SELL"}]
                            ]
                        }
                        user_states[chat_id] = {'pair': pair, 'step': 'type'}
                        send_message(chat_id, f"2️⃣ Buy yoki Sell?\n\nValyuta: **{pair}**", keyboard)
                    elif data.startswith('type_'):
                        trade_type = data.replace('type_', '')
                        state = user_states.get(chat_id, {})
                        state['type'] = trade_type
                        state['step'] = 'entry'
                        user_states[chat_id] = state
                        send_message(chat_id, "3️⃣ Entry narxni yuboring:\n\n_Masalan: 1.0850_")
                
                # Handle message
                elif 'message' in update:
                    message = update['message']
                    chat_id = message['chat']['id']
                    
                    if 'text' in message:
                        text = message['text']
                        
                        if text == '/start':
                            handle_start(chat_id, message['from']['first_name'])
                        elif text == '/stats':
                            handle_stats(chat_id)
                        else:
                            handle_text(chat_id, text)
        
        except Exception as e:
            print(f"❌ Xato: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
