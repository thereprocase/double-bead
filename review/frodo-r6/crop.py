import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image
im = Image.open(r"F:\code\beadjoint\review\frodo-r6\mono_samples.png")
im.crop((0, 20, 1700, 390)).save(r"F:\code\beadjoint\review\frodo-r6\crop_row1.png")
