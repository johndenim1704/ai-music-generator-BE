import enum 

class OfferStatus(enum.Enum):
    PENDING = "pending"            
    ACCEPTED = "accepted"           
    REJECTED = "rejected"          
    COUNTER_OFFERED = "counter_offered" 
    EXPIRED = "expired"             
    PAYMENT_FAILED = "payment_failed" 
    REQUIRES_ACTION = "requires_action"