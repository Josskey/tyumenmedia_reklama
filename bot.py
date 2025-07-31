import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
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
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Подать заявку на рекламу", callback_data="begin_form")]
    ])
    await update.message.reply_text(
        "Добро пожаловать в официальный бот медиаплатформы ТюМедиа.\n"
        "Здесь вы можете оставить заявку на размещение рекламного объявления.\n\n"
        "ℹ️ Чтобы начать оформление, нажмите кнопку ниже.",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message

    if user_id not in user_sessions:
        user_sessions[user_id] = {"step": "photo"}

    session = user_sessions[user_id]

    if session.get("step") == "waiting_admin":
        await update.message.reply_text("⏳ Ваша заявка уже отправлена админу. Пожалуйста, дождитесь решения.")
        return

    if session.get("editing"):
        field = session.get("edit_field")
        if field == "photo" and message.photo:
            session["photo_file_id"] = message.photo[-1].file_id
        elif field in ["text", "link", "budget"]:
            session[field] = message.text
        session["editing"] = False
        session["edit_field"] = None
        await message.reply_text("✅ Изменения сохранены. Проверьте ещё раз заявку.", reply_markup=preview_keyboard())
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
        session["step"] = "preview"
        await send_preview(update, context, user_id)

async def send_preview(update, context, user_id):
    session = user_sessions[user_id]
    preview_text = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
    keyboard = preview_keyboard()
    await update.message.reply_photo(photo=session["photo_file_id"], caption=preview_text, parse_mode="HTML", reply_markup=keyboard)

def preview_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 Отправить", callback_data="send"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit"),
            InlineKeyboardButton("❌ Удалить", callback_data="cancel")
        ]
    ])

def edit_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📷 Фото", callback_data="edit_photo"),
            InlineKeyboardButton("📝 Текст", callback_data="edit_text")
        ],
        [
            InlineKeyboardButton("🔗 Ссылка", callback_data="edit_link"),
            InlineKeyboardButton("💰 Бюджет", callback_data="edit_budget")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "begin_form":
        user_sessions[user_id] = {"step": "photo"}
        await context.bot.send_message(chat_id=user_id, text="📷 Пожалуйста, отправьте изображение для рекламы.")
    elif data == "send":
        session = user_sessions.get(user_id, {})
        if all(k in session for k in ["photo_file_id", "text", "link", "budget"]):
            caption = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")
                ]
            ])
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=session["photo_file_id"], caption=caption, parse_mode="HTML", reply_markup=keyboard)
            await query.edit_message_caption(caption=caption + "\n\n⏳ Отправлено админу.")
            await context.bot.send_message(chat_id=user_id, text="✅ Заявка отправлена админу. Ожидайте решения.")
            user_sessions[user_id]["step"] = "waiting_admin"
    elif data == "cancel":
        user_sessions[user_id] = {}
        await query.edit_message_caption(caption="❌ Заявка отменена.")
    elif data == "edit":
        await query.edit_message_reply_markup(reply_markup=edit_keyboard())
    elif data.startswith("edit_"):
        field = data.split("_")[1]
        user_sessions[user_id]["editing"] = True
        user_sessions[user_id]["edit_field"] = field
        await context.bot.send_message(chat_id=user_id, text=f"✏️ Пришлите новое значение для поля: {field.upper()}")
    elif data == "back":
        await query.edit_message_reply_markup(reply_markup=preview_keyboard())
    elif "|" in data:
        action, target_id_str = data.split("|")
        target_id = int(target_id_str)
        msg = query.message
        photo = msg.photo[-1].file_id
        caption = msg.caption
        if action == "approve":
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption, parse_mode="HTML")
            await query.edit_message_caption(caption=caption + "\n\n✅ Одобрено и опубликовано.")
            await context.bot.send_message(chat_id=target_id, text="✅ Ваша заявка одобрена и опубликована.")
            user_sessions[target_id] = {}
        elif action == "reject":
            await query.edit_message_caption(caption=caption + "\n\n❌ Отклонено.")
            await context.bot.send_message(chat_id=target_id, text="❌ Ваша заявка отклонена.")
            user_sessions[target_id] = {}

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()












