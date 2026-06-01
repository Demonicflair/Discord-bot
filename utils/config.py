# utils/config.py

import os
import re

from dotenv import load_dotenv

load_dotenv()

# ==================================================
# BOT CONFIG
# ==================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError(
        "TOKEN missing from environment variables."
    )

PREFIX = os.getenv(
    "PREFIX",
    "!"
)

BOT_NAME = os.getenv(
    "BOT_NAME",
    "Dem Security"
)

# ==================================================
# DATABASE
# SINGLE DATABASE SYSTEM
# ==================================================

DB_PATH = os.getenv(
    "DB_PATH",
    "dem.db"
)

# ==================================================
# COLORS
# ==================================================

BRAND_COLOR = 0x2B2D31

SUCCESS_COLOR = 0x57F287
ERROR_COLOR = 0xED4245
WARNING_COLOR = 0xFEE75C

# ==================================================
# RAILWAY
# ==================================================

IS_RAILWAY = bool(
    os.getenv(
        "RAILWAY_ENVIRONMENT"
    )
)

# ==================================================
# SECURITY
# ==================================================

WHITELIST = set()

ANTI_NUKE_LIMIT = int(
    os.getenv(
        "ANTI_NUKE_LIMIT",
        3
    )
)

BAD_WORDS = {

    "badword1",
    "badword2"

}

ANTI_LINK = os.getenv(
    "ANTI_LINK",
    "true"
).lower() == "true"

SCAM_PATTERN = re.compile(

    r"(free.*nitro|"
    r"nitro.*free|"
    r"steam.*gift|"
    r"claim.*reward|"
    r"discord.*gift)",

    re.IGNORECASE

)

# ==================================================
# LOGGING
# ==================================================

MOD_LOG_NAME = "mod-logs"

BOT_LOG_NAME = "bot-logs"

LOG_CATEGORY_NAME = "SERVER LOGS"

# ==================================================
# TICKETS
# ==================================================

TICKET_CATEGORY_NAME = "TICKETS"

TICKET_TAG = os.getenv(
    "TICKET_TAG",
    "0117"
)

# ==================================================
# LEVELING
# ==================================================

XP_PER_MESSAGE = int(
    os.getenv(
        "XP_PER_MESSAGE",
        15
    )
)

LEVEL_ROLES = {

    5: "Bronze Member",
    10: "Silver Member",
    20: "Gold Member",
    50: "Elite Member"

}

# ==================================================
# STAFF / AUTO ROLE
# ==================================================

STAFF_ROLE_NAME = "Staff"

AUTO_ROLE_NAME = "Member"
