import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"F:\code\beadjoint")
from beadjoint.charset import full_p
from beadjoint.sheet import grid
P = full_p()
R = r"F:\code\beadjoint\review\frodo-letters"
a = "ÀÁÂÃÄÅĂĀĄÇĆČĎĐÈÉÊËĚĘĞĢĤÍÎÏĮİĴĶĹĻĽŁŃŅŇÑÓÔÕÖŐŔŘŚŞŠȘŢŤȚÚÛÜŮŰŲŴŶŸŹŻŽ"
b = "àáâãäåăāąçćčďđèéêëěęğģĥíîïįĵķĺļľłńņňñóôõöőŕřśşšșţťțúûüůűųŵŷÿźżž"
grid({c: P[c] for c in a}, fr"{R}\z_acc_caps.png", cols=12, scale=6, cell=(16, 32))
grid({c: P[c] for c in b}, fr"{R}\z_acc_low.png", cols=12, scale=6, cell=(16, 32))
