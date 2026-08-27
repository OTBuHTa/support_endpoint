from pydantic import BaseModel, Field


class ClientOrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=5000)


class ClientOrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class ClientOrganizationResponse(BaseModel):
    id: str
    name: str
    domain: str
    notes: str
    is_active: bool

    model_config = {"from_attributes": True}


class ClientContactCreateRequest(BaseModel):
    label: str = Field(default="", max_length=100)
    channel_type: str = Field(default="email", pattern="^(email|phone|other)$")
    value: str = Field(min_length=1, max_length=255)


class ClientContactResponse(BaseModel):
    id: str
    client_id: str
    label: str
    channel_type: str
    value: str

    model_config = {"from_attributes": True}


class ClientCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    primary_email: str = Field(default="", max_length=255)
    primary_phone: str = Field(default="", max_length=64)
    organization_id: str | None = None
    notes: str = Field(default="", max_length=5000)


class ClientUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    primary_email: str | None = Field(default=None, max_length=255)
    primary_phone: str | None = Field(default=None, max_length=64)
    organization_id: str | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class ClientResponse(BaseModel):
    id: str
    full_name: str
    primary_email: str
    primary_phone: str
    organization_id: str | None
    notes: str
    is_active: bool

    model_config = {"from_attributes": True}


class ClientOrganizationListResponse(BaseModel):
    items: list[ClientOrganizationResponse]
    total: int
    limit: int
    offset: int


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    limit: int
    offset: int
