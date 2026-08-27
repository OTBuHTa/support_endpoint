from pydantic import BaseModel, Field


class QueueCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)


class QueueUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class QueueResponse(BaseModel):
    id: str
    name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class TicketCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)


class TicketCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class TicketCategoryResponse(BaseModel):
    id: str
    name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="", max_length=20)


class TagResponse(BaseModel):
    id: str
    name: str
    color: str

    model_config = {"from_attributes": True}
