#!/usr/bin/env bash
cd "$(dirname "$0")/.."
demo/tune.sh m50a30 min_bead_width=50% initial_layer_min_bead_width=50% wall_transition_angle=30 &
demo/tune.sh m40 min_bead_width=40% initial_layer_min_bead_width=40% &
demo/tune.sh m40a30 min_bead_width=40% initial_layer_min_bead_width=40% wall_transition_angle=30 &
wait
demo/tune.sh m30a30 min_bead_width=30% initial_layer_min_bead_width=30% wall_transition_angle=30 &
demo/tune.sh m50a45 min_bead_width=50% initial_layer_min_bead_width=50% wall_transition_angle=45 &
demo/tune.sh m50a30f10 min_bead_width=50% initial_layer_min_bead_width=50% wall_transition_angle=30 min_feature_size=10% &
wait
python3 demo/tune_score.py
