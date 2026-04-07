import enum 

class OfferStatus(enum.Enum):
    PENDING = "PENDING"            
    ACCEPTED = "ACCEPTED"           
    REJECTED = "REJECTED"          
    COUNTER_OFFERED = "COUNTER_OFFERED" 
    EXPIRED = "EXPIRED"             
    PAYMENT_FAILED = "PAYMENT_FAILED" 
    REQUIRES_ACTION = "REQUIRES_ACTION"