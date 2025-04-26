from pathlib import Path

# Get the data (root of this module) directory
# This logic needs to be updated if the module is moved to a different directory
DATA_DIR = Path(__file__).resolve().parent.parent # -> Forecasting -> data

# ── DIRECTORIES ───────────────────────────────────────────────────────────────────
LOGS_DIRECTORY = DATA_DIR / "Records"
MODEL_DIRECTORY = DATA_DIR / "Forcasting" / "keras_models"


# ── CONSTANTS ───────────────────────────────────────────────────────────────────
GARAGE_NAMES = ["south", "west", "north", "south_campus"]


# ── TRAINING CONSTANTS ───────────────────────────────────────────────────────────
# Define parameters for long model
LONG_SEQ = 8
LONG_FUTURE_STEPS = 128

# Define parameters for short model
SHORT_SEQ = 16
SHORT_FUTURE_STEPS = 16

