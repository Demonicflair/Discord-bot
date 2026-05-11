import os
from dotenv import load_dotenv

# Load .env file if running locally
load_dotenv()

# =========================
# 🔐 SECURE TOKENS
# =========================
# Default to None so the bot can throw a clean error if missing
TOKEN = os.getenv("TOKEN")

# =========================
# 🛡️ SECURITY & ANTI-NUKE
# =========================
# Add your ID and your trusted Co-Owners here
WHITELIST = [123456789012345678] 

# Threshold for Anti-Nuke (Actions per minute before lockdown)
ANTI_NUKE_LIMIT = 3

# =========================
# 📢 DEFAULT NAMING
# =========================
# These are used by setup_logs.py if no custom names are set
MOD_LOG_NAME = "mod-logs"
BOT_LOG_NAME = "bot-logs"
LOG_CATEGORY_NAME = "SERVER LOGS"

# =========================
# 🎫 TICKET SETTINGS
# =========================
# Unique ID for ticket naming (e.g., ticket-0117)
TICKET_TAG = "0117"
TICKET_CATEGORY_NAME = "TICKETS"

# =========================
# 📊 LEVELING SYSTEM
# =========================
# Experience gained per message
XP_PER_MESSAGE = 15

# Role Rewards
LEVEL_ROLES = {
    5: "Bronze Member",
    10: "Silver Member",
    20: "Gold Member",
    50: "Elite Member"
}

# =========================
# 👮 STAFF & ROLES
# =========================
STAFF_ROLE_NAME = "Staff"
AUTO_ROLE_NAME = "Member"

# =========================
# 🚫 AUTOMOD
# =========================
BAD_WORDS = ["badword1", "badword2"]
ANTI_LINK = True
