import logging
import os
from datetime import datetime
from collections import deque
from typing import List, Dict

# Configuration
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
MAX_MEMORY_LOGS = 1000  # Number of recent logs to keep in memory

# Ensure log directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("api_logger")

# In-memory storage for real-time log viewing (e.g., for a "logs.tsx" component)
recent_logs = deque(maxlen=MAX_MEMORY_LOGS)

def log_event(level: str, message: str, extra: Dict = None):
    """
    Log an event to file and in-memory buffer
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "message": message,
        "extra": extra or {}
    }
    
    # Add to in-memory buffer
    recent_logs.append(log_entry)
    
    # Log to standard logger
    if level.lower() == "info":
        logger.info(f"{message} | Extra: {extra}")
    elif level.lower() == "error":
        logger.error(f"{message} | Extra: {extra}")
    elif level.lower() == "warn" or level.lower() == "warning":
        logger.warning(f"{message} | Extra: {extra}")
    else:
        logger.debug(f"{message} | Extra: {extra}")

def get_recent_logs(limit: int = 100) -> List[Dict]:
    """
    Retrieve the most recent logs
    """
    logs_list = list(recent_logs)
    return logs_list[-limit:]
