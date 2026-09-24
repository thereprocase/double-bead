"""Small-size views: set lines rendered at 8 px/w then downsampled (antialiased) to ~1.4 px/w."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from PIL import Image
from beadjoint.setting import mixed
from beadjoint.specimen import draw_rows

def small(rows, path, big=8, factor=3.0):
    tmp = path.replace(".png", "_big.png")
    draw_rows(rows, scale=big, path=tmp)
    im = Image.open(tmp)
    im.resize((int(im.width / factor), int(im.height / factor)), Image.LANCZOS).save(path)

if __name__ == "__main__":
    R = r"F:\code\beadjoint\review\frodo-symbols"
    t = ["5S 8B 0O 1lI| 2Z 6G 9g 4A", "‘a’ “a” 'a' ″ ′ \" ´ `", "* × x + · • . ° º ˚", "- − – — ~ ¬ ÷ ±", "¼ ½ ¾ 1/4 1/2 3/4 ¹ ² ³",
         "45% 3‰ §2 ¶ @ & © ® ™ ¤"]
    small([(s, [mixed(s)]) for s in t], fr"{R}\small_now.png")
