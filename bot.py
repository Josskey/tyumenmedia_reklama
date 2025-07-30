import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# Настройки
TOKEN = "8180478614:AAGY0UbvZlK-4wF2n4V25h_Wy_rWV1ogm6o"
ADMIN_ID = 987540995
CHANNEL_ID = "@tyumenmedia"

# Стейты
PHOTO, TEXT, LINK, BUDGET, CONFIRM, EDIT_CHOICE = range(6)

# Временное хранилище заявок
user_data = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("Привет! Пришли изображение для рекламы.")
    return PHOTO

def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    context.user_data['photo'] = photo
    update.message.reply_text("Теперь отправь рекламный текст.")
    return TEXT

def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['text'] = update.message.text
    update.message.reply_text("Отправь ссылку (обязательно).")
    return LINK

def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['link'] = update.message.text
    update.message.reply_text("Укажи рекламный бюджет.")
    return BUDGET

def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['budget'] = update.message.text
    return preview(update, context)

def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    caption = f"{data['text']}\n\n{data['link']}\n\nБюджет: {data['budget']}"
    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="submit"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit"),
            InlineKeyboardButton("❌ Удалить", callback_data="cancel"),
        ]
    ]
    update.message.reply_photo(photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    choice = query.data

    if choice == "submit":
        data = context.user_data
        caption = f"{data['text']}\n\n{data['link']}\n\nБюджет: {data['budget']}"
        context.bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=caption, reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data="publish"),
                InlineKeyboardButton("❌ Отклонить", callback_data="reject")
            ]
        ]))
        query.edit_message_text("Заявка отправлена на модерацию.")
        return ConversationHandler.END

    elif choice == "edit":
        keyboard = [
            [InlineKeyboardButton("Фото", callback_data="edit_photo"),
             InlineKeyboardButton("Текст", callback_data="edit_text")],
            [InlineKeyboardButton("Ссылка", callback_data="edit_link"),
             InlineKeyboardButton("Бюджет", callback_data="edit_budget")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")]
        ]
        query.edit_message_text("Что редактировать?", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_CHOICE

    elif choice == "cancel":
        query.edit_message_text("Заявка удалена.")
        return ConversationHandler.END

def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    context.user_data['edit_param'] = query.data

    if query.data == "edit_photo":
        context.bot.send_message(chat_id=query.from_user.id, text="Пришли новое фото.")
        return PHOTO
    elif query.data == "edit_text":
        context.bot.send_message(chat_id=query.from_user.id, text="Введи новый текст.")
        return TEXT
    elif query.data == "edit_link":
        context.bot.send_message(chat_id=query.from_user.id, text="Введи новую ссылку.")
        return LINK
    elif query.data == "edit_budget":
        context.bot.send_message(chat_id=query.from_user.id, text="Укажи новый бюджет.")
        return BUDGET
    elif query.data == "cancel_edit":
        return preview(update, context)

def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    if query.data == "publish":
        context.bot.send_photo(chat_id=CHANNEL_ID, photo=query.message.photo[-1].file_id, caption=query.message.caption)
        query.edit_message_text("✅ Опубликовано")
    elif query.data == "reject":
        query.edit_message_text("❌ Отклонено")

def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("Заявка отменена.")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_budget)],
            CONFIRM: [CallbackQueryHandler(confirm)],
            EDIT_CHOICE: [CallbackQueryHandler(edit_choice)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(publish|reject)$"))
    app.run_polling()

if __name__ == "__main__":
    main()








