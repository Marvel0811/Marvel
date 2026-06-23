# Forex Trading Journal - Telegram Bot (Webhook)

## 🚀 Deploy qilish

### Cloudflare Workers

1. **Cloudflare account ochish:** https://dash.cloudflare.com/sign-up
2. **Wrangler CLI o'rnatish:**
   ```bash
   npm install -g wrangler
   ```
3. **Login qilish:**
   ```bash
   wrangler login
   ```
4. **Deploy qilish:**
   ```bash
   wrangler deploy
   ```
5. **Webhook o'rnatish:**
   ```bash
   curl -X POST https://api.telegram.org/bot8269807517:AAGmyZ4qkK2P3mVeDqeg8ItgpmMM9CimgMo/setWebhook \
     -d url=https://forex-bot-webhook.YOURNAME.workers.dev
   ```

### Vercel

1. **Vercel account:** https://vercel.com/signup
2. **Vercel CLI:**
   ```bash
   npm install -g vercel
   ```
3. **Deploy:**
   ```bash
   vercel
   ```

## 📊 Xususiyatlar

✅ Serverless (bepul)
✅ Webhook (tezkor)
✅ In-memory storage (yoki KV)
✅ Inline tugmalar
✅ Real-time statistika

## 🤖 Bot buyruqlari

- `/start` - Boshlash
- `/stats` - Statistika
- Tugmalar orqali: Trade qo'shish, Ro'yxat, Bugun

## 🔧 Sozlash

`wrangler.toml` faylida `BOT_TOKEN` ni o'zgartiring.

## 📝 Ma'lumotlar

Hozirda **in-memory** (xotira)da saqlanadi.
Production uchun **Cloudflare KV** yoki **D1** ishlatish tavsiya etiladi.
