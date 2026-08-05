from datetime import datetime

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FamilyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FamilyUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FamilyResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AncestorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=100)
    birth_year: str | None = None
    birth_place: str | None = None
    death_year: str | None = None
    death_place: str | None = None
    notes: str = Field(min_length=1)
    parent_ancestor_id: int | None = None
    spouse_ancestor_id: int | None = None


class AncestorUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    relation: str = Field(min_length=1, max_length=100)
    birth_year: str | None = None
    birth_place: str | None = None
    death_year: str | None = None
    death_place: str | None = None
    notes: str = Field(min_length=1)
    parent_ancestor_id: int | None = None
    spouse_ancestor_id: int | None = None


class AncestorSummaryResponse(BaseModel):
    id: int
    name: str
    relation: str
    created_at: datetime
    has_profile: bool
    parent_ancestor_id: int | None = None
    spouse_ancestor_id: int | None = None
    generation: int
    birth_year: str | None = None
    birth_place: str | None = None
    death_year: str | None = None
    death_place: str | None = None
    notes: str = ""

    model_config = {"from_attributes": True}
