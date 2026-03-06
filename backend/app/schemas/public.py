from pydantic import BaseModel, EmailStr, Field


class PublicDemoStreamRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=36)
    channel: str = Field(default="public-demo", max_length=32)


class PublicMarketingLeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    email: EmailStr
    company: str | None = Field(default=None, max_length=140)
    message: str = Field(min_length=8, max_length=3000)


class PublicMarketingLeadResponse(BaseModel):
    lead_id: str
    conversation_id: str
    status: str
    message: str
