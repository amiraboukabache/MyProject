import numpy as np
import os

sequences_path = "sequences"
for gesture in sorted(os.listdir(sequences_path)):
    gesture_path = os.path.join(sequences_path, gesture)
    if not os.path.isdir(gesture_path):
        continue
    files = os.listdir(gesture_path)
    print(f"{gesture}: {len(files)} sequences")