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
rejection_reasons = {
    "reason1": "❌ Несоответствие контента",
    "reason2": "❌ Недостаточный бюджет",
    "reason3": "❌ Не подходит по тематике",
    "reason4": "❌ Нарушение законодательства"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Заполнить рекламную заявку", callback_data="begin_form")]
    ])
    await update.message.reply_text(
        "Это официальный Telegram-бот TyumenMedia.\n\nЗдесь вы можете оставить заявку на размещение рекламы.\n\nДля начала нажмите кнопку ниже:",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message

    if user_id not in user_sessions or "step" not in user_sessions[user_id]:
        await message.reply_text("Нажмите /start и затем кнопку для подачи заявки.")
        return

    session = user_sessions[user_id]

    if session.get("step") == "waiting_admin":
        await message.reply_text("⏳ Ваша заявка уже отправлена админу. Пожалуйста, дождитесь решения.")
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

def rejection_keyboard(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=f"reason|{key}|{user_id}")]
        for key, text in rejection_reasons.items()
    ])

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "begin_form":
        user_sessions[user_id] = {"step": "photo"}
        await context.bot.send_message(
            chat_id=user_id,
            text="Привет! Отправьте:\n1. Фото\n2. Текст\n3. Ссылку\n4. Бюджет\n— и я создам пост и передам админу на модерацию."
        )
        return

    if data == "send":
        session = user_sessions.get(user_id, {})
        if all(k in session for k in ["photo_file_id", "text", "link", "budget"]):
            caption = f"📌 <b>Рекламный пост</b>\n\n{session['text']}\n\n🔗 {session['link']}\n💸 Бюджет: {session['budget']}"
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_menu|{user_id}")
                ]
            ])
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=session["photo_file_id"], caption=caption, parse_mode="HTML", reply_markup=keyboard)
            await query.edit_message_caption(caption=caption + "\n\n⏳ Отправлено админу.")
            await context.bot.send_message(chat_id=user_id, text="✅ Заявка отправлена админу. Ожидайте решения.")
            session["step"] = "waiting_admin"
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
    elif data.startswith("approve"):
        _, target_id = data.split("|")
        target_id = int(target_id)
        msg = query.message
        photo = msg.photo[-1].file_id
        caption = msg.caption
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption, parse_mode="HTML")
        await query.edit_message_caption(caption=caption + "\n\n✅ Одобрено и опубликовано.")
        await context.bot.send_message(chat_id=target_id, text="✅ Ваша заявка одобрена и опубликована.")
        user_sessions[target_id] = {}
    elif data.startswith("reject_menu"):
        _, target_id = data.split("|")
        await query.edit_message_reply_markup(reply_markup=rejection_keyboard(target_id))
    elif data.startswith("reason"):
        _, reason_key, target_id = data.split("|")
        target_id = int(target_id)
        reason_text = rejection_reasons.get(reason_key, "❌ Заявка отклонена.")
        await context.bot.send_message(chat_id=target_id, text=f"{reason_text}\n
nВаша заявка отклонена.")
        await query.edit_message_caption(caption=query.message.caption + f"\n\n{reason_text}")
        user_sessions[target_id] = {}

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()







