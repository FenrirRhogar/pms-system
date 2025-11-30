from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# This is a duplicated model from user-service for now
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str

# ============ TEAM MODELS ============


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    leader_id: str


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    leader_id: Optional[str] = None


class TeamMemberResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str


class TeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    leader_id: str
    created_at: str
    updated_at: str


class TeamDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    leader: UserResponse
    members: List[TeamMemberResponse]
    created_at: str
    updated_at: str


class AddMemberRequest(BaseModel):
    user_id: str
