"""Current state: marks and composites in words, at label size (scale 3) and large (scale 8)."""
from _lib import *

rows = [
    ("acute / grave / circumflex / caron / breve / tilde / macron", ["aá aà aâ aă aã aā aä aå", "eé eè eê eě eĕ eē eė eë", "ô ŏ čĉ ňñ šŝ řŕ ěê"]),
    ("vowel runs", ["áàâăãāäå éèêěĕēėëę íìîĭĩīïį óòôŏõōöőø úùûŭũūüűůų"]),
    ("caps", ["ÁÀÂĂÃĀÄÅ ÉÈÊĚĔĒĖËĘ ÍÌÎĬĨĪÏĮİ ÓÒÔŎÕŌÖŐØ ÚÙÛŬŨŪÜŰŮŲ"]),
    ("below", ["çşţșțģķļņŗ ąęįų ÇŞŢȘȚĢĶĻŅŖ ĄĘĮŲ"]),
    ("specials", ["đĐðÐħĦŧŦłŁøØæÆœŒŋŊĸıȷĳĲŉſþÞŀĿß"]),
    ("Czech", ["Příliš žluťoučký kůň úpěl ďábelské ódy"]),
    ("Slovak", ["Ľudia ľúbia ťavy, ďateľ; Ďalej šťastný ŤÝŽDEŇ"]),
    ("Hungarian", ["Árvíztűrő tükörfúrógép ŐRÜLT ŰRHAJÓ"]),
    ("Latvian", ["Ģīmeņa ķēniņš ļoti gribēja ŗūķīt dzērienu"]),
    ("Lithuanian", ["Įlinkdama fechtuotojo špaga sublykčiojusi pragręžė apvalų arbūzą"]),
    ("Turkish", ["Pijamalı hasta yağız şoföre çabucak güvendi. İĞNE ŞÖFÖR"]),
    ("Polish", ["Pchnąć w tę łódź jeża lub ośm skrzyń fig ŁÓDŹ ŻÓŁW"]),
    ("Romanian", ["Înjurând pițigăiat, zoofobul comandă vexat whisky și tequila ȘȚ"]),
    ("Icelandic", ["Kæmi ný öxi hér, ykist þjófum nú bæði víl og ádrepa. Ðað ÞÆ"]),
    ("Croatian / Maltese / Esperanto", ["Đurđevak međa Đoković; Ħamrun ħobż; ĉiuĵaŭde ŝi manĝas ĝis"]),
    ("clash", ["fí Tí Té Tý ľť ŤÝ lï fï Yí Vá Wó îl ďá ťá Ťá"]),
]
text({}, rows, "look_small.png", scale=3)
text({}, rows, "look_big.png", scale=8)
