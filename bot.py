import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
import os

TOKEN = "8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o"
CHANNEL_ID = "@tyumenmedia"
ADMIN_ID = 987540995

logging.basicConfig(level=logging.INFO)

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправьте:\n1. Фото\n2. Текст\n3. Ссылку\n4. Бюджет\n— и я создам пост и передам админу на модерацию."
    )
    user_sessions[update.message.from_user.id] = {"step": "photo"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message
    session = user_sessions.setdefault(user_id, {})

    if "editing" in session:
        field = session["editing"]
        if field == "photo" and message.photo:
            session[field] = message.photo[-1].file_id
        else:
            session[field] = message.text
        session.pop("editing")
        await send_preview(update, context, session)
        return

    step = session.get("step", "photo")

    if step == "photo":
        if message.photo:
            session["photo"] = message.photo[-1].file_id
            session["step"] = "text"
            await message.reply_text("📝 Теперь отправьте текст объявления.")
        else:
            await message.reply_text("Пожалуйста, отправьте фото.")
    elif step == "text":
        session["text"] = message.text
        session["step"] = "link"
        await message.reply_text("🔗 Теперь пришлите ссылку.")
    elif step == "link":
        session["link"] = message.text
        session["step"] = "budget"
        await message.reply_text("💰 Укажите бюджет.")
    elif step == "budget":
        session["budget"] = message.text
        await send_preview(update, context, session)

async def send_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить", callback_data=f"send|{user_id}"),
         InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_menu|{user_id}")],
        [InlineKeyboardButton("❌ Удалить", callback_data=f"delete|{user_id}")]
    ])
    caption = f"<b>📌 Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
    await context.bot.send_photo(chat_id=user_id, photo=session["photo"], caption=caption, parse_mode="HTML", reply_markup=keyboard)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_parts = query.data.split("|")
    action = data_parts[0]
    user_id = int(data_parts[1]) if len(data_parts) > 1 else query.from_user.id
    session = user_sessions.setdefault(user_id, {})

    if action == "send":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")]
        ])
        caption = f"<b>📌 Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=session["photo"], caption=caption, parse_mode="HTML", reply_markup=keyboard)
        await context.bot.send_message(chat_id=user_id, text="✅ Заявка отправлена админу.")
        user_sessions[user_id] = {}

    elif action == "delete":
        user_sessions[user_id] = {}
        await context.bot.send_message(chat_id=user_id, text="❌ Заявка удалена.")

    elif action == "edit_menu":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📷 Фото", callback_data="edit_field|photo")],
            [InlineKeyboardButton("📝 Текст", callback_data="edit_field|text")],
            [InlineKeyboardButton("🔗 Ссылка", callback_data="edit_field|link")],
            [InlineKeyboardButton("💰 Бюджет", callback_data="edit_field|budget")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"cancel_edit|{user_id}")]
        ])
        await context.bot.send_message(chat_id=user_id, text="Выберите, что хотите изменить:", reply_markup=keyboard)

    elif action == "edit_field":
        field = data_parts[1]
        session["editing"] = field
        prompts = {
            "photo": "📷 Отправьте новое фото.",
            "text": "📝 Отправьте новый текст.",
            "link": "🔗 Отправьте новую ссылку.",
            "budget": "💰 Укажите новый бюджет."
        }
        await context.bot.send_message(chat_id=user_id, text=prompts[field])

    elif action == "cancel_edit":
        await send_preview(update, context, session)

    elif action == "approve":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=update.effective_message.photo[-1].file_id,
                                     caption=update.effective_message.caption, parse_mode="HTML")
        await query.edit_message_caption(caption=update.effective_message.caption + "\n\n✅ Одобрено и опубликовано.")

    elif action == "reject":
        await query.edit_message_caption(caption=update.effective_message.caption + "\n\n❌ Отклонено.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()













