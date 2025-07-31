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
        "Привет! Отправьте:",
    )
    await show_ad_form(update, context)

async def show_ad_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📷 Фото", callback_data="edit|photo")],
        [InlineKeyboardButton("📝 Текст", callback_data="edit|text")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data="edit|link")],
        [InlineKeyboardButton("💰 Бюджет", callback_data="edit|budget")],
        [
            InlineKeyboardButton("✅ Отправить", callback_data="submit"),
            InlineKeyboardButton("❌ Удалить", callback_data="delete")
        ]
    ]
    await update.message.reply_text("Что вы хотите сделать?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message

    session = user_sessions.setdefault(user_id, {})
    step = session.get("step")

    if step == "photo" and message.photo:
        session["photo_file_id"] = message.photo[-1].file_id
        await message.reply_text("Фото обновлено ✅")
    elif step == "text" and message.text:
        session["text"] = message.text
        await message.reply_text("Текст обновлён ✅")
    elif step == "link" and message.text:
        session["link"] = message.text
        await message.reply_text("Ссылка обновлена ✅")
    elif step == "budget" and message.text:
        session["budget"] = message.text
        await message.reply_text("Бюджет обновлён ✅")
    else:
        await message.reply_text("Пожалуйста, выберите, что хотите отредактировать.")

    session["step"] = None
    await show_ad_form(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    data = query.data
    session = user_sessions.setdefault(user_id, {})

    if data.startswith("edit"):
        _, field = data.split("|")
        session["step"] = field
        await query.message.reply_text(f"✍️ Пришлите новое значение для поля: {field.upper()}.")

    elif data == "submit":
        if not all(session.get(k) for k in ("photo_file_id", "text", "link")):
            await query.message.reply_text("Необходимо заполнить как минимум фото, текст и ссылку.")
            return

        post_preview = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session.get('budget', 'не указан')}"
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

        await query.message.reply_text("Заявка отправлена админу ✅")
        session.clear()

    elif data == "delete":
        session.clear()
        await query.message.reply_text("Заявка удалена 🗑")

    elif data.startswith("approve") or data.startswith("reject"):
        action, uid = data.split("|")
        uid = int(uid)
        target_session = user_sessions.get(uid, {})
        caption = query.message.caption
        photo = query.message.photo[-1].file_id if query.message.photo else None

        if action == "approve" and photo:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption, parse_mode="HTML")
            await query.edit_message_caption(caption=caption + "\n\n✅ Одобрено и опубликовано.")
        elif action == "reject":
            await query.edit_message_caption(caption=caption + "\n\n❌ Отклонено.")

        user_sessions.pop(uid, None)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()


if __name__ == "__main__":
    main()






