import json
import os
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ========= НАСТРОЙКИ =========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLASH_API_TOKEN = os.getenv("CLASH_API_TOKEN")
CLAN_TAG = "GQUJGVG0"  # без #
MAX_DECKS = 4
LINKS_FILE = "links.json"
# =============================

HEADERS = {
    "Authorization": f"Bearer {CLASH_API_TOKEN}"
}

# ---------- utils ----------
def reply(update: Update, text: str, **kwargs):
    if update.message:
        return update.message.reply_text(text, **kwargs)
    if update.callback_query:
        return update.callback_query.message.reply_text(text, **kwargs)

# ---------- files ----------
def load_links():
    if not os.path.exists(LINKS_FILE):
        return {}
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_links(data):
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- Clash API ----------
def get_current_war():
    url = f"https://api.clashroyale.com/v1/clans/%23{CLAN_TAG}/currentriverrace"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

# ---------- keyboard ----------
def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏹 War", callback_data="war"),
            InlineKeyboardButton("🔗 Link", callback_data="link_help"),
        ],
        [
            InlineKeyboardButton("❌ Unlink", callback_data="unlink"),
        ],
    ])

# ---------- /ping ----------
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "🤖 Бот работает ✅", reply_markup=main_keyboard())

# ---------- /link ----------
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await reply(
            update,
            "Использование:\n/link НикВИгре\n\nПример:\n/link Ivan",
            reply_markup=main_keyboard()
        )
        return

    cr_name = " ".join(context.args)
    tg_user = update.effective_user.username

    if not tg_user:
        await reply(update, "❌ У тебя нет @username")
        return

    links = load_links()
    links[cr_name] = f"@{tg_user}"
    save_links(links)

    await reply(
        update,
        f"✅ Привязано:\n{cr_name} → @{tg_user}",
        reply_markup=main_keyboard()
    )

# ---------- /unlink ----------
async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg = f"@{update.effective_user.username}"
    links = load_links()

    removed = None
    for k, v in list(links.items()):
        if v == tg:
            removed = k
            del links[k]

    save_links(links)

    if removed:
        await reply(update, f"❌ Отвязано: {removed}", reply_markup=main_keyboard())
    else:
        await reply(update, "ℹ️ Ты не был привязан", reply_markup=main_keyboard())

# ---------- /war ----------
async def war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = get_current_war()
        clan = data["clan"]
        participants = clan["participants"]
        links = load_links()

        full, partial, missed = [], [], []
        total_left = 0

        for p in participants:
            used = p["decksUsedToday"]
            total_left += MAX_DECKS - used
            name = links.get(p["name"], p["name"])

            if used == 4:
                full.append(name)
            elif used > 0:
                partial.append(f"{name} ({used})")
            else:
                missed.append(name)

        text = (
            "🏹 <b>CLAN WAR — River Race</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🏰 <b>{clan['name']}</b>\n\n"
            f"🃏 <b>Осталось колод:</b> {total_left}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        if full:
            text += "🔥 <b>Полностью отбили:</b>\n" + ", ".join(full) + "\n\n"
        if partial:
            text += "⚔️ <b>Частично:</b>\n" + ", ".join(partial) + "\n\n"
        if missed:
            text += "❌ <b>Не отбили:</b>\n" + ", ".join(missed)

        await reply(
            update,
            text,
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )

    except requests.exceptions.HTTPError as e:
        await reply(update, "❌ API отказал в доступе (403)\nПроверь IP и API-ключ")
        print(e)

# ---------- buttons ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "war":
        await war(update, context)
    elif q.data == "link_help":
        await reply(update, "🔗 /link НикВИгре")
    elif q.data == "unlink":
        await unlink(update, context)

# ---------- start ----------
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CommandHandler("unlink", unlink))
    app.add_handler(CommandHandler("war", war))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
