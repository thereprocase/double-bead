#!/usr/bin/env bash
cd /mnt/f/code/beadjoint
demo/tune.sh gapall gap_fill_target=everywhere &
demo/tune.sh dist3 wall_distribution_count=3 &
demo/tune.sh mbw50 min_bead_width=50% initial_layer_min_bead_width=50% &
wait
demo/tune.sh wtl40 wall_transition_length=40% &
demo/tune.sh wta30 wall_transition_angle=30 &
demo/tune.sh conc top_surface_pattern=concentric bottom_surface_pattern=concentric &
wait
demo/tune.sh loops8 wall_loops=8 &
demo/tune.sh classic wall_generator=classic &
demo/tune.sh owt0 only_one_wall_top=0 &
wait
python3 demo/tune_score.py
