from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize the Limiter with IP-based rate limiting
# key_func=get_remote_address uses the client's IP address as the identifier
limiter = Limiter(key_func=get_remote_address)
