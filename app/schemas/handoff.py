from pydantic import BaseModel, Field


class HandoffCreate(BaseModel):
    productSlug: str = Field(min_length=1, max_length=64)
    targetOrigin: str = Field(min_length=1, max_length=256)
    returnPath: str = Field(min_length=1, max_length=512)


class HandoffCreated(BaseModel):
    code: str
    expiresIn: int


class HandoffExchange(BaseModel):
    code: str = Field(min_length=20, max_length=128)
    targetOrigin: str = Field(min_length=1, max_length=256)
    returnPath: str = Field(min_length=1, max_length=512)
