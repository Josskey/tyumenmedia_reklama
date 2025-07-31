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

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправьте:\n1. Фото\n2. Текст\n3. Ссылку\n4. Бюджет\n— и я создам пост и передам админу на модерацию."
    )

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
        await show_preview(update, context, session)

    elif session["step"] == "edit_photo":
        if message.photo:
            session["photo_file_id"] = message.photo[-1].file_id
            await message.reply_text("✅ Фото обновлено.")
            await show_preview(update, context, session)
        else:
            await message.reply_text("Пожалуйста, отправьте новое изображение.")

    elif session["step"] == "edit_text":
        session["text"] = message.text
        await message.reply_text("✅ Текст обновлён.")
        await show_preview(update, context, session)

    elif session["step"] == "edit_link":
        session["link"] = message.text
        await message.reply_text("✅ Ссылка обновлена.")
        await show_preview(update, context, session)

    elif session["step"] == "edit_budget":
        session["budget"] = message.text
        await message.reply_text("✅ Бюджет обновлён.")
        await show_preview(update, context, session)

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, session):
    post_preview = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Отправить", callback_data=f"submit|{update.message.from_user.id}"),
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit|{update.message.from_user.id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete|{update.message.from_user.id}")
        ]
    ])
    await update.message.reply_photo(photo=session['photo_file_id'], caption=post_preview, parse_mode="HTML", reply_markup=keyboard)
    session["step"] = "preview"

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]
    user_id = int(data[1])
    session = user_sessions.get(user_id, {})

    if action == "submit":
        post_preview = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")
            ]
        ])
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=session['photo_file_id'], caption=post_preview, parse_mode="HTML", reply_markup=keyboard)
        await query.edit_message_caption(caption="✅ Заявка отправлена админу. Ожидайте решения.")

    elif action == "edit":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📷 Фото", callback_data=f"edit_photo|{user_id}")],
            [InlineKeyboardButton("📝 Текст", callback_data=f"edit_text|{user_id}")],
            [InlineKeyboardButton("🔗 Ссылка", callback_data=f"edit_link|{user_id}")],
            [InlineKeyboardButton("💰 Бюджет", callback_data=f"edit_budget|{user_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"back|{user_id}")]
        ])
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif action.startswith("edit_"):
        field = action.split("_")[1]
        session["step"] = f"edit_{field}"
        await context.bot.send_message(chat_id=user_id, text=f"Введите новое значение для поля: {field}")

    elif action == "back":
        await show_preview(update, context, session)

    elif action == "delete":
        user_sessions[user_id] = {}
        await query.edit_message_caption(caption="❌ Заявка удалена.")

    elif action == "approve":
        message = query.message
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=message.caption, parse_mode="HTML")
        await query.edit_message_caption(caption=message.caption + "\n\n✅ Одобрено и опубликовано.")

    elif action == "reject":
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ Отклонено.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()













