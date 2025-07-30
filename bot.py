import logging
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
import os
import json

TOKEN = "8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o"
CHANNEL_ID = "@tyumenmedia"
ADMIN_ID = 987540995

logging.basicConfig(level=logging.INFO)

ADS_FILE = "ads.json"

if not os.path.exists(ADS_FILE):
    with open(ADS_FILE, "w") as f:
        json.dump([], f)

ads_cache = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправьте:\n1. Фото\n2. Текст\n3. Ссылку\n4. Бюджет\n— и я создам пост и передам админу на модерацию."
    )

user_sessions = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message

    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "photo"}

    session = user_sessions[user_id]

    if session["step"] == "photo":
        if message.photo:
            session["photo_file_id"] = message.photo[-1].file_id
            session["step"] = "text"
            await message.reply_text("📝 Теперь отправьте текст объявления.")
        else:
            await message.reply_text("Пожалуйста, пришлите изображение.")
    elif session["step"] == "text":
        session["text"] = message.text
        session["step"] = "link"
        await message.reply_text("🔗 Теперь пришлите ссылку.")
    elif session["step"] == "link":
        session["link"] = message.text
        session["step"] = "budget"
        await message.reply_text("💰 И наконец — бюджет.")
    elif session["step"] == "budget":
        session["budget"] = message.text

        post_preview = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")]
        ])

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=session['photo_file_id'],
            caption=post_preview,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await message.reply_text("✅ Заявка отправлена админу. Ожидайте решения.")
        user_sessions[user_id] = {}

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id_str = query.data.split("|")
    user_id = int(user_id_str)

    message = query.message
    photo_file_id = message.photo[-1].file_id
    caption = message.caption

    if action == "approve":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption, parse_mode="HTML")
        await query.edit_message_caption(caption=caption + "\n\n✅ Одобрено и опубликовано.")
    elif action == "reject":
        await query.edit_message_caption(caption=caption + "\n\n❌ Отклонено.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()







