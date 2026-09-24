import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image
im = Image.open(r"F:\code\beadjoint\review\frodo-r6\mono_samples.png")
print(im.size)
# rows: aligned numbers 1/2/3 around y ~1700-2650 based on original 2800x4645 image, row pitch ~ (12*28+8)*10+... let's just crop generously
im.crop((0, 1650, 1300, 2650)).save(r"F:\code\beadjoint\review\frodo-r6\crop_numbers.png")
im.crop((0, 400, 2600, 780)).save(r"F:\code\beadjoint\review\frodo-r6\crop_code.png")
im.crop((0, 1150, 2400, 1600)).save(r"F:\code\beadjoint\review\frodo-r6\crop_path.png")
