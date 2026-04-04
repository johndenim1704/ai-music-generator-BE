import enum

class OrderStatus(enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class OrderOrigin(enum.Enum):
    DIRECT_PURCHASE = "DIRECT_PURCHASE"
    ACCEPTED_OFFER = "ACCEPTED_OFFER"