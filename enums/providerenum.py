import enum

class ProviderEnum(str, enum.Enum):
    local = "local"
    google = "google"
    facebook = "facebook"