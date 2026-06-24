import os
from dotenv import load_dotenv

load_dotenv()

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

# Admin
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
if not ADMIN_ID_RAW or not ADMIN_ID_RAW.lstrip("-").isdigit():
    raise RuntimeError("ADMIN_ID не задан или некорректен в .env")

ADMIN_ID = int(ADMIN_ID_RAW)

# Database
DATABASE_FILE = "english2.db"

# Test stages
TOTAL_STAGES = 5

# Redis or FSM Storage (используем MemoryStorage для локальной разработки)
USE_REDIS = os.getenv("USE_REDIS", "False").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Logging
LOG_FILE = "bot.log"

# Pagination
USERS_PER_PAGE = 10