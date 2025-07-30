import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler, filters)

import os
import json

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 987540995))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@tyumenmedia")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Этапы диалога
PHOTO, TEXT, LINK, BUDGET, CONFIRM = range(5)
EDIT_CHOICE, EDIT_PHOTO, EDIT_TEXT, EDIT_LINK, EDIT_BUDGET = range(5, 10)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 Отправьте фото для рекламного поста")
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {
        "photo": update.message.photo[-1].file_id
    }
    await update.message.reply_text("✏️ Введите текст поста")
    return TEXT

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["text"] = update.message.text
    await update.message.reply_text("🔗 Введите ссылку (обязательно)")
    return LINK

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["link"] = update.message.text
    await update.message.reply_text("💰 Введите бюджет (опционально)")
    return BUDGET

async def handle_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["budget"] = update.message.text
    return await preview(update, context)

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = user_data[chat_id]
    caption = f"{data['text']}\n\n🔗 {data['link']}"
    if data.get("budget"):
        caption += f"\n💰 Бюджет: {data['budget']}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Отправить", callback_data="send"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit"),
            InlineKeyboardButton("🗑️ Удалить", callback_data="delete")
        ]
    ]
    await context.bot.send_photo(chat_id=chat_id, photo=data["photo"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM

async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "send":
        data = user_data[chat_id]
        caption = f"{data['text']}\n\n🔗 {data['link']}"
        if data.get("budget"):
            caption += f"\n💰 Бюджет: {data['budget']}"
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=data['photo'], caption=caption)
        await query.edit_message_caption("✅ Заявка отправлена на модерацию")
        return ConversationHandler.END

    elif query.data == "edit":
        keyboard = [
            [InlineKeyboardButton("📷 Изменить фото", callback_data="edit_photo")],
            [InlineKeyboardButton("✏️ Изменить текст", callback_data="edit_text")],
            [InlineKeyboardButton("🔗 Изменить ссылку", callback_data="edit_link")],
            [InlineKeyboardButton("💰 Изменить бюджет", callback_data="edit_budget")],
            [
                InlineKeyboardButton("✅ Сохранить", callback_data="save_edit"),
                InlineKeyboardButton("❌ Отменить", callback_data="cancel_edit")
            ]
        ]
        await query.edit_message_caption("Выберите, что хотите изменить:", reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_CHOICE

    elif query.data == "delete":
        await query.edit_message_caption("❌ Заявка удалена")
        user_data.pop(chat_id, None)
        return ConversationHandler.END

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "edit_photo":
        await context.bot.send_message(chat_id, "📷 Отправьте новое фото")
        return EDIT_PHOTO
    elif query.data == "edit_text":
        await context.bot.send_message(chat_id, "✏️ Введите новый текст")
        return EDIT_TEXT
    elif query.data == "edit_link":
        await context.bot.send_message(chat_id, "🔗 Введите новую ссылку")
        return EDIT_LINK
    elif query.data == "edit_budget":
        await context.bot.send_message(chat_id, "💰 Введите новый бюджет")
        return EDIT_BUDGET
    elif query.data == "save_edit":
        return await preview(update, context)
    elif query.data == "cancel_edit":
        await context.bot.send_message(chat_id, "🔙 Редактирование отменено")
        return await preview(update, context)

async def update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("✅ Фото обновлено")
    return await preview(update, context)

async def update_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["text"] = update.message.text
    await update.message.reply_text("✅ Текст обновлён")
    return await preview(update, context)

async def update_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["link"] = update.message.text
    await update.message.reply_text("✅ Ссылка обновлена")
    return await preview(update, context)

async def update_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["budget"] = update.message.text
    await update.message.reply_text("✅ Бюджет обновлён")
    return await preview(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Заявка отменена")
    user_data.pop(update.effective_chat.id, None)
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
            TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget)],
            CONFIRM: [CallbackQueryHandler(handle_decision)],
            EDIT_CHOICE: [CallbackQueryHandler(edit_choice)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO, update_photo)],
            EDIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_text)],
            EDIT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_link)],
            EDIT_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_budget)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.run_polling()


