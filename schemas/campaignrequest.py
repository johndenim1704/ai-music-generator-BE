from pydantic import BaseModel

class CampaignRequest(BaseModel):
    campaign_name: str
    subject: str
    html_content: str