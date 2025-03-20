import os
import subprocess
import time

import params

try:
	from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
	from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
	from telegram.constants import ParseMode
except ModuleNotFoundError:
	print("python-telegram-bot not found. Installing.")
	subprocess.check_call([sys.executable, "-m", "pip", "install", 'python-telegram-bot'])
	print("Packages installed, please run the program again.")
	exit()
try:
	from dotenv import load_dotenv
except ModuleNotFoundError:
	print("python-telegram-bot not found. Installing.")
	subprocess.check_call([sys.executable, "-m", "pip", "install", 'dotenv'])
	print("Packages installed, please run the program again.")
	exit()
load_dotenv()

import telegram_commands as commands
import image_conversion as img

import cv2

USERS_FILES = {}
USERS_HANDLING = {}
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	query = update.callback_query
	
	await query.answer()
	if USERS_HANDLING.get(update.effective_user.id) == "WAIT_CONVERT":
		await query.edit_message_text(
			f"ℹ️ Выбран вариант: {'Далее' if query.data == 'next' else 'Остановить'}",
			reply_markup=None
		)
		file_info = img.cons.fp_info(str(USERS_FILES[update.effective_user.id]))
		base_path = f"{file_info[2]}\\{file_info[0]}"
		for v in params.SUPPORTED_EXTENSIONS.values():
			for e in v:
				if os.path.exists(base_path + f".{e}"):
					os.remove(base_path + f".{e}")
		if query.data == "next":
			if file_info[1] == f".{params.OUTPUT_EXTENSIONS['image']}":
				await update.effective_chat.send_message(
					"ℹ️ Конвертирую изображение..."
				)
				start_time = time.time()
				out_path = base_path + f"_DISPLAY.{params.OUTPUT_CREATENEW_EXTENSIONS['image']}"
				img.cons.create_image(f"{base_path}{file_info[1]}", out_path)
				end_time = time.time()
				
				await update.effective_chat.send_message(
					"✅ Изображение конвертировано!\n"
					f"Время: `{round(end_time-start_time, 2)}с`",
					parse_mode=ParseMode.MARKDOWN
				)
				await update.effective_chat.send_document(
					document=out_path
				)
				if os.path.exists(out_path):
					os.remove(out_path)
			elif file_info[1] == f".{params.OUTPUT_EXTENSIONS['video']}":
				msg = await update.effective_chat.send_message(
					"ℹ️ Конвертирую видео... Это может занять долгое время."
				)
				start_time = time.time()
				out_path = base_path + f"_DISPLAY.{params.OUTPUT_CREATENEW_EXTENSIONS['video']}"
				in_path = f"{base_path}{file_info[1]}"
				dims, fps, frames = img.cons.video_read(in_path, out_path)
				original_text = msg.text
				images = []
				
				for i, frame in enumerate(frames):
					res = img.cons.image_data_to_image(frame)
					images.append(res)
					if i % round(float(fps) / 2) == 0:
						percent = round((i / len(frames)) * 100)
						await msg.edit_text(
							f"{original_text}\n\n"
							f"Кадр `{i + 1}/{len(frames)}` конвертирован... (`{percent}%`)",
							parse_mode=ParseMode.MARKDOWN
						)
				first_size = images[0].shape
				
				await msg.edit_text(
					f"{original_text}\n\n"
					f"Создаю видео файл...",
					parse_mode=ParseMode.MARKDOWN
				)
				
				video_size = (first_size[1], first_size[0])
				video = cv2.VideoWriter(
					f"{out_path}", cv2.VideoWriter_fourcc(*"MP4V"),
					# found codec thanks to: https://stackoverflow.com/questions/30509573/writing-an-mp4-video-using-python-opencv
					float(fps), video_size
				)
				for i, image in enumerate(images):
					temp = cv2.resize(image, video_size)  # BIG thanks to: https://stackoverflow.com/questions/53695143/python-cv2-videowriter-file-getting-corrupted
					video.write(temp)
					if i % round(float(fps) / 2) == 0:
						percent = round((i / len(frames)) * 100)
						await msg.edit_text(
							f"{original_text}\n\n"
							f"Кадр `{i + 1}/{len(images)}` записан... (`{percent}%`)",
							parse_mode=ParseMode.MARKDOWN
						)
				video.release()
				
				end_time = time.time()
				
				await update.effective_chat.send_message(
					"✅ Видео конвертировано!\n"
					f"Время: `{round(end_time - start_time, 2)}с`",
					parse_mode=ParseMode.MARKDOWN
				)
				await update.effective_chat.send_document(
					document=out_path
				)
				if os.path.exists(out_path):
					os.remove(out_path)
			
			if os.path.exists(base_path + f".{params.OUTPUT_EXTENSIONS['image']}"):
				os.remove(base_path + f".{params.OUTPUT_EXTENSIONS['image']}")
			if os.path.exists(base_path + f".{params.OUTPUT_EXTENSIONS['video']}"):
				os.remove(base_path + f".{params.OUTPUT_EXTENSIONS['video']}")
			USERS_HANDLING[update.effective_user.id] = None
			USERS_FILES[update.effective_user.id] = None
		else:
			if os.path.exists(base_path + f".{params.OUTPUT_EXTENSIONS['image']}"):
				os.remove(base_path + f".{params.OUTPUT_EXTENSIONS['image']}")
			if os.path.exists(base_path + f".{params.OUTPUT_EXTENSIONS['video']}"):
				os.remove(base_path + f".{params.OUTPUT_EXTENSIONS['video']}")
			USERS_HANDLING[update.effective_user.id] = None
			USERS_FILES[update.effective_user.id] = None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	global USERS_HANDLING
	
	if USERS_HANDLING.get(update.effective_user.id, None) is not None:
		if USERS_HANDLING.get(update.effective_user.id) == "WAIT_DIM":
			file_dimensions = (1, 1)
			given_dimensions = update.message.text
			if given_dimensions.lower() != "отмена":
				dimensions = given_dimensions.split(" ")
				if len(dimensions) == 2:
					dimensions = (dimensions[0], dimensions[1])
					if (not dimensions[0].isdigit()) or (not dimensions[1].isdigit()):
						await update.effective_chat.send_message("⚠️ Введены не числа. Попробуйте снова.")
						return
					dimensions = (int(dimensions[0]), int(dimensions[1]))
					if (dimensions[0] < 1) or (dimensions[1] < 1):
						await update.effective_chat.send_message("⚠️ Размер слишком мал. Попробуйте снова.")
						return
					if (dimensions[0] > params.X_LIMIT) or (dimensions[1] > params.Y_LIMIT):
						await update.effective_chat.send_message("⚠️ Большой размер изображения. "
																 "Операция может занять долгое время.")
					file_dimensions = dimensions
				else:
					await update.effective_chat.send_message("⚠️ Введены не числа. Попробуйте снова.")
					return
			else:
				if os.path.exists(USERS_FILES[update.effective_user.id]):
					os.remove(USERS_FILES[update.effective_user.id])
				USERS_HANDLING[update.effective_user.id] = None
				await update.effective_chat.send_message("✅ Операция отменена.")
				return
			
			await update.effective_chat.send_message(f"✅ Принятый размер: `{file_dimensions}`",
													 parse_mode=ParseMode.MARKDOWN)
			await update.effective_chat.send_message("ℹ️ Конвертирую файл...")
			
			USERS_HANDLING[update.effective_user.id] = None
			downloaded_path = USERS_FILES[update.effective_user.id]
			uploaded_info = img.cons.fp_info(downloaded_path, True)
			
			converted_path = ""
			if uploaded_info[1][1:] in params.SUPPORTED_EXTENSIONS.get("image"):
				start_time = time.time()
				converted_path = img.cons.convert_image(str(downloaded_path), file_dimensions, start_time, True)
				end_time = time.time()
				if type(converted_path).__name__ == "list":
					await update.effective_chat.send_message(
						"😥 *Ошибка во время конвертации файла:*\n"
						f"`{converted_path[0]}`",
						parse_mode=ParseMode.MARKDOWN
					)
				else:
					await update.effective_chat.send_message(
						"✅ *Файл успешно конвертирован!*\n"
						f"Время: `{round(end_time-start_time, 2)}с`\n"
						f"Размер: `{dimensions}`",
						parse_mode=ParseMode.MARKDOWN
					)
					await update.effective_chat.send_document(
						document=converted_path
					)
			elif uploaded_info[1][1:] in params.SUPPORTED_EXTENSIONS.get("video"):
				start_time = time.time()
				converted_path, fps = img.cons.convert_video(str(downloaded_path), file_dimensions, start_time, True)
				end_time = time.time()
				if type(converted_path).__name__ == "list":
					await update.effective_chat.send_message(
						"😥 *Ошибка во время конвертации видео:*\n"
						f"`{converted_path[0]}`",
						parse_mode=ParseMode.MARKDOWN
					)
				else:
					await update.effective_chat.send_message(
						"✅ *Видео успешно конвертировано!*\n"
						f"Время: `{round(end_time - start_time, 2)}с`\n"
						f"Размер: `{dimensions}`\n"
						f"Кадров в секунду: `{fps}`",
						parse_mode=ParseMode.MARKDOWN
					)
					await update.effective_chat.send_document(
						document=converted_path
					)
					
			keyboard = [
				[InlineKeyboardButton("➡️ Далее ➡️", callback_data="next")],
				[InlineKeyboardButton("🛑 Остановить 🛑", callback_data="cancel")]
			]
			USERS_HANDLING[update.effective_user.id] = "WAIT_CONVERT"
			USERS_FILES[update.effective_user.id] = converted_path
			
			await update.effective_chat.send_message(
				"💬 Если вы хотите преобразовать свой файл в изображение/видео, нахмите на кнопку \"Далее\". "
				"Иначе нажмите на кнопку \"Остановить\"",
				reply_markup=InlineKeyboardMarkup(keyboard),
				parse_mode=ParseMode.MARKDOWN
			)
		elif USERS_HANDLING.get(update.effective_user.id) == "WAIT_CONVERT":
			await update.effective_chat.send_message("⚠️ Сначала выберите, что делать дальше.")
	else:
		if update.message.document:
			await update.effective_chat.send_message("🔎 Смотрю файл...")
			file = await update.message.document.get_file()
			uploaded_info = img.cons.fp_info(file.file_path, True)
			ext = []
			for v in params.SUPPORTED_EXTENSIONS.values():
				ext += v
			if uploaded_info[1][1:] in ext:
				await update.effective_chat.send_message("✅ Файл опознан.")
				await update.effective_chat.send_message("ℹ️ Скачиваю файл...")
				
				uploaded_info = img.cons.fp_info(file.file_path, True)
				downloaded_path = await file.download_to_drive(
					custom_path=f"for_converting/FILE_{update.effective_user.id}_{file.file_unique_id}.{uploaded_info[1][1:]}"
				)
				await update.effective_chat.send_message("✅ Файл скачан.")
				
				shape = (0, 0)
				if uploaded_info[1][1:] in params.SUPPORTED_EXTENSIONS["image"]:
					image = cv2.imread(str(downloaded_path))
					shape = (image.shape[1], image.shape[0])
				elif uploaded_info[1][1:] in params.SUPPORTED_EXTENSIONS["video"]:
					vid = cv2.VideoCapture(str(downloaded_path))
					_, first_frame = vid.read()
					shape = (first_frame.shape[1], first_frame.shape[0])
					vid.release()
				
				while shape[0] > params.X_LIMIT and shape[1] > params.Y_LIMIT:
					shape = (int(shape[0] // 1.5), int(shape[1] // 1.5))
				
				await update.effective_chat.send_message("💬 Введите размер изображения для выхода\n(в формате `x y`).\n"
														 f"*Рекоммендуемый размер:* `{shape[0]} {shape[1]}`\n"
														 f"*Размер выше* `{params.X_LIMIT} {params.Y_LIMIT}` *может занять долгое время.*\n"
														 "Вы можете ввести *\"отмена\"*, если хотите отменить операцию.",
														 parse_mode=ParseMode.MARKDOWN)
				USERS_FILES[update.effective_user.id] = downloaded_path
				USERS_HANDLING[update.effective_user.id] = "WAIT_DIM"
			else:
				await update.effective_chat.send_message(f"❌ Неподдерживаемое расширение файла \"{uploaded_info[1][1:]}\".")

app = ApplicationBuilder().token(os.getenv("TOKEN")).build()
for cmd in commands.commands:
	app.add_handler(CommandHandler([cmd] + commands.commands[cmd][0], commands.commands[cmd][1]))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(MessageHandler(None, message_handler))

app.run_polling()
