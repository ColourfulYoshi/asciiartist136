import os
import platform
import binascii
import time
import subprocess

try:
	import cv2
	import numpy as np
except ModuleNotFoundError:
	print("opencv-python not found. Installing.")
	subprocess.check_call([sys.executable, "-m", "pip", "install", 'opencv-python'])
	print("Packages installed, please run the program again.")
	exit()

import params

operating_system = platform.system()

class ImageOperation:
	def __init__(self):
		pass
	
	def get_char_for_brightness(self, bright):
		gap = round(255/len(params.SYMBOLS))
		section = bright // gap
		char = params.SYMBOLS[(len(params.SYMBOLS)-1)-min([section, len(params.SYMBOLS)-1])]
		return char
	
	def read_image(self, fp):
		img = cv2.imread(fp)
		return img
	
	def resize(self, img, width, height):
		out = cv2.resize(img, (width, height))
		return out
	
	def grayscale(self, img):
		out = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		return out
	
	def pixelize(self, img, pixel_w=16, pixel_h=16):
		height, width = img.shape[:2]
		temp = cv2.resize(img, (pixel_w, pixel_h), interpolation=cv2.INTER_NEAREST)
		out = cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)
		return out
	
	def closest_color(self, col): # col is given in the [b, g, r] format
		res = [-1, ""]
		for c in params.COLORS:
			rdiff = abs(int(col[2]) - c[0][0])
			gdiff = abs(int(col[1]) - c[0][1])
			bdiff = abs(int(col[0]) - c[0][2])
			diff = (rdiff + gdiff + bdiff)/3
			if (diff < res[0]) or (res[0] == -1):
				res = [diff, c[1]]
		return res[1]
	
	def image_to_text(self, img):
		"""
		Takes a BGR cv2 image and outputs it in a text format.
		:param img: The image to be converted.
		:return: The string of the image.
		"""
		gray = self.grayscale(img)
		size = img.shape
		result = ""
		for y in range(size[0]):
			for x in range(size[1]):
				col = self.closest_color(img[y, x])
				bright = gray[y, x]
				if col == "":
					result += self.get_char_for_brightness(int(bright))*2
				else:
					result += f"<c{col}>{self.get_char_for_brightness(int(bright))*2}<ce>"
			result += "\n"
		return result
	
	def get_image_dimensions(self, data: str):
		height = len(data.split("\n"))-1
		width = data.split("\n")[0]
		for c in params.COLORS + [[None, "e"]]:
			if c[1] != "":
				width = width.replace(f"<c{c[1]}>", "")
		width = len(width) // 2
		return [width, height]
	
	def image_data_to_image(self, data: str):
		FONT_FACE = cv2.FONT_HERSHEY_PLAIN
		FONT_SCALE = 1.5
		PIXELS_HEIGHT = 10
		DECREASING = 2
		
		decoded = self.decode_image_data(data)
		dims = self.get_image_dimensions(decoded)
		(char_width, char_height), baseline = cv2.getTextSize("#", fontFace=FONT_FACE, fontScale=FONT_SCALE, thickness=1)
		factor = (char_height - 1) / FONT_SCALE
		font_size = PIXELS_HEIGHT / factor
		w, h = ((dims[0] - 1) * (char_height / DECREASING) * 2) + char_width, dims[1] * (char_height - 0.435)
		result = np.zeros((round(h), round(w), 3), np.uint8)

		decoded_split = decoded.split("<ce>")[:-1] # the last line is always an empty newline (\n)
		text_x = -2
		text_y = -2
		for line in decoded_split:
			arg = ""
			arg_lasts = 0
			reading_arg = False
			for c in line:
				if c == "<":
					reading_arg = True
					arg = ""
				elif c == ">":
					reading_arg = False
					arg_lasts = 2
				else:
					if reading_arg:
						arg += c
					else:
						if c == "\n":
							text_x = -2
							text_y += char_height
						else:
							color = (255, 255, 255)
							if arg != "":
								for col in params.COLORS:
									if col[1] == arg[1:]:
										color = (col[0][2], col[0][1], col[0][0])
										break
							cv2.putText(
								result, c, (round(text_x), round(text_y)),
								fontFace=FONT_FACE, fontScale=font_size, color=color, thickness=1
							)
							text_x += char_height / DECREASING
							arg_lasts -= 1
							if arg_lasts <= 0:
								arg = ""
		
		return result
	
	def encode_image_data(self, data: str):
		return binascii.hexlify(data.encode()).decode()
	
	def decode_image_data(self, data: str):
		return binascii.unhexlify(data.encode()).decode()

class Console(ImageOperation):
	opsys = "Windows"
	COLORS = {}
	REPLACEMENTS = {}
	
	def __init__(self, given_sys):
		super().__init__()
		self.opsys = given_sys
		self.COLORS = {
			"HEADER": '\033[95m',
			"OKBLUE": '\033[94m',
			"OKCYAN": '\033[96m',
			"OKGREEN": '\033[92m',
			"WARNING": '\033[93m',
			"FAIL": '\033[91m',
			"ENDC": '\033[0m',
			"BOLD": '\033[1m',
			"UNDERLINE": '\033[4m'
		}
		self.REPLACEMENTS = {
			"h": "HEADER",
			"blue": "OKBLUE",
			"cyan": "OKCYAN",
			"green": "OKGREEN",
			"warn": "WARNING",
			"fail": "FAIL",
			"e": "ENDC",
			"b": "BOLD",
			"u": "UNDERLINE",
		}
	
	def fp_info(self, fp, ignore_exist=False):
		"""
		If file exists, returns a list with the file's name, extension and location.
		Otherwise, returns None.
		:param fp: path to the file
		:param ignore_exist: Whether to ignore the fact that the file exists on the device's storage.
		:return: None | list
		"""
		if os.path.exists(fp) or ignore_exist:
			fn, fe = os.path.splitext(os.path.basename(fp))
			fd = os.path.dirname(fp)
			return [fn, fe, fd]
		else:
			return None
	
	def clear(self):
		if self.opsys == "Linux":
			os.system("clear")
		else:  # assume it's Windows
			os.system("cls")
	
	def log(self, *args, end=None):
		result = ""
		for i, arg in enumerate(args):
			if type(arg).__name__ == "str":
				for r in self.REPLACEMENTS:
					arg = arg.replace(f"<c{r}>", self.COLORS[self.REPLACEMENTS[r]])
				result += arg
			else:
				result += str(arg)
			if i != len(args):
				result += " "
		print(result, end=(end or "\n"))
	
	def formatting(self, arg, returning=False):
		if arg == "line":
			if returning:
				return f"<cfail>{'='*50}<ce>"
			else:
				self.log(f"<cfail>{'='*50}<ce>")
		elif arg == "supported_extensions":
			res = []
			for v0 in params.SUPPORTED_EXTENSIONS.keys():
				for v1 in params.SUPPORTED_EXTENSIONS[v0]:
					res.append(v1)
			return res
	
	def get(self, *args):
		return input(*args)
	
	def displayImage(self, img_data, clear=True):
		if clear:
			self.clear()
		self.log(img_data)
	
	def MainUI(self, clearing=True):
		if clearing:
			self.clear()
			self.log("<ch><cb>Video -> Text<ce>")
			self.formatting("line")
			self.log("<cblue><cb>[ Action Menu ]<ce>")
			for a in [
				["convert", "Convert image/video to text"],
				["display", f"Display a .{params.OUTPUT_EXTENSIONS['image']} or .{params.OUTPUT_EXTENSIONS['video']} file"],
				["createnew", f"Convert a .{params.OUTPUT_EXTENSIONS['image']} or .{params.OUTPUT_EXTENSIONS['video']} file to a .png | .mp4"],
				["exit", "Exit program"],
			]:
				self.log(f"<ccyan>[ {a[0]} ]<ce> - <cwarn>{a[1]}<ce>")
		self.log("<cblue>Enter action:<ce>")
		act = self.get(">")
		if act == "exit":
			return "exit"
		elif act == "convert":
			ext = self.formatting("supported_extensions")
			self.log(f"<cblue>Enter full file path (supported extensions: {' | '.join(x for x in ext)}):<ce>")
			fp = self.get(">")
			return ["convert", fp]
		elif act == "display":
			self.log(f"<cblue>Enter full file path (supported extensions: {' | '.join(x for x in list(params.OUTPUT_EXTENSIONS.values()))}):<ce>")
			fp = self.get(">")
			return ["display", fp]
		elif act == "createnew":
			self.log(f"<cblue>Enter full file path (supported extensions: {params.OUTPUT_EXTENSIONS['image']} | {params.OUTPUT_EXTENSIONS['video']}):<ce>")
			fp = self.get(">")
			return ["createnew", fp]
		return -1
	
	def InfoTopbar(self, filepath, video=None, return_string=False):
		if return_string:
			result = f"<ch><cb>Currently showing: {filepath}<ce>\n"
			if video:
				result += f"<ch>FPS: {video['fps']} | Resolution: {video['res'][0]}x{video['res'][1]}<ce>\n" \
						  f"<ch>Frame: {video['frames']['now']}/{video['frames']['total']}<ce>\n"
			result += self.formatting("line", True)
			result += "\n"
			return result
		else:
			self.log(f"<ch><cb>Currently showing: {filepath}<ce>")
			if video:
				self.log(f"<ch>FPS: {video['fps']} | Resolution: {video['res'][0]}x{video['res'][1]}<ce>")
				self.log(f"<ch>Frame: {video['frames']['now']}/{video['frames']['total']}<ce>")
			self.formatting("line")
			self.log("\n")
	
	def convert_image(self, filepath, dimensions, start_time=0.0, silent=False):
		file_info = self.fp_info(filepath)
		filetype = "image"
		img = self.read_image(filepath)
		pixelated = self.pixelize(img, dimensions[0], dimensions[1])
		pixels = self.resize(pixelated, dimensions[0], dimensions[1])
		if not silent:
			self.log("<ccyan>Converting...<ce>")
		data = self.image_to_text(pixels)
		conv_end = time.time()
		if not silent:
			self.log(f"<ccyan>Image converted in {round(conv_end - start_time, 4)}s, writing file...<ce>")
		try:
			with open(f"{file_info[2]}\\{file_info[0]}.{params.OUTPUT_EXTENSIONS[filetype]}", mode="w",
					  encoding="utf-8") as file:
				file.write(self.encode_image_data(data))
				file.close()
			if not silent:
				self.log("<cgreen>Success.<ce>")
			else:
				return f"{file_info[2]}\\{file_info[0]}.{params.OUTPUT_EXTENSIONS[filetype]}"
		except Exception as e:
			if not silent:
				self.log(f"<cfail>Unexpected error occurred:\n{e}<ce>")
			else:
				return [e]
	
	def convert_video(self, filepath, dimensions, start_time=0.0, silent=False):
		file_info = self.fp_info(filepath)
		filetype = "video"
		if not silent:
			self.log("<ccyan>Reading video capture...<ce>")
		full_data = ""
		cap = cv2.VideoCapture(filepath)
		i = 0
		while cap.isOpened():
			ret, frame = cap.read()
			if not silent:
				self.log(f"<ccyan>Converting frame {i + 1}...<ce>")
			if ret:
				pixelated = self.pixelize(frame, dimensions[0], dimensions[1])
				pixels = self.resize(pixelated, dimensions[0], dimensions[1])
				data = self.image_to_text(pixels)
				full_data += f"{self.encode_image_data(data)}\n"
			else:
				break
			i += 1
		conv_end = time.time()
		if not silent:
			self.log(f"<ccyan>All frames converted in {round(conv_end - start_time, 4)}s, writing to file...<ce>")
		fps = float(cap.get(cv2.CAP_PROP_FPS))
		full_data = f"{dimensions[0]},{dimensions[1]}|{fps}\n{full_data}"
		cap.release()
		try:
			with open(f"{file_info[2]}\\{file_info[0]}.{params.OUTPUT_EXTENSIONS[filetype]}", mode="w",
					  encoding="utf-8") as file:
				file.write(full_data)
				file.close()
			if not silent:
				self.log("<cgreen>Success.<ce>")
			else:
				return f"{file_info[2]}\\{file_info[0]}.{params.OUTPUT_EXTENSIONS[filetype]}", fps
		except Exception as e:
			if not silent:
				self.log(f"<cfail>Unexpected error occurred:\n{e}<ce>")
			else:
				return [e], None
	
	def create_image(self, in_path, out_path):
		with open(in_path, mode="r", encoding="utf-8") as file:
			result = self.image_data_to_image(file.read())
			file.close()
		cv2.imwrite(out_path, result)
	
	def edit_telegram_message(self, message, parse_mode, content): # should have async before def
		# This function is disabled due to it increasing the program's runtime.
		pass
		# await message.edit_text(
		# 	content,
		# 	parse_mode=parse_mode
		# )
	
	def video_read(self, in_path, out_path):
		with open(in_path, mode="r", encoding="utf-8") as original_file:
			data = original_file.read()
			original_file.close()
		dims, fps = map(str, data.split("\n")[0].split("|"))
		frames = data.split("\n")[1:-1]
		return dims, fps, frames
	
	def create_video(self, in_path, out_path):
		dims, fps, frames = self.video_read(in_path, out_path)
		images = []
		
		for i, frame in enumerate(frames):
			res = self.image_data_to_image(frame)
			images.append(res)
			self.log(f"<ccyan>Frame {i+1}/{len(frames)} converted...<ce>")
		first_size = images[0].shape
		
		self.log(f"<cgreen>Frames converted. Creating video file.<ce>")
		
		video_size = (first_size[1], first_size[0])
		video = cv2.VideoWriter(
			f"{out_path}", cv2.VideoWriter_fourcc(*"MP4V"),
			# found codec thanks to: https://stackoverflow.com/questions/30509573/writing-an-mp4-video-using-python-opencv
			float(fps), video_size
		)
		for i, image in enumerate(images):
			temp = cv2.resize(image,
							  video_size)  # BIG thanks to: https://stackoverflow.com/questions/53695143/python-cv2-videowriter-file-getting-corrupted
			video.write(temp)
			self.log(f"<ccyan>Frame {i+1}/{len(frames)} written...<ce>")
		video.release()
	
	def MainCycle(self):
		running = True
		next_clear = True
		while running:
			result = self.MainUI(next_clear)
			next_clear = True
			if result == "exit":
				running = False
			elif result == -1:
				self.log("<cfail>Invalid action<ce>")
				next_clear = False
			else:
				if result[0] == "convert":
					next_clear = False
					file_info = self.fp_info(result[1])
					if file_info is not None:
						filetype = None
						if file_info[1][1:] in params.SUPPORTED_EXTENSIONS["image"]:
							filetype = "image"
						elif file_info[1][1:] in params.SUPPORTED_EXTENSIONS["video"]:
							filetype = "video"
						
						if filetype is not None:
							self.log("<cblue>Enter dimensions of the output image separated with a space "
									 "(leave empty for the default 20x20).<ce>")
							dimensions = self.get(">")
							if dimensions == "":
								dimensions = (20, 20)
							else:
								dimensions = dimensions.split(" ")
								if len(dimensions) == 2:
									dimensions = (dimensions[0], dimensions[1])
									if (not dimensions[0].isdigit()) or (not dimensions[1].isdigit()):
										self.log(f"<cfail>Invalid dimensions given. Expected integers.<ce>")
										continue
									dimensions = (int(dimensions[0]), int(dimensions[1]))
									if (dimensions[0] < 1) or (dimensions[1] < 1):
										self.log(f"<cfail>Given dimensions are way too small.<ce>")
										continue
									if (dimensions[0] > 100) or (dimensions[1] > 100):
										self.log("<cwarn>Given dimensions may cause lag and extensive memory usage.<ce>")
								else:
									self.log(f"<cfail>Invalid amount of arguments given. Expected 2, got {len(dimensions)}<ce>")
									continue
							start_time = time.time()
							if filetype == "image":
								self.convert_image(result[1], dimensions, start_time)
							elif filetype == "video":
								self.convert_video(result[1], dimensions, start_time)
						else:
							ext = self.formatting("supported_extensions")
							self.log(f"<cfail>Extension {file_info[1]} is not supported. "
									 f"Supported extensions: {' | '.join(x for x in ext)}<ce>")
					else:
						self.log("<cfail>File does not exist.<ce>")
				elif result[0] == "display":
					file_info = self.fp_info(result[1])
					next_clear = False
					if file_info is not None:
						filetype = None
						if file_info[1][1:] in params.OUTPUT_EXTENSIONS["image"]:
							filetype = "image"
						elif file_info[1][1:] in params.OUTPUT_EXTENSIONS["video"]:
							filetype = "video"
						
						if filetype is not None:
							self.log("<ccyan>Fetching data...<ce>")
							if filetype == "image":
								with open(f"{result[1]}", mode="r", encoding="utf-8") as file:
									data = self.decode_image_data(file.read())
									file.close()
								self.log("<ccyan>Data fetched. Displaying.<ce>")
								
								self.clear()
								self.InfoTopbar(result[1])
								self.displayImage(data, False)
								self.log("\n<cblue>Press Enter to exit<ce>")
								self.get()
								self.clear()
								next_clear = True
							elif filetype == "video":
								with open(f"{result[1]}", mode="r", encoding="utf-8") as file:
									data = file.read()
									file.close()
								first_line = data.split("\n")[0]
								self.log("<ccyan>Data fetched. Displaying.<ce>")
								
								frames = data.split("\n")[1:-1]
								resolution = (
									int(first_line.split("|")[0].split(",")[0]),
									int(first_line.split("|")[0].split(",")[1])
								)
								fps = float(first_line.split("|")[1])
								i = 0
								while i < len(frames):
									f = frames[i]
									self.clear()
									topbar_str = self.InfoTopbar(result[1], {
										"fps": fps,
										"res": resolution,
										"frames": {
											"now": i+1,
											"total": len(frames)
										}
									}, True)
									self.log(f"{topbar_str}\n{self.decode_image_data(f)}")
									i += 1
									last_time = time.time()
									while time.time()-last_time < (1 / fps):
										pass
								self.log("<cblue>Video end\nPress Enter to exit<ce>")
								self.get()
								self.clear()
								next_clear = True
						else:
							self.log(f"<cfail>Extension {file_info[1]} is incorrect. "
									 f"Supported extensions: {params.OUTPUT_EXTENSIONS['image']} | {params.OUTPUT_EXTENSIONS['video']}<ce>")
					else:
						self.log("<cfail>File does not exist.<ce>")
				elif result[0] == "createnew":
					file_info = self.fp_info(result[1])
					next_clear = False
					if file_info is not None:
						filetype = None
						if file_info[1][1:] in params.OUTPUT_EXTENSIONS["image"]:
							filetype = "image"
						elif file_info[1][1:] in params.OUTPUT_EXTENSIONS["video"]:
							filetype = "video"
						
						if filetype is not None:
							self.log("<ccyan>Creating...<ce>")
							base_path = f"{file_info[2]}\\{file_info[0]}"
							out_path = base_path + f"_created.{params.OUTPUT_CREATENEW_EXTENSIONS[filetype]}"
							if filetype == "image":
								try:
									self.create_image(f"{base_path}{file_info[1]}", out_path)
								except Exception as e:
									self.log(f"<cfail>Unexpected error when creating a new image:\n{e}<ce>")
								else:
									self.log(f"<cgreen>Success! Image saved at:\n{out_path}<ce>")
							elif filetype == "video":
								try:
									self.create_video(f"{base_path}{file_info[1]}", out_path)
								except Exception as e:
									self.log(f"<cfail>Unexpected error when creating a new video:\n{e}<ce>")
								else:
									self.log(f"<cgreen>Success! Video saved at:\n{out_path}<ce>")
						else:
							self.log(f"<cfail>Extension {file_info[1]} is incorrect. "
									 f"Supported extensions: {params.OUTPUT_EXTENSIONS['image']} | {params.OUTPUT_EXTENSIONS['video']}<ce>")
					else:
						self.log("<cfail>File does not exist.<ce>")

cons = Console(operating_system)
if __name__ == "__main__":
	cons.MainCycle()
