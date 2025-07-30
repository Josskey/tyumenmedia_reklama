import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, ConversationHandler

TOKEN = "8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o"
ADMIN_CHAT_ID = 987540995
CHANNEL_ID = "@tyumenmedia"

logging.basicConfig(level=logging.INFO)

# Этапы разговора
PHOTO, TEXT, LINK, BUDGET, PREVIEW, EDIT_SELECT, EDIT_FIELD = range(7)

user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь фото для начала оформления заявки на рекламу.")
    user_data_store[update.effective_chat.id] = {}
    return PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = update.message.photo[-1].file_id
    user_data_store[update.effective_chat.id]['photo'] = photo_file
    await update.message.reply_text("Теперь отправь текст для поста.")
    return TEXT

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]['text'] = update.message.text
    await update.message.reply_text("Отправь ссылку для поста.")
    return LINK

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]['link'] = update.message.text
    await update.message.reply_text("Укажи бюджет (руб).")
    return BUDGET

async def receive_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_store[update.effective_chat.id]['budget'] = update.message.text
    return await preview_post(update, context)

async def preview_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = user_data_store.get(update.effective_chat.id, {})
    caption = f"{data['text']}\n{data['link']}\n\n💰 Бюджет: {data['budget']} руб."
    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data="submit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit")],
        [InlineKeyboardButton("❌ Удалить", callback_data="cancel")]
    ]
    await update.message.reply_photo(photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    return PREVIEW

async def handle_preview_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data_store.get(user_id, {})

    if query.data == "submit":
        caption = f"{data['text']}\n{data['link']}\n\n💰 Бюджет: {data['budget']} руб."
        keyboard = [
            [InlineKeyboardButton("✅ Опубликовать", callback_data="approve"),
             InlineKeyboardButton("❌ Отклонить", callback_data="reject")]
        ]
        await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.edit_message_caption(caption="Заявка отправлена на модерацию ✅")
        return ConversationHandler.END

    elif query.data == "edit":
        edit_keyboard = [
            [InlineKeyboardButton("Фото", callback_data="edit_photo"),
             InlineKeyboardButton("Текст", callback_data="edit_text")],
            [InlineKeyboardButton("Ссылка", callback_data="edit_link"),
             InlineKeyboardButton("Бюджет", callback_data="edit_budget")],
            [InlineKeyboardButton("❌ Отменить редактирование", callback_data="cancel_edit")]
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(edit_keyboard))
        return EDIT_SELECT

    elif query.data == "cancel":
        await query.edit_message_caption(caption="Заявка удалена ❌")
        user_data_store.pop(user_id, None)
        return ConversationHandler.END

async def edit_field_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['editing'] = query.data

    prompts = {
        'edit_photo': "Отправь новое фото",
        'edit_text': "Отправь новый текст",
        'edit_link': "Отправь новую ссылку",
        'edit_budget': "Укажи новый бюджет"
    }
    if query.data == "cancel_edit":
        return await preview_post(update, context)

    await query.edit_message_text(prompts[query.data])
    return EDIT_FIELD

async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    edit_type = context.user_data.get('editing')

    if edit_type == "edit_photo":
        user_data_store[user_id]['photo'] = update.message.photo[-1].file_id
    elif edit_type == "edit_text":
        user_data_store[user_id]['text'] = update.message.text
    elif edit_type == "edit_link":
        user_data_store[user_id]['link'] = update.message.text
    elif edit_type == "edit_budget":
        user_data_store[user_id]['budget'] = update.message.text

    await update.message.reply_text("Изменения сохранены ✅")
    return await preview_post(update, context)

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    message = query.message

    if query.data == "approve":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=message.caption)
        await query.edit_message_caption(caption="✅ Пост опубликован в канале")
    elif query.data == "reject":
        await query.edit_message_caption(caption="❌ Пост отклонён")

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
        BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_budget)],
        PREVIEW: [CallbackQueryHandler(handle_preview_buttons)],
        EDIT_SELECT: [CallbackQueryHandler(edit_field_choice)],
        EDIT_FIELD: [MessageHandler(filters.ALL, handle_edit_input)],
    },
    fallbacks=[]
)

application = Application.builder().token(TOKEN).build()
application.add_handler(conv_handler)
application.add_handler(CallbackQueryHandler(handle_admin_action, pattern="^(approve|reject)$"))

async def main():
    await application.initialize()
    await application.start()
    print("Бот запущен...")
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())









