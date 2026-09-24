import sys; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image
im = Image.open(r"F:\code\beadjoint\review\frodo-r6\mono_samples.png")
im.crop((600, 20, 1900, 390)).save(r"F:\code\beadjoint\review\frodo-r6\crop_0O1Il_v2.png")
