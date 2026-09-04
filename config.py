import os

# Base project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory to store browser persistent profiles
USER_DATA_DIR = os.path.join(BASE_DIR, ".user_data")

TWITTER_USER_DATA = os.path.join(USER_DATA_DIR, "twitter")
FACEBOOK_USER_DATA = os.path.join(USER_DATA_DIR, "facebook")

# Ensure directories exist
os.makedirs(TWITTER_USER_DATA, exist_ok=True)
os.makedirs(FACEBOOK_USER_DATA, exist_ok=True)

# Cleanup pacing (delays in seconds between deletions/actions)
# Default set to Moderate (1.5 - 2.5s)
DEFAULT_MIN_DELAY = 1.5
DEFAULT_MAX_DELAY = 2.5

# Periodic page refresh interval (in seconds) to prevent Twitter UI sticking / memory issues
PAGE_REFRESH_INTERVAL = 120  # 2 minutes

