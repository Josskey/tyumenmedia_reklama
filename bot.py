import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes, ConversationHandler

# Константы для шагов
PHOTO, TEXT, LINK, BUDGET, PREVIEW, EDIT_SELECT, EDIT_PHOTO, EDIT_TEXT, EDIT_LINK, EDIT_BUDGET = range(10)

# Временное хранилище заявок
user_data_storage = {}
admin_id = 987540995  # Твой Telegram ID
channel_id = "@tyumenmedia"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь фото для рекламы.")
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id] = {
        "photo": update.message.photo[-1].file_id
    }
    await update.message.reply_text("Отлично! Теперь пришли текст объявления.")
    return TEXT

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]["text"] = update.message.text
    await update.message.reply_text("Теперь отправь ссылку.")
    return LINK

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]["link"] = update.message.text
    await update.message.reply_text("И последний шаг — укажи бюджет в рублях.")
    return BUDGET

async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]["budget"] = update.message.text
    return await send_preview(update, context)

async def send_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = user_data_storage.get(update.effective_chat.id)
    if not data:
        return ConversationHandler.END

    caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']} ₽"
    buttons = [
        [InlineKeyboardButton("✅ Отправить", callback_data="submit")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="edit"), InlineKeyboardButton("🗑️ Удалить", callback_data="delete")]
    ]
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
    return PREVIEW

async def handle_preview_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id

    if action == "submit":
        data = user_data_storage.get(user_id)
        caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']} ₽"
        buttons = [
            [InlineKeyboardButton("📢 Публиковать", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")]
        ]
        await context.bot.send_photo(chat_id=admin_id, photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(buttons))
        await query.edit_message_text("Заявка отправлена на модерацию. Ожидайте ответа.")
        return ConversationHandler.END

    elif action == "edit":
        buttons = [
            [InlineKeyboardButton("Фото", callback_data="edit_photo"),
             InlineKeyboardButton("Текст", callback_data="edit_text")],
            [InlineKeyboardButton("Ссылку", callback_data="edit_link"),
             InlineKeyboardButton("Бюджет", callback_data="edit_budget")],
            [InlineKeyboardButton("↩️ Отменить", callback_data="cancel_edit")]
        ]
        await query.edit_message_text("Что вы хотите изменить?", reply_markup=InlineKeyboardMarkup(buttons))
        return EDIT_SELECT

    elif action == "delete":
        user_data_storage.pop(user_id, None)
        await query.edit_message_text("Заявка удалена.")
        return ConversationHandler.END

async def handle_edit_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "edit_photo":
        await query.edit_message_text("Отправьте новое фото:")
        return EDIT_PHOTO
    elif choice == "edit_text":
        await query.edit_message_text("Введите новый текст:")
        return EDIT_TEXT
    elif choice == "edit_link":
        await query.edit_message_text("Введите новую ссылку:")
        return EDIT_LINK
    elif choice == "edit_budget":
        await query.edit_message_text("Введите новый бюджет:")
        return EDIT_BUDGET
    elif choice == "cancel_edit":
        return await send_preview(update, context)

async def edit_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("Фото обновлено.")
    return await send_preview(update, context)

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]['text'] = update.message.text
    await update.message.reply_text("Текст обновлен.")
    return await send_preview(update, context)

async def edit_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]['link'] = update.message.text
    await update.message.reply_text("Ссылка обновлена.")
    return await send_preview(update, context)

async def edit_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_storage[update.effective_chat.id]['budget'] = update.message.text
    await update.message.reply_text("Бюджет обновлён.")
    return await send_preview(update, context)

async def admin_approve_or_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, user_id_str = query.data.split("_")
    user_id = int(user_id_str)
    data = user_data_storage.get(user_id)

    if not data:
        await query.edit_message_text("Заявка не найдена или уже была обработана.")
        return

    if action == "approve":
        caption = f"{data['text']}\n\n🔗 {data['link']}\n💰 Бюджет: {data['budget']} ₽"
        await context.bot.send_photo(chat_id=channel_id, photo=data['photo'], caption=caption)
        await query.edit_message_text("Заявка одобрена и опубликована.")
    else:
        await context.bot.send_message(chat_id=user_id, text="Ваша заявка отклонена.")
        await query.edit_message_text("Заявка отклонена.")

    user_data_storage.pop(user_id, None)

from telegram.ext import Application

app = ApplicationBuilder().token("8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
        BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
        PREVIEW: [CallbackQueryHandler(handle_preview_action)],
        EDIT_SELECT: [CallbackQueryHandler(handle_edit_selection)],
        EDIT_PHOTO: [MessageHandler(filters.PHOTO, edit_photo)],
        EDIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
        EDIT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_link)],
        EDIT_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_budget)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(admin_approve_or_reject, pattern=r"^(approve|reject)_\d+$"))

app.run_polling()



