from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class MembershipResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    role_name: str
