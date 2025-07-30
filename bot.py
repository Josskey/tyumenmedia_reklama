import logging
import os
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto)
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler)

# Включаем логгирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Этапы ConversationHandler
PHOTO, TEXT, LINK, BUDGET, CONFIRM, EDIT, EDIT_PARAM = range(7)

user_data_store = {}

# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Отправь фото для рекламы:")
    return PHOTO

async def handle_photo(update: Update, context: CallbackContext):
    user_data_store[update.effective_chat.id] = {"photo": update.message.photo[-1].file_id}
    await update.message.reply_text("Отлично! Теперь отправь рекламный текст:")
    return TEXT

async def handle_text(update: Update, context: CallbackContext):
    user_data_store[update.effective_chat.id]["text"] = update.message.text
    await update.message.reply_text("Теперь отправь ссылку:")
    return LINK

async def handle_link(update: Update, context: CallbackContext):
    user_data_store[update.effective_chat.id]["link"] = update.message.text
    await update.message.reply_text("Укажи бюджет:")
    return BUDGET

async def handle_budget(update: Update, context: CallbackContext):
    user_data_store[update.effective_chat.id]["budget"] = update.message.text

    data = user_data_store[update.effective_chat.id]
    caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']}"

    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data="submit"),
         InlineKeyboardButton("Редактировать", callback_data="edit"),
         InlineKeyboardButton("Удалить", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(photo=data['photo'], caption=caption, reply_markup=reply_markup)
    return CONFIRM

async def confirm_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    choice = query.data

    user_id = query.from_user.id
    data = user_data_store.get(user_id)

    if choice == "submit":
        caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']}"
        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать", callback_data="approve"),
             InlineKeyboardButton("❌ Отклонить", callback_data="reject")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=caption, reply_markup=reply_markup)
        await query.edit_message_caption(caption="Заявка отправлена на модерацию. Ожидайте ответа.")
        return ConversationHandler.END

    elif choice == "edit":
        keyboard = [
            [InlineKeyboardButton("Фото", callback_data="edit_photo"),
             InlineKeyboardButton("Текст", callback_data="edit_text")],
            [InlineKeyboardButton("Ссылка", callback_data="edit_link"),
             InlineKeyboardButton("Бюджет", callback_data="edit_budget")],
            [InlineKeyboardButton("Отменить редактирование", callback_data="cancel"),
             InlineKeyboardButton("Сохранить", callback_data="save")]
        ]
        await query.edit_message_caption(caption="Что хочешь изменить?", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT

    elif choice == "cancel":
        await query.edit_message_caption(caption="Заявка отменена.")
        user_data_store.pop(user_id, None)
        return ConversationHandler.END

async def handle_edit_param(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['edit_target'] = query.data.split("_")[1]  # photo/text/link/budget
    await query.edit_message_caption(caption=f"Отправьте новое значение для: {context.user_data['edit_target']}")
    return EDIT_PARAM

async def save_edit(update: Update, context: CallbackContext):
    param = context.user_data.get('edit_target')
    value = update.message.text or (update.message.photo[-1].file_id if update.message.photo else None)
    if param and value:
        user_data_store[update.effective_chat.id][param] = value

    data = user_data_store[update.effective_chat.id]
    caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']}"
    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data="submit"),
         InlineKeyboardButton("Редактировать", callback_data="edit"),
         InlineKeyboardButton("Удалить", callback_data="cancel")]
    ]
    await update.message.reply_photo(photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

async def admin_decision(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "approve":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=query.message.photo[-1].file_id, caption=query.message.caption)
        await query.edit_message_caption(caption="✅ Опубликовано в канале")

    elif choice == "reject":
        await query.edit_message_caption(caption="❌ Заявка отклонена")

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# Запуск
async def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            CONFIRM: [CallbackQueryHandler(confirm_choice, pattern="^(submit|edit|cancel)$")],
            EDIT: [CallbackQueryHandler(handle_edit_param, pattern="^edit_"), CallbackQueryHandler(confirm_choice, pattern="^(cancel|save)$")],
            EDIT_PARAM: [MessageHandler(filters.TEXT | filters.PHOTO, save_edit)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(approve|reject)$"))

    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())









