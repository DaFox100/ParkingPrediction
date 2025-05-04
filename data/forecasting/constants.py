from pathlib import Path

# Get the data (root of this module) directory
# This logic needs to be updated if the module is moved to a different directory
DATA_DIR = Path(__file__).resolve().parent.parent # -> Forecasting -> data

# ── DIRECTORIES ───────────────────────────────────────────────────────────────────
LOGS_DIRECTORY = DATA_DIR / "records"
MODEL_DIRECTORY = DATA_DIR / "forecasting" / "keras_models"
EVENTS_DIRECTORY = DATA_DIR / "events"

# ── CONSTANTS ───────────────────────────────────────────────────────────────────
GARAGE_NAMES = ["south", "west", "north", "south_campus"]


# ── TRAINING CONSTANTS ───────────────────────────────────────────────────────────
# Define parameters for long model
LONG_SEQ = 8
LONG_FUTURE_STEPS = 196

# Define parameters for short model
SHORT_SEQ = 16
SHORT_FUTURE_STEPS = 16

ENABLE_TIME_ENCODING: bool          = True
ENABLE_INSTR_DAY: bool              = True
ENABLE_INSTR_NEXT_DAY: bool         = True
ENABLE_EVENT_ENCODING: bool         = True