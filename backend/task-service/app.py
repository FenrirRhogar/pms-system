from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, engine
from db_models import Task, Comment, User, Team, Attachment
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from models import (
    UserResponse, TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse,
    CommentCreate, CommentUpdate, CommentResponse, AttachmentResponse
)
from db_models import Base
from sqlalchemy.exc import OperationalError
import time

load_dotenv()

# Retry logic for DB connection
def wait_for_db():
    retries = 0
    while retries < 30:
        try:
            with engine.connect() as connection:
                print("Database connected.")
                return
        except OperationalError:
            retries += 1
            print(f"Database not ready. Retrying {retries}/30...")
            time.sleep(2)
    raise Exception("Could not connect to database after 30 retries")

wait_for_db()

# Initialize Database Tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table creation warning (might be handled by another service): {e}")

# Initialize FastAPI
app = FastAPI(title="Task Service")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ============ HELPER FUNCTIONS ============

import httpx

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_user(user_id: str) -> UserResponse:
    if not user_id:
        return None
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://user-service:8080/api/users/{user_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return UserResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error getting user {user_id} from user-service: {e.response.text}")
        except Exception as e:
            print(f"An unexpected error occurred while fetching user {user_id}: {str(e)}")
            return None

async def get_team(team_id: str, token: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            # The token is passed as a query parameter in the team-service
            response = await client.get(f"http://team-service:8081/api/teams/{team_id}?token={token}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error getting team {team_id} from team-service: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching team {team_id}: {str(e)}")

# ============ ENDPOINTS ============

@app.get("/")
def read_root():
    return {"message": "Task Service - Welcome!"}

# ============ TASKS ENDPOINTS ============

@app.post("/api/tasks/team/{team_id}", response_model=TaskDetailResponse)
async def create_task(team_id: str, task_data: TaskCreate, token: str = None, db: Session = Depends(get_db)):
    """
    Δημιουργεί μια νέα εργασία σε ομάδα.
    Μόνο leader της ομάδας ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Get team and user info
        # Check permissions via Team Service/DB
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
             raise HTTPException(status_code=404, detail="Team not found")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
             raise HTTPException(status_code=404, detail="User not found")

        user_role = user.role.upper()
        if user_role != "TEAM_LEADER" or str(team.leader_id) != user_id:
            raise HTTPException(status_code=403, detail="Only team leader can create tasks for their team.")

        # Δημιουργία εργασίας
        new_task = Task(
            team_id=team_id,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            status="TODO",
            created_by=user_id,
            assigned_to=task_data.assigned_to,
            due_date=task_data.due_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        created_by_user = await get_user(str(new_task.created_by))
        
        assigned_to_user = None
        if new_task.assigned_to:
            assigned_to_user = await get_user(str(new_task.assigned_to))

        return TaskDetailResponse(
            id=str(new_task.id),
            team_id=str(new_task.team_id),
            title=new_task.title,
            description=new_task.description,
            status=new_task.status,
            priority=new_task.priority,
            created_by=str(new_task.created_by),
            created_by_user=created_by_user,
            assigned_to=str(new_task.assigned_to) if new_task.assigned_to else None,
            assigned_to_user=assigned_to_user,
            due_date=new_task.due_date,
            created_at=new_task.created_at,
            updated_at=new_task.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.get("/api/tasks/team/{team_id}")
async def get_team_tasks(team_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Returns tasks for a team.
    - Team leaders and admins see all tasks.
    - Members only see tasks assigned to them.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)
    
    # We can use local DB for user info since sharing DB
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        query = db.query(Task).filter(Task.team_id == team_id)

        if user.role.upper() == "MEMBER":
            query = query.filter(Task.assigned_to == user_id)

        tasks_list = query.order_by(Task.created_at.desc()).all()

        result = []
        for task in tasks_list:
            created_by_user = await get_user(str(task.created_by))
            
            assigned_to_user = None
            if task.assigned_to:
                assigned_to_user = await get_user(str(task.assigned_to))

            # Fetch comments for this task
            # Using relationship
            comments = []
            for c in task.comments:
                comment_user = await get_user(str(c.user_id))
                
                comments.append(CommentResponse(
                    id=str(c.id),
                    task_id=str(c.task_id),
                    user_id=str(c.user_id),
                    content=c.content,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                    user=comment_user
                ))

            result.append({
                "id": str(task.id),
                "team_id": str(task.team_id),
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "created_by": str(task.created_by),
                "created_by_user": created_by_user,
                "assigned_to": str(task.assigned_to) if task.assigned_to else None,
                "assigned_to_user": assigned_to_user,
                "due_date": task.due_date,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "comments": comments
            })

        return result
    except Exception as e:
        print(f"Error getting tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get tasks")

@app.get("/api/tasks/{task_id}/details", response_model=TaskDetailResponse)
async def get_task_details(task_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Get detailed information about a single task, including comments.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        # Fetch task
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Fetch users
        created_by_user = await get_user(str(task.created_by))
        assigned_to_user = await get_user(str(task.assigned_to)) if task.assigned_to else None
        
        # Fetch comments
        comments = []
        # Sort comments manually or use order_by in relationship query if needed
        # Default relationship is list, can sort in python
        sorted_comments = sorted(task.comments, key=lambda c: c.created_at, reverse=True)
        
        for c in sorted_comments:
            comment_user = await get_user(str(c.user_id))
            
            comments.append(CommentResponse(
                id=str(c.id),
                task_id=str(c.task_id),
                user_id=str(c.user_id),
                content=c.content,
                created_at=c.created_at,
                updated_at=c.updated_at,
                user=comment_user
            ))

        # Fetch attachments
        attachments = []
        for att in task.attachments:
            attachments.append(AttachmentResponse(
                id=str(att.id),
                task_id=str(att.task_id),
                uploader_id=str(att.uploader_id),
                filename=att.filename,
                file_path=att.file_path,
                created_at=att.created_at
            ))

        return TaskDetailResponse(
            id=str(task.id),
            team_id=str(task.team_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            created_by=str(task.created_by),
            created_by_user=created_by_user,
            assigned_to=str(task.assigned_to) if task.assigned_to else None,
            assigned_to_user=assigned_to_user,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            comments=comments,
            attachments=attachments
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching task details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch task details")


@app.patch("/api/tasks/{task_id}", response_model=TaskDetailResponse)
async def update_task(task_id: str, task_data: TaskUpdate, token: str = None, db: Session = Depends(get_db)):
    """
    Ενημερώνει μια εργασία.
    Μόνο leader της ομάδας ή ο assigned user ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε την εργασία
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get team and user info
        # We can check team leader via DB
        team = db.query(Team).filter(Team.id == task.team_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        user_role = user.role.upper()
        
        is_team_leader = (team and str(team.leader_id) == user_id)
        is_assigned_member = (str(task.assigned_to) == user_id)

        if is_team_leader:
            can_update = True
        elif is_assigned_member:
            # Assigned member can only change status
            # Check if any field other than status is being updated
            other_fields_being_updated = False
            if task_data.title is not None and task_data.title != task.title: other_fields_being_updated = True
            if task_data.description is not None and task_data.description != task.description: other_fields_being_updated = True
            if task_data.priority is not None and task_data.priority != task.priority: other_fields_being_updated = True
            if task_data.assigned_to is not None and str(task_data.assigned_to) != str(task.assigned_to or ""): other_fields_being_updated = True
            # Note: assigned_to logic is a bit brittle with None handling, but roughly correct
            if task_data.due_date is not None and task_data.due_date != task.due_date: other_fields_being_updated = True

            if other_fields_being_updated:
                raise HTTPException(status_code=403, detail="Assigned members can only change task status.")
            
            can_update = True # Allowed to update status, or if no changes were made.
        else:
            can_update = False # Neither leader nor assigned member


        if not can_update:
            raise HTTPException(status_code=403, detail="Not allowed to update this task")

        # Ενημέρωση
        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.status is not None:
            task.status = task_data.status
        if task_data.priority is not None:
            task.priority = task_data.priority
        if task_data.due_date is not None:
            task.due_date = task_data.due_date
        if task_data.assigned_to is not None:
            task.assigned_to = task_data.assigned_to

        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)

        created_by_user = await get_user(str(task.created_by))
        
        assigned_to_user = None
        if task.assigned_to:
            assigned_to_user = await get_user(str(task.assigned_to))

        return TaskDetailResponse(
            id=str(task.id),
            team_id=str(task.team_id),
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            created_by=str(task.created_by),
            created_by_user=created_by_user,
            assigned_to=str(task.assigned_to) if task.assigned_to else None,
            assigned_to_user=assigned_to_user,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Διαγράφει μια εργασία.
    Μόνο leader της ομάδας ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε την εργασία
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Get team and user info
        team = db.query(Team).filter(Team.id == task.team_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        user_role = user.role.upper()
        can_delete = (team and str(team.leader_id) == user_id) # Only Team Leader can delete

        if not can_delete:
            raise HTTPException(status_code=403, detail="Only team leader can delete tasks.")

        # Διαγραφή
        db.delete(task)
        db.commit()

        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

# ============ COMMENTS ENDPOINTS ============

@app.post("/api/comments/task/{task_id}", response_model=CommentResponse)
async def create_comment(task_id: str, comment_data: CommentCreate, token: str = None, db: Session = Depends(get_db)):
    """
    Δημιουργεί ένα νέο σχόλιο σε μια εργασία.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η εργασία
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Δημιουργία σχολίου
        new_comment = Comment(
            task_id=task_id,
            user_id=user_id,
            content=comment_data.content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)

        user_info = await get_user(str(new_comment.user_id))

        return CommentResponse(
            id=str(new_comment.id),
            task_id=str(new_comment.task_id),
            user_id=str(new_comment.user_id),
            user=user_info,
            content=new_comment.content,
            created_at=new_comment.created_at,
            updated_at=new_comment.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.get("/api/comments/task/{task_id}")
async def get_task_comments(task_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Επιστρέφει όλα τα σχόλια μιας εργασίας.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        comments = db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.created_at.asc()).all()

        result = []
        for comment in comments:
            user_info = await get_user(str(comment.user_id))

            result.append({
                "id": str(comment.id),
                "task_id": str(comment.task_id),
                "user_id": str(comment.user_id),
                "user": user_info,
                "content": comment.content,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at
            })

        return result
    except Exception as e:
        print(f"Error getting comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@app.patch("/api/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(comment_id: str, comment_data: CommentUpdate, token: str = None, db: Session = Depends(get_db)):
    """
    Ενημερώνει ένα σχόλιο.
    Μόνο ο συγγραφέας του ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε το σχόλιο
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        # Έλεγχος δικαιωμάτων
        if str(comment.user_id) != user_id:
            user = await get_user(user_id)
            if user.role.upper() != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to update this comment")

        # Ενημέρωση
        comment.content = comment_data.content
        comment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(comment)

        user_info = await get_user(str(comment.user_id))

        return CommentResponse(
            id=str(comment.id),
            task_id=str(comment.task_id),
            user_id=str(comment.user_id),
            user=user_info,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update comment")


@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Διαγράφει ένα σχόλιο.
    Μόνο ο συγγραφέας του ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε το σχόλιο
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        # Έλεγχος δικαιωμάτων
        if str(comment.user_id) != user_id:
            user = await get_user(user_id)
            if user.role.upper() != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

        # Διαγραφή
        db.delete(comment)
        db.commit()

        return {"message": "Comment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")

# ============ ATTACHMENTS ENDPOINTS ============

@app.post("/api/tasks/{task_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(
    task_id: str,
    file: UploadFile = File(...),
    token: str = None,
    db: Session = Depends(get_db)
):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Verify task existence
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Generate unique filename to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_location = UPLOAD_DIR / safe_filename
        
        # Save file to disk
        with file_location.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Save metadata to DB
        attachment = Attachment(
            task_id=task_id,
            uploader_id=user_id,
            filename=file.filename,
            file_path=str(file_location),
            created_at=datetime.utcnow()
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        return AttachmentResponse(
            id=str(attachment.id),
            task_id=str(attachment.task_id),
            uploader_id=str(attachment.uploader_id),
            filename=attachment.filename,
            file_path=attachment.file_path,
            created_at=attachment.created_at
        )
    except Exception as e:
        db.rollback()
        print(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/api/attachments/{attachment_id}/download")
async def download_attachment(attachment_id: str, token: str = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    verify_token(token)
    
    try:
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
            
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on server")
            
        return FileResponse(
            path=file_path,
            filename=attachment.filename,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to download file")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
