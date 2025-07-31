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
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_sessions[user_id] = {"step": "photo"}
    await update.message.reply_text(
        "Привет! Отправьте:\n1. Фото\n2. Текст\n3. Ссылку\n4. Бюджет\n— и я создам пост и передам админу на модерацию."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message

    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "photo"}

    session = user_sessions[user_id]

    if session.get("editing"):  # Режим редактирования
        field = session["editing"]
        session[field] = message.text if field != "photo_file_id" else message.photo[-1].file_id
        session.pop("editing")
        await message.reply_text(f"✅ {field} обновлено.", reply_markup=preview_keyboard())
        return

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
        await message.reply_photo(
            photo=session["photo_file_id"],
            caption=generate_preview(session),
            parse_mode="HTML",
            reply_markup=preview_keyboard()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("edit:"):
        field = data.split(":")[1]
        user_sessions[user_id]["editing"] = field
        prompt = {
            "photo_file_id": "📷 Пришлите новое фото.",
            "text": "📝 Введите новый текст.",
            "link": "🔗 Введите новую ссылку.",
            "budget": "💰 Введите новый бюджет."
        }[field]
        await query.edit_message_caption(caption="✏️ Редактирование поля.", reply_markup=None)
        await context.bot.send_message(chat_id=user_id, text=prompt)
    elif data == "submit":
        session = user_sessions[user_id]
        post_preview = generate_preview(session)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")
            ]
        ])
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=session['photo_file_id'],
            caption=post_preview,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await context.bot.send_message(chat_id=user_id, text="✅ Заявка отправлена админу. Ожидайте решения.")
        user_sessions[user_id] = {}
    elif data == "cancel":
        user_sessions.pop(user_id, None)
        await query.edit_message_caption(caption="❌ Заявка отменена.", reply_markup=None)
    elif data.startswith("approve") or data.startswith("reject"):
        action, uid_str = data.split("|")
        uid = int(uid_str)
        message = query.message
        photo_file_id = message.photo[-1].file_id
        caption = message.caption

        if action == "approve":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo_file_id, caption=caption, parse_mode="HTML")
            await query.edit_message_caption(caption=caption + "\n\n✅ Одобрено и опубликовано.")
        else:
            await query.edit_message_caption(caption=caption + "\n\n❌ Отклонено.")


def generate_preview(session):
    return f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"

def preview_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Фото", callback_data="edit:photo_file_id"),
         InlineKeyboardButton("📝 Текст", callback_data="edit:text")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data="edit:link"),
         InlineKeyboardButton("💰 Бюджет", callback_data="edit:budget")],
        [InlineKeyboardButton("✅ Отправить", callback_data="submit"),
         InlineKeyboardButton("❌ Удалить", callback_data="cancel")]
    ])

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()







