import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters,
                          ContextTypes, ConversationHandler, CallbackQueryHandler)

# Этапы диалога
PHOTO, TEXT, LINK, BUDGET, PREVIEW, EDIT_CHOICE = range(6)

# Список обязательных полей
REQUIRED_FIELDS = ["photo", "text", "link"]

# TOKEN и ID администратора и канала
TOKEN = "8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o"
ADMIN_ID = 987540995
CHANNEL_ID = "@tyumenmedia"

# Временное хранилище заявок
user_data_storage = {}

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь фото для рекламы.")
    user_data_storage[update.effective_user.id] = {}
    return PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    user_data_storage[update.effective_user.id]["photo"] = photo
    await update.message.reply_text("Теперь отправь текст поста")
    return TEXT

async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_user.id]["text"] = update.message.text
    await update.message.reply_text("Отправь ссылку")
    return LINK

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_user.id]["link"] = update.message.text
    await update.message.reply_text("Укажи рекламный бюджет (например: 1000 ₽)")
    return BUDGET

async def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_user.id]["budget"] = update.message.text
    return await send_preview(update, context)

async def send_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = user_data_storage[update.effective_user.id]
    caption = f"{data['text']}\n\n🔗 {data['link']}\n💸 Бюджет: {data.get('budget', 'не указан')}"

    keyboard = [
        [InlineKeyboardButton("📤 Отправить", callback_data="send")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("🗑 Удалить", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(chat_id=update.effective_user.id, photo=data['photo'], caption=caption, reply_markup=reply_markup)
    return PREVIEW

async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "send":
        data = user_data_storage[user_id]
        caption = f"{data['text']}\n\n🔗 {data['link']}\n💸 Бюджет: {data.get('budget', 'не указан')}"

        # Кнопки для админа
        keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=caption, reply_markup=reply_markup)
        await query.edit_message_caption(caption="Отправлено на модерацию.")
        return ConversationHandler.END

    elif query.data == "edit":
        keyboard = [
            [InlineKeyboardButton("📷 Фото", callback_data="edit_photo"),
             InlineKeyboardButton("💬 Текст", callback_data="edit_text")],
            [InlineKeyboardButton("🔗 Ссылка", callback_data="edit_link"),
             InlineKeyboardButton("💸 Бюджет", callback_data="edit_budget")],
            [InlineKeyboardButton("❌ Отменить редактирование", callback_data="cancel_edit")]
        ]
        await query.edit_message_caption(caption="Выбери, что хочешь изменить:", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_CHOICE

    elif query.data == "cancel":
        await query.edit_message_caption(caption="Заявка удалена.")
        user_data_storage.pop(user_id, None)
        return ConversationHandler.END

async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("edit_", "")

    if field == "photo":
        await query.message.reply_text("Пришли новое фото")
        return PHOTO
    elif field == "text":
        await query.message.reply_text("Введи новый текст")
        return TEXT
    elif field == "link":
        await query.message.reply_text("Отправь новую ссылку")
        return LINK
    elif field == "budget":
        await query.message.reply_text("Укажи новый бюджет")
        return BUDGET
    elif field == "cancel":
        return await send_preview(update, context)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id = query.data.split("_")
    user_id = int(user_id)
    data = user_data_storage.get(user_id)

    if not data:
        await query.edit_message_caption(caption="❌ Данные заявки не найдены или уже удалены.")
        return

    caption = f"{data['text']}\n\n🔗 {data['link']}\n💸 Бюджет: {data.get('budget', 'не указан')}"

    if action == "approve":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data['photo'], caption=caption)
        await context.bot.send_message(chat_id=user_id, text="✅ Ваша реклама опубликована!")
        await query.edit_message_caption(caption="✅ Пост опубликован.")

    elif action == "reject":
        await context.bot.send_message(chat_id=user_id, text="❌ Ваша заявка на рекламу отклонена.")
        await query.edit_message_caption(caption="❌ Заявка отклонена.")

    user_data_storage.pop(user_id, None)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заявка отменена.")
    user_data_storage.pop(update.effective_user.id, None)
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

async def main():
    app = ApplicationBuilder().token(os.getenv("TOKEN")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_budget)],
            PREVIEW: [CallbackQueryHandler(preview_callback)],
            EDIT_CHOICE: [CallbackQueryHandler(handle_edit_choice)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve|reject)_"))
    app.add_error_handler(error_handler)

    print("Бот запущен...")
    await app.run_polling()

import asyncio

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()








