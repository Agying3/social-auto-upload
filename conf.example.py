import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = Path(os.environ.get("TUJUE_AUTOSEND_DATA_DIR") or Path(os.environ.get("APPDATA", BASE_DIR)) / "TujueAutoSend")
XHS_SERVER = "http://127.0.0.1:11901"  # only used by xhs-related flows
LOCAL_CHROME_PATH = ""  # optional, e.g. C:/Program Files/Google/Chrome/Application/chrome.exe
LOCAL_CHROME_HEADLESS = True  # default headless behavior for uploader/examples
DEBUG_MODE = True  # default debug behavior
