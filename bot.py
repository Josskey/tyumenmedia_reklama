import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters,
                          ConversationHandler, CallbackContext, CallbackQueryHandler)
import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 987540995))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@tyumenmedia")

# Этапы диалога
PHOTO, TEXT, LINK, BUDGET, CONFIRM = range(5)

# Словарь для хранения черновиков заявок
user_data_store = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Давайте начнем с загрузки фото для вашей рекламы. 📷")
    return PHOTO

async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1].file_id
    user_data_store[user_id] = {'photo': photo}
    await update.message.reply_text("Отлично! Теперь отправьте текст рекламного поста ✍️")
    return TEXT

async def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data_store[user_id]['text'] = update.message.text
    await update.message.reply_text("Теперь пришлите ссылку на ваш сайт или страницу 🌐")
    return LINK

async def handle_link(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data_store[user_id]['link'] = update.message.text
    await update.message.reply_text("Последний шаг — укажите бюджет рекламы 💰")
    return BUDGET

async def handle_budget(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data_store[user_id]['budget'] = update.message.text

    data = user_data_store[user_id]
    caption = f"{data['text']}\n\n🔗 {data['link']}\n💸 Бюджет: {data['budget']}"
    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data="send"),
         InlineKeyboardButton("🔄 Редактировать", callback_data="edit"),
         InlineKeyboardButton("🗑 Удалить", callback_data="delete")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(photo=data['photo'], caption=caption, reply_markup=reply_markup)
    return CONFIRM

async def confirm_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data_store.get(user_id)

    if query.data == "send":
        caption = f"{data['text']}\n\n🔗 {data['link']}\n💸 Бюджет: {data['budget']}"
        keyboard = [
            [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{user_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject|{user_id}")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=caption, reply_markup=markup)
        await query.edit_message_caption(caption="Заявка отправлена на модерацию ✅")
        return ConversationHandler.END

    elif query.data == "edit":
        await query.edit_message_caption(caption="Редактирование заявки. Отправьте новое фото.")
        return PHOTO

    elif query.data == "delete":
        user_data_store.pop(user_id, None)
        await query.edit_message_caption(caption="Заявка удалена ❌")
        return ConversationHandler.END

async def moderation_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("|")
    user_id = int(user_id)
    data = user_data_store.get(user_id)

    if not data:
        await query.edit_message_caption("Заявка не найдена или уже обработана.")
        return

    if action == "approve":
        caption = f"{data['text']}\n\n🔗 {data['link']}"
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data['photo'], caption=caption)
        await query.edit_message_caption("✅ Заявка одобрена и опубликована.")
        user_data_store.pop(user_id, None)
    elif action == "reject":
        await query.edit_message_caption("❌ Заявка отклонена.")
        user_data_store.pop(user_id, None)

async def cancel(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_data_store.pop(user_id, None)
    await update.message.reply_text("Заявка отменена.")
    return ConversationHandler.END

if __name__ == '__main__':
    from telegram.ext import Application
    import asyncio

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            CONFIRM: [CallbackQueryHandler(confirm_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(moderation_callback, pattern="^(approve|reject)\\|"))

    app.run_polling()

