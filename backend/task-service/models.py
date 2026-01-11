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

# ============ COMMENTS ============

class CommentCreate(BaseModel):
    content: str

class CommentUpdate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: str
    task_id: str
    user_id: str
    user: Optional[UserResponse] = None
    content: str
    created_at: datetime
    updated_at: datetime

# ============ ATTACHMENTS ============

class AttachmentResponse(BaseModel):
    id: str
    task_id: str
    uploader_id: str
    filename: str
    file_path: str
    created_at: datetime

# ============ TASKS ============

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'MEDIUM'  # LOW, MEDIUM, HIGH, URGENT
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None  # user_id
    team_id: str # Added team_id

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
    created_by_user: Optional[UserResponse] = None
    assigned_to: Optional[str]
    assigned_to_user: Optional[UserResponse] = None
    due_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    comments: Optional[List[CommentResponse]] = []
    attachments: Optional[List[AttachmentResponse]] = []