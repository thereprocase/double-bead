import sys
from pathlib import Path; sys.stdout.reconfigure(encoding="utf-8"); sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image
im = Image.open(str(Path(__file__).resolve().parents[2] / "review/frodo-r6/mono_samples.png"))
im.crop((0, 850, 2800, 1200)).save(str(Path(__file__).resolve().parents[2] / "review/frodo-r6/crop_codeline.png"))
