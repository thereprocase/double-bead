import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from beadjoint.charset import full_p
from beadjoint.sheet import grid
P = full_p()
R = str(Path(__file__).resolve().parents[2] / "review/frodo-letters")
a = "ÀÁÂÃÄÅĂĀĄÇĆČĎĐÈÉÊËĚĘĞĢĤÍÎÏĮİĴĶĹĻĽŁŃŅŇÑÓÔÕÖŐŔŘŚŞŠȘŢŤȚÚÛÜŮŰŲŴŶŸŹŻŽ"
b = "àáâãäåăāąçćčďđèéêëěęğģĥíîïįĵķĺļľłńņňñóôõöőŕřśşšșţťțúûüůűųŵŷÿźżž"
grid({c: P[c] for c in a}, fr"{R}\z_acc_caps.png", cols=12, scale=6, cell=(16, 32))
grid({c: P[c] for c in b}, fr"{R}\z_acc_low.png", cols=12, scale=6, cell=(16, 32))
