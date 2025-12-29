from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    platform: str = Field(default="PC", max_length=64)

class ItemUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    rating: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=500)

class ItemOut(BaseModel):
    id: int
    title: str
    platform: str
    status: str
    rating: int | None
    note: str | None

    class Config:
        from_attributes = True
