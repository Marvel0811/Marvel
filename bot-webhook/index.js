/**
 * Forex Trading Journal - Telegram Bot (Webhook)
 * Cloudflare Workers / Vercel Serverless
 */

const BOT_TOKEN = '8269807517:AAGmyZ4qkK2P3mVeDqeg8ItgpmMM9CimgMo';
const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// In-memory storage (use KV or D1 for production)
const trades = new Map();
const userStates = new Map();

// Telegram API helper
async function sendMessage(chatId, text, keyboard = null) {
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: 'Markdown'
  };
  
  if (keyboard) {
    body.reply_markup = keyboard;
  }
  
  const response = await fetch(`${TELEGRAM_API}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  return response.json();
}

async function editMessage(chatId, messageId, text, keyboard = null) {
  const body = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: 'Markdown'
  };
  
  if (keyboard) {
    body.reply_markup = keyboard;
  }
  
  const response = await fetch(`${TELEGRAM_API}/editMessageText`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  return response.json();
}

// Calculate pips and profit
function calculatePips(entry, exit, type, pair) {
  const multiplier = pair.includes('JPY') ? 100 : 10000;
  const pips = type === 'BUY' 
    ? (exit - entry) * multiplier 
    : (entry - exit) * multiplier;
  return Math.round(pips * 10) / 10;
}

function calculateProfit(pips, lotSize, pair) {
  const pipValue = pair.includes('JPY') ? 1000 : 10;
  const profit = (pips / 10) * pipValue * lotSize;
  return Math.round(profit * 100) / 100;
}

// Get user statistics
function getUserStats(userId) {
  const userTrades = trades.get(userId) || [];
  
  if (userTrades.length === 0) {
    return null;
  }
  
  const wins = userTrades.filter(t => t.profitUSD > 0);
  const losses = userTrades.filter(t => t.profitUSD < 0);
  
  const totalProfit = wins.reduce((sum, t) => sum + t.profitUSD, 0);
  const totalLoss = Math.abs(losses.reduce((sum, t) => sum + t.profitUSD, 0));
  const netProfit = totalProfit - totalLoss;
  
  const bestTrade = Math.max(...userTrades.map(t => t.profitUSD), 0);
  const worstTrade = Math.min(...userTrades.map(t => t.profitUSD), 0);
  
  const winRate = (wins.length / userTrades.length * 100).toFixed(1);
  const profitFactor = totalLoss > 0 ? (totalProfit / totalLoss).toFixed(2) : totalProfit.toFixed(2);
  
  return {
    total: userTrades.length,
    wins: wins.length,
    losses: losses.length,
    winRate,
    totalProfit: totalProfit.toFixed(2),
    totalLoss: totalLoss.toFixed(2),
    netProfit: netProfit.toFixed(2),
    profitFactor,
    bestTrade: bestTrade.toFixed(2),
    worstTrade: worstTrade.toFixed(2)
  };
}

// Main keyboard
function getMainKeyboard() {
  return {
    inline_keyboard: [
      [
        { text: '➕ Yangi Trade', callback_data: 'add_trade' },
        { text: '📊 Statistika', callback_data: 'stats' }
      ],
      [
        { text: '📋 Tradelar', callback_data: 'list' },
        { text: '📅 Bugun', callback_data: 'today' }
      ]
    ]
  };
}

// Handle /start command
async function handleStart(chatId, userName) {
  const text = `👋 Assalomu alaykum, ${userName}!

🤖 **Forex Trading Journal** botiga xush kelibsiz!

Bu bot orqali:
✅ Tradelaringizni oson qo'shishingiz
✅ Statistikani real-time ko'rishingiz
✅ Tahlil qilishingiz mumkin

📊 Quyidagi tugmalardan birini tanlang:`;

  return sendMessage(chatId, text, getMainKeyboard());
}

// Handle statistics
async function handleStats(chatId, messageId) {
  const stats = getUserStats(chatId);
  
  if (!stats) {
    const text = '❌ Hali tradelar yo\'q!\n\nBirinchi tradeni qo\'shing 👇';
    const keyboard = {
      inline_keyboard: [
        [{ text: '➕ Birinchi Trade', callback_data: 'add_trade' }]
      ]
    };
    return editMessage(chatId, messageId, text, keyboard);
  }
  
  const text = `📊 **STATISTIKA**
${'━'.repeat(25)}

📈 Jami tradelar: **${stats.total}**
✅ Yutish: **${stats.wins}** (${stats.winRate}%)
❌ Zarar: **${stats.losses}**

💰 **FOYDA/ZARAR:**
Jami Foyda: **$${stats.totalProfit}**
Jami Zarar: **$${stats.totalLoss}**
Net Profit: **$${stats.netProfit}**

📊 Profit Factor: **${stats.profitFactor}**

🏆 **ENG YAXSHI/YOMON:**
Eng Yaxshi: **$${stats.bestTrade}**
Eng Yomon: **$${stats.worstTrade}**`;

  const keyboard = {
    inline_keyboard: [
      [{ text: '◀️ Orqaga', callback_data: 'back' }],
      [{ text: '➕ Yangi Trade', callback_data: 'add_trade' }]
    ]
  };
  
  return editMessage(chatId, messageId, text, keyboard);
}

// Handle list trades
async function handleList(chatId, messageId) {
  const userTrades = trades.get(chatId) || [];
  
  if (userTrades.length === 0) {
    return editMessage(chatId, messageId, '❌ Hali tradelar yo\'q!');
  }
  
  const recent = userTrades.slice(-5).reverse();
  
  let text = '📋 **OXIRGI TRADELAR:**\n' + '━'.repeat(25) + '\n\n';
  
  recent.forEach(trade => {
    const emoji = trade.profitUSD >= 0 ? '✅' : '❌';
    const date = new Date(trade.date).toLocaleDateString('uz-UZ');
    
    text += `${date} | **${trade.pair}** ${trade.type}\n`;
    text += `${emoji} ${trade.pips > 0 ? '+' : ''}${trade.pips} pips (${trade.profitUSD > 0 ? '+' : ''}$${trade.profitUSD})\n\n`;
  });
  
  const keyboard = {
    inline_keyboard: [
      [{ text: '◀️ Orqaga', callback_data: 'back' }]
    ]
  };
  
  return editMessage(chatId, messageId, text, keyboard);
}

// Handle today's trades
async function handleToday(chatId, messageId) {
  const userTrades = trades.get(chatId) || [];
  const today = new Date().toDateString();
  
  const todayTrades = userTrades.filter(t => new Date(t.date).toDateString() === today);
  
  if (todayTrades.length === 0) {
    return editMessage(chatId, messageId, '❌ Bugun hali tradelar yo\'q!');
  }
  
  const totalProfit = todayTrades.reduce((sum, t) => sum + t.profitUSD, 0);
  
  let text = `📅 **BUGUNGI TRADELAR:**\n${'━'.repeat(25)}\n\n`;
  text += `📊 Jami: ${todayTrades.length} tradelar\n`;
  text += `💰 Profit: **$${totalProfit > 0 ? '+' : ''}${totalProfit.toFixed(2)}**`;
  
  const keyboard = {
    inline_keyboard: [
      [{ text: '◀️ Orqaga', callback_data: 'back' }]
    ]
  };
  
  return editMessage(chatId, messageId, text, keyboard);
}

// Start adding trade - select pair
async function handleAddTrade(chatId, messageId) {
  const pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 'NZD/USD', 'USD/CAD'];
  
  const keyboard = {
    inline_keyboard: pairs.map(pair => [
      { text: pair, callback_data: `pair_${pair}` }
    ]).concat([[{ text: '❌ Bekor qilish', callback_data: 'back' }]])
  };
  
  const text = '📊 **YANGI TRADE QO\'SHISH**\n\n1️⃣ Valyuta juftini tanlang:';
  
  return editMessage(chatId, messageId, text, keyboard);
}

// Handle pair selection
async function handlePairSelect(chatId, messageId, pair) {
  userStates.set(chatId, { pair, step: 'type' });
  
  const keyboard = {
    inline_keyboard: [
      [{ text: '📈 BUY', callback_data: 'type_BUY' }],
      [{ text: '📉 SELL', callback_data: 'type_SELL' }],
      [{ text: '◀️ Orqaga', callback_data: 'add_trade' }]
    ]
  };
  
  const text = `📊 **YANGI TRADE**\n\nValyuta: **${pair}**\n\n2️⃣ Buy yoki Sell?`;
  
  return editMessage(chatId, messageId, text, keyboard);
}

// Handle type selection
async function handleTypeSelect(chatId, messageId, type) {
  const state = userStates.get(chatId);
  state.type = type;
  state.step = 'entry';
  userStates.set(chatId, state);
  
  const text = `📊 **YANGI TRADE**\n\nValyuta: **${state.pair}**\nTuri: **${type}**\n\n3️⃣ Entry narxni yuboring:\n\n_Masalan: 1.0850_`;
  
  return editMessage(chatId, messageId, text);
}

// Handle text message (entry, exit, lot)
async function handleTextMessage(chatId, text) {
  const state = userStates.get(chatId);
  
  if (!state) {
    return sendMessage(chatId, 'Iltimos /start dan boshlang!');
  }
  
  const value = parseFloat(text.trim());
  
  if (isNaN(value)) {
    return sendMessage(chatId, '❌ Noto\'g\'ri format! Raqam kiriting.');
  }
  
  if (state.step === 'entry') {
    state.entry = value;
    state.step = 'exit';
    userStates.set(chatId, state);
    
    return sendMessage(chatId, `4️⃣ Exit narxni yuboring:\n\n_Masalan: 1.0890_`, null);
  }
  
  if (state.step === 'exit') {
    state.exit = value;
    state.step = 'lot';
    userStates.set(chatId, state);
    
    return sendMessage(chatId, `5️⃣ Lot hajmini yuboring:\n\n_Masalan: 0.1_`, null);
  }
  
  if (state.step === 'lot') {
    state.lot = value;
    
    // Calculate and save trade
    const pips = calculatePips(state.entry, state.exit, state.type, state.pair);
    const profitUSD = calculateProfit(pips, state.lot, state.pair);
    
    const trade = {
      pair: state.pair,
      type: state.type,
      entry: state.entry,
      exit: state.exit,
      lot: state.lot,
      pips,
      profitUSD,
      date: new Date().toISOString()
    };
    
    // Save trade
    const userTrades = trades.get(chatId) || [];
    userTrades.push(trade);
    trades.set(chatId, userTrades);
    
    // Get updated stats
    const stats = getUserStats(chatId);
    
    const emoji = profitUSD >= 0 ? '✅' : '❌';
    
    const resultText = `${emoji} **TRADE SAQLANDI!**
${'━'.repeat(25)}

📊 **${state.pair}** ${state.type}
↗️ ${state.entry} → ${state.exit}
${emoji} **${pips > 0 ? '+' : ''}${pips} pips | ${profitUSD > 0 ? '+' : ''}$${profitUSD}**

📈 **YANGI STATISTIKA:**
Jami: ${stats.total} | Win Rate: ${stats.winRate}%
Net Profit: $${stats.netProfit}`;

    const keyboard = {
      inline_keyboard: [
        [
          { text: '➕ Yana qo\'shish', callback_data: 'add_trade' },
          { text: '📊 Statistika', callback_data: 'stats' }
        ]
      ]
    };
    
    userStates.delete(chatId);
    
    return sendMessage(chatId, resultText, keyboard);
  }
}

// Main webhook handler
export default {
  async fetch(request, env, ctx) {
    if (request.method === 'POST') {
      const update = await request.json();
      
      // Handle callback query (button press)
      if (update.callback_query) {
        const query = update.callback_query;
        const chatId = query.message.chat.id;
        const messageId = query.message.message_id;
        const data = query.data;
        
        // Answer callback query
        await fetch(`${TELEGRAM_API}/answerCallbackQuery`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ callback_query_id: query.id })
        });
        
        if (data === 'back') {
          return handleStart(chatId, query.from.first_name);
        }
        
        if (data === 'stats') {
          return handleStats(chatId, messageId);
        }
        
        if (data === 'list') {
          return handleList(chatId, messageId);
        }
        
        if (data === 'today') {
          return handleToday(chatId, messageId);
        }
        
        if (data === 'add_trade') {
          return handleAddTrade(chatId, messageId);
        }
        
        if (data.startsWith('pair_')) {
          const pair = data.replace('pair_', '');
          return handlePairSelect(chatId, messageId, pair);
        }
        
        if (data.startsWith('type_')) {
          const type = data.replace('type_', '');
          return handleTypeSelect(chatId, messageId, type);
        }
      }
      
      // Handle text message
      if (update.message) {
        const message = update.message;
        const chatId = message.chat.id;
        const text = message.text;
        
        if (text === '/start') {
          return handleStart(chatId, message.from.first_name);
        }
        
        if (text === '/stats') {
          const stats = getUserStats(chatId);
          if (!stats) {
            return sendMessage(chatId, '❌ Hali tradelar yo\'q!');
          }
          // Send stats as message (not edit)
          const statsText = `📊 **STATISTIKA**\n\nJami: ${stats.total}\nWin Rate: ${stats.winRate}%\nNet Profit: $${stats.netProfit}`;
          return sendMessage(chatId, statsText, getMainKeyboard());
        }
        
        // Handle numeric input (entry/exit/lot)
        return handleTextMessage(chatId, text);
      }
      
      return new Response('OK', { status: 200 });
    }
    
    return new Response('Forex Trading Journal Bot', { status: 200 });
  }
};
