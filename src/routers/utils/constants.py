"""Define a static variable"""

# messages
REST_API_401_ERROR = "Session error."
REST_API_403_ERROR = "Forbidden error."
REST_API_429_ERROR = "Too many requests."
REST_API_500_ERROR = "Internal server error."

# session
MIN_SESSION_SECRET_KEY_LENGTH = 32
# Maximum number of chat_ids kept in the session (cookie size is limited to about 4KB)
MAX_SESSION_CHAT_IDS = 10

# input limits
# The front end limits input to 5000 "full-width" characters (half-width counts as 0.5),
# so up to 10000 half-width characters can be sent.
MAX_USER_REQUEST_LENGTH = 10000
MAX_CHAT_ID_LENGTH = 64

# rate limit of /api/ask_agent (per client address)
ASK_AGENT_RATE_LIMIT = 10
ASK_AGENT_RATE_WINDOW_SEC = 60

# Conversation history (MemorySaver) kept on the server
MAX_CHAT_THREADS = 1000
CHAT_THREAD_TTL_SEC = 24 * 60 * 60
