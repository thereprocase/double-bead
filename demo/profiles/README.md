# Demo slicer profiles

`demo/demo_plate.py` slices the coupon with the three OrcaSlicer presets in this directory:

| File | Inherits | Purpose |
| --- | --- | --- |
| `machine.json` | `Bambu Lab P1S 0.4 nozzle` | Printer, two-colour via tool change |
| `process.json` | `0.16mm Optimal @BBL X1C` | 0.2 mm first layer, 0.16 mm layers, Arachne walls |
| `filament.json` | `Bambu PLA Basic @BBL X1C` | Both colours; the script sets their colours |

They are a starting point, not the exact profile behind the committed showcase. The
point of the demo is to compare how the slicer fills the glyphs under different wall
settings, so the settings that matter are small overrides on stock presets:

| Setting | Starting value | Why |
| --- | --- | --- |
| `wall_generator` | `arachne` | Variable-width beads; `classic` shows the fixed-width contrast |
| `min_bead_width` | `50%` | Lets thin joins still get a bead |
| `initial_layer_min_bead_width` | `50%` | Same for the bed face |
| `wall_transition_angle` | `45` | Where Arachne adds or drops a bead at joins |

Override any process key per run instead of editing the files:

```sh
python demo/demo_plate.py --set wall_generator=classic --out demo/slice-classic
demo/tune.sh classic wall_generator=classic
```

`demo/tune_all.sh` runs a batch of such variants and `demo/tune_score.py` ranks them.

## Using other presets

Point `--profiles DIR` or the `FILLAPRINT_PROFILES` environment variable at a directory
with your own `machine.json`, `process.json` and `filament.json`. In OrcaSlicer, save a
user preset and export it, or copy it from the user preset folder (`user/<id>/machine`,
`process` and `filament` under OrcaSlicer's data directory). A different printer needs
its own machine preset and a process preset compatible with it; the preset names in
`inherits` must exist in your OrcaSlicer version.
