import enum

class DiscountType(enum.Enum):
    PERCENT = "percent"
    FIXED_AMOUNT = "fixed_amount"


class CouponScope(enum.Enum):
    GLOBAL = "global"
    MUSIC = "music"
    LICENSE = "license"