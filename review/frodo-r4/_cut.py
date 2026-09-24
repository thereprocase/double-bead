import sys
from PIL import Image
src, n = sys.argv[1], int(sys.argv[2])
im = Image.open(src)
h = im.height // n
for i in range(n):
    im.crop((0, i * h, im.width, min(im.height, (i + 1) * h))).save(src.replace(".png", f"_part{i}.png"))
print(im.size)
