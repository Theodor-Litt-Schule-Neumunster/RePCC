import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(BASE_DIR)
ROAMING_REPCC_DIR = os.path.join(os.getenv("APPDATA", ""), ".RePCC")
ROAMING_SETTINGS_DIR = os.path.join(ROAMING_REPCC_DIR, "settings")
ROAMING_DATA_DIR = os.path.join(ROAMING_REPCC_DIR, "data")
ROAMING_MACROS_DIR = os.path.join(ROAMING_REPCC_DIR, "macros")
DEFAULT_SETTINGS_DIR = os.path.join(BACKEND_DIR, "windows", "assets", "_settings")
