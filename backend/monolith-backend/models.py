from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ============ USER MODELS ============


class UserSignUp(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


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


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'MEDIUM'  # LOW, MEDIUM, HIGH, URGENT
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None  # user_id

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # TODO, IN_PROGRESS, COMPLETED, ON_HOLD
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    team_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    created_by: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class TaskDetailResponse(BaseModel):
    id: str
    team_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    created_by: str
    created_by_user: UserResponse  # full user object
    assigned_to: Optional[str]
    assigned_to_user: Optional[UserResponse]  # full user object if assigned
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ============ TASKS ============

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'MEDIUM'  # LOW, MEDIUM, HIGH, URGENT
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None  # user_id

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # TODO, IN_PROGRESS, COMPLETED, ON_HOLD
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    team_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    created_by: str
    assigned_to: Optional[str]
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class TaskDetailResponse(BaseModel):
    id: str
    team_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    created_by: str
    created_by_user: Optional['UserResponse'] = None
    assigned_to: Optional[str]
    assigned_to_user: Optional['UserResponse'] = None
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

# ============ COMMENTS ============

class CommentCreate(BaseModel):
    content: str

class CommentUpdate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user: Optional['UserResponse'] = None
    content: str
    created_at: datetime
    updated_at: datetime