import os

# 🔐 BOT TOKEN (from Railway Variables)
TOKEN = os.getenv("TOKEN")

# 📢 Logging
LOG_CHANNEL = "mod-logs"

# 👮 Staff role
STAFF_ROLE = "Staff"

# 🎫 Ticket system
TICKET_TAG = "0117"

# 👥 Auto role on join
AUTO_ROLE = "Member"

# 🚫 Automod
BAD_WORDS = ["badword1", "badword2"]
ANTI_LINK = True

# ⚡ Anti-nuke settings
ANTI_NUKE_LIMIT = 3
WHITELIST = []  # add your user ID here like: [1234567890]

# 📊 Leveling system
LEVEL_ROLES = {
    5: "Bronze",
    10: "Silver",
    20: "Gold"
}
