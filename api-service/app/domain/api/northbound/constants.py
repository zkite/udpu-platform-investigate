from datetime import timedelta


STATUS_PREFIX = "STATUS"
UDPU_ENTITY = "UDPU"
MAC_ADDRESS_KEY = "MA"
PPPOE_ENTITY = "PPPOE"

MAC_ADDRESS_REGEX = "[0-9a-fA-F]{2}([-:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$"

DATE_TIME_FORMAT = "%a, %b %d, %Y %H:%M:%S %p %Z"

CONTEXT_KEY_PREFIX = "udpu_context"
LOCATION_PREFIX = "udpu_location"


OFFLINE_THRESHOLD = timedelta(seconds=10)