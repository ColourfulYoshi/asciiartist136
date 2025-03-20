def translate(v, lmin, lmax, rmin, rmax):
    lspan = lmax - lmin
    rspan = rmax - rmin
    scaled = float(v - lmin) / float(lspan)
    return rmin + (scaled * rspan)

SUPPORTED_EXTENSIONS = {
	"image": ["png", "jpg", "jpeg"],
	"video": ["mp4", "avi", "mov"]
}
OUTPUT_EXTENSIONS = {
	"image": "ittcf", # Image To Text Conversion Format
	"video": "vttcf" # Video To Text Conversion Format
}
OUTPUT_CREATENEW_EXTENSIONS = {
	"image": "png",
	"video": "mp4"
}

SYMBOLS = "#@0O=-"

COLORS = [
	[(237, 126, 237), "h"],
	[(255, 64, 80), "fail"],
	[(33, 175, 255), "blue"],
	[(11, 228, 226), "cyan"],
	[(77, 195, 25), "green"],
	[(228, 190, 12), "warn"],
	[(255, 255, 255), ""],
	[(127, 127, 127), ""],
	[(0, 0, 0), ""]
]

X_LIMIT = 125
Y_LIMIT = 125
