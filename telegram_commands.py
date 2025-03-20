import math
import random
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, \
	ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler
from telegram.constants import ParseMode

import image_conversion as img

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
	ext = img.cons.formatting("supported_extensions")
	await update.effective_chat.send_message(
		f"*Для начала работы отправьте любой файл с расширением:*\n{' */* '.join(x for x in ext)}\n\n"
		f"*Важно! Файл нужно прислать как документ, а не изображение/видео.*\n"
		f"Для этого нажмите на `📎 (отправить вложение) -> Файл`.",
		parse_mode=ParseMode.MARKDOWN
	)

commands = {
	"start": [["s", "help", "h"], start_command]
}
