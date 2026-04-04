from pydantic import BaseModel

class TitleRequest(BaseModel):
    audio_url: str
    genre: str
    num_titles: int = 1

class TitleResponse(BaseModel):
    titles: str
