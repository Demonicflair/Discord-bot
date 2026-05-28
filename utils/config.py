import os

from dotenv import load_dotenv

load_dotenv()

# =========================
# BOT CONFIG
# =========================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError(
        "TOKEN missing in environment variables."
    )

PREFIX = "!"

# =========================
# BRANDING
# =========================

BRAND_COLOR = 0x2B2D31

BOT_NAME = "Dem Security"

# =========================
# SECURITY
# =========================

WHITELIST = {
    123456789012345678
}

ANTI_NUKE_LIMIT = 3

SCAM_PATTERN = (
    r"(free.*nitro|"
    r"nitro.*free|"
    r"steam.*gift|"
    r"claim.*reward|"
    r"discord.*gift)"
)

BAD_WORDS = {
    "badword1",
    "badword2"
}

ANTI_LINK = True

# =========================
# LOGGING
# =========================

MOD_LOG_NAME = "mod-logs"

BOT_LOG_NAME = "bot-logs"

LOG_CATEGORY_NAME = "SERVER LOGS"

# =========================
# TICKETS
# =========================

TICKET_CATEGORY_NAME = "TICKETS"

TICKET_TAG = "0117"

# =========================
# LEVELING
# =========================

XP_PER_MESSAGE = 15

LEVEL_ROLES = {
    5: "Bronze Member",
    10: "Silver Member",
    20: "Gold Member",
    50: "Elite Member"
}

# =========================
# STAFF
# =========================

STAFF_ROLE_NAME = "Staff"

AUTO_ROLE_NAME = "Member"

# =========================
# RAILWAY
# =========================

RAILWAY_ENVIRONMENT = os.getenv(
    "RAILWAY_ENVIRONMENT",
    "LOCAL"
)

IS_RAILWAY = bool(
    os.getenv("RAILWAY_ENVIRONMENT")
)
