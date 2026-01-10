from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from models import (
    UserResponse, TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse,
    CommentCreate, CommentUpdate, CommentResponse
)

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Task Service")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Supabase Admin Client (for RLS bypass)
supabase_admin: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"

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
async def create_task(team_id: str, task_data: TaskCreate, token: str = None):
    """
    Δημιουργεί μια νέα εργασία σε ομάδα.
    Μόνο leader της ομάδας ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Get team and user info
        team = await get_team(team_id, token)
        user = await get_user(user_id)

        user_role = user.role.upper()
        if user_role != "TEAM_LEADER" or team["leader"]["id"] != user_id:
            raise HTTPException(status_code=403, detail="Only team leader can create tasks for their team.")

        # Δημιουργία εργασίας
        task_insert = supabase_admin.table("tasks").insert({
            "team_id": team_id,
            "title": task_data.title,
            "description": task_data.description,
            "priority": task_data.priority,
            "status": "TODO",
            "created_by": user_id,
            "assigned_to": task_data.assigned_to,
            "due_date": task_data.due_date.isoformat() if task_data.due_date else None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        if not task_insert.data:
            raise HTTPException(status_code=400, detail="Failed to create task")

        task = task_insert.data[0]

        created_by_user = await get_user(task["created_by"])
        
        assigned_to_user = None
        if task["assigned_to"]:
            assigned_to_user = await get_user(task["assigned_to"])

        return TaskDetailResponse(
            id=task["id"],
            team_id=task["team_id"],
            title=task["title"],
            description=task["description"],
            status=task["status"],
            priority=task["priority"],
            created_by=task["created_by"],
            created_by_user=created_by_user,
            assigned_to=task["assigned_to"],
            assigned_to_user=assigned_to_user,
            due_date=task["due_date"],
            created_at=task["created_at"],
            updated_at=task["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.get("/api/tasks/team/{team_id}")
async def get_team_tasks(team_id: str, token: str = None):
    """
    Returns tasks for a team.
    - Team leaders and admins see all tasks.
    - Members only see tasks assigned to them.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)
    user = await get_user(user_id)

    try:
        query = supabase_admin.table("tasks").select("*").eq("team_id", team_id)

        if user.role.upper() == "MEMBER":
            query = query.eq("assigned_to", user_id)

        tasks_resp = query.order("created_at", desc=True).execute()

        tasks = []
        for task in (tasks_resp.data or []):
            created_by_user = await get_user(task["created_by"])
            
            assigned_to_user = None
            if task["assigned_to"]:
                assigned_to_user = await get_user(task["assigned_to"])

            # Fetch comments for this task
            comments_resp = supabase_admin.table("task_comments").select("*, user:users(*)").eq("task_id", task["id"]).order("created_at", desc=False).execute()
            comments = []
            for c in (comments_resp.data or []):
                user_data = None
                if c.get("user"):
                    user_data = UserResponse(**c["user"])
                
                comments.append(CommentResponse(
                    id=c["id"],
                    task_id=c["task_id"],
                    user_id=c["user_id"],
                    content=c["content"],
                    created_at=c["created_at"],
                    updated_at=c["updated_at"],
                    user=user_data
                ))

            tasks.append({
                "id": task["id"],
                "team_id": task["team_id"],
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
                "priority": task["priority"],
                "created_by": task["created_by"],
                "created_by_user": created_by_user,
                "assigned_to": task["assigned_to"],
                "assigned_to_user": assigned_to_user,
                "due_date": task["due_date"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "comments": comments
            })

        return tasks
    except Exception as e:
        print(f"Error getting tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get tasks")

@app.get("/api/tasks/{task_id}/details", response_model=TaskDetailResponse)
async def get_task_details(task_id: str, token: str = None):
    """
    Get detailed information about a single task, including comments.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        # Fetch task
        task_resp = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")
        task = task_resp.data[0]

        # Fetch users
        created_by_user = await get_user(task["created_by"])
        assigned_to_user = await get_user(task["assigned_to"]) if task["assigned_to"] else None
        
        # Fetch comments
        comments_resp = supabase_admin.table("task_comments").select("*, user:users(*)").eq("task_id", task_id).order("created_at", desc=True).execute()
        comments = []
        for c in (comments_resp.data or []):
            user_data = None
            if c.get("user"):
                user_data = UserResponse(**c["user"])
            
            comments.append(CommentResponse(
                id=c["id"],
                task_id=c["task_id"],
                user_id=c["user_id"],
                content=c["content"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                user=user_data
            ))


        return TaskDetailResponse(
            id=task["id"],
            team_id=task["team_id"],
            title=task["title"],
            description=task["description"],
            status=task["status"],
            priority=task["priority"],
            created_by=task["created_by"],
            created_by_user=created_by_user,
            assigned_to=task["assigned_to"],
            assigned_to_user=assigned_to_user,
            due_date=task["due_date"],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            comments=comments
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching task details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch task details")


@app.patch("/api/tasks/{task_id}", response_model=TaskDetailResponse)
async def update_task(task_id: str, task_data: TaskUpdate, token: str = None):
    """
    Ενημερώνει μια εργασία.
    Μόνο leader της ομάδας ή ο assigned user ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε την εργασία
        task_resp = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_resp.data[0]

        # Get team and user info
        team = await get_team(task["team_id"], token)
        user = await get_user(user_id)

        user_role = user.role.upper()
        
        is_team_leader = (team and team["leader"]["id"] == user_id)
        is_assigned_member = (task["assigned_to"] == user_id)

        if is_team_leader:
            can_update = True
        elif is_assigned_member:
            # Assigned member can only change status
            # Check if any field other than status is being updated
            other_fields_being_updated = False
            if task_data.title is not None and task_data.title != task["title"]: other_fields_being_updated = True
            if task_data.description is not None and task_data.description != task["description"]: other_fields_being_updated = True
            if task_data.priority is not None and task_data.priority != task["priority"]: other_fields_being_updated = True
            if task_data.assigned_to is not None and task_data.assigned_to != task["assigned_to"]: other_fields_being_updated = True
            if task_data.due_date is not None and task_data.due_date != task["due_date"]: other_fields_being_updated = True

            if other_fields_being_updated:
                raise HTTPException(status_code=403, detail="Assigned members can only change task status.")
            
            can_update = True # Allowed to update status, or if no changes were made.
        else:
            can_update = False # Neither leader nor assigned member


        if not can_update:
            raise HTTPException(status_code=403, detail="Not allowed to update this task")

        # Ενημέρωση
        update_data = {}
        if task_data.title is not None:
            update_data["title"] = task_data.title
        if task_data.description is not None:
            update_data["description"] = task_data.description
        if task_data.status is not None:
            update_data["status"] = task_data.status
        if task_data.priority is not None:
            update_data["priority"] = task_data.priority
        if task_data.due_date is not None:
            update_data["due_date"] = task_data.due_date.isoformat()
        if task_data.assigned_to is not None:
            update_data["assigned_to"] = task_data.assigned_to

        update_data["updated_at"] = datetime.utcnow().isoformat()

        updated_resp = supabase_admin.table("tasks").update(update_data).eq("id", task_id).execute()

        if not updated_resp.data:
            raise HTTPException(status_code=400, detail="Failed to update task")

        updated_task = updated_resp.data[0]

        created_by_user = await get_user(updated_task["created_by"])
        
        assigned_to_user = None
        if updated_task["assigned_to"]:
            assigned_to_user = await get_user(updated_task["assigned_to"])

        return TaskDetailResponse(
            id=updated_task["id"],
            team_id=updated_task["team_id"],
            title=updated_task["title"],
            description=updated_task["description"],
            status=updated_task["status"],
            priority=updated_task["priority"],
            created_by=updated_task["created_by"],
            created_by_user=created_by_user,
            assigned_to=updated_task["assigned_to"],
            assigned_to_user=assigned_to_user,
            due_date=updated_task["due_date"],
            created_at=updated_task["created_at"],
            updated_at=updated_task["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, token: str = None):
    """
    Διαγράφει μια εργασία.
    Μόνο leader της ομάδας ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε την εργασία
        task_resp = supabase_admin.table("tasks").select("*").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_resp.data[0]

        # Get team and user info
        team = await get_team(task["team_id"], token)
        user = await get_user(user_id)

        user_role = user.role.upper()
        can_delete = (team and team["leader"]["id"] == user_id) # Only Team Leader can delete

        if not can_delete:
            raise HTTPException(status_code=403, detail="Only team leader can delete tasks.")

        # Διαγραφή
        supabase_admin.table("tasks").delete().eq("id", task_id).execute()

        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

# ============ COMMENTS ENDPOINTS ============

@app.post("/api/comments/task/{task_id}", response_model=CommentResponse)
async def create_comment(task_id: str, comment_data: CommentCreate, token: str = None):
    """
    Δημιουργεί ένα νέο σχόλιο σε μια εργασία.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η εργασία
        task_resp = supabase_admin.table("tasks").select("id").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        # Δημιουργία σχολίου
        comment_insert = supabase_admin.table("task_comments").insert({
            "task_id": task_id,
            "user_id": user_id,
            "content": comment_data.content,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        if not comment_insert.data:
            raise HTTPException(status_code=400, detail="Failed to create comment")

        comment = comment_insert.data[0]

        user_info = await get_user(comment["user_id"])

        return CommentResponse(
            id=comment["id"],
            task_id=comment["task_id"],
            user_id=comment["user_id"],
            user=user_info,
            content=comment["content"],
            created_at=comment["created_at"],
            updated_at=comment["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.get("/api/comments/task/{task_id}")
async def get_task_comments(task_id: str, token: str = None):
    """
    Επιστρέφει όλα τα σχόλια μιας εργασίας.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        comments_resp = supabase_admin.table("task_comments").select("*").eq("task_id", task_id).order("created_at", desc=False).execute()

        comments = []
        for comment in (comments_resp.data or []):
            user_info = await get_user(comment["user_id"])

            comments.append({
                "id": comment["id"],
                "task_id": comment["task_id"],
                "user_id": comment["user_id"],
                "user": user_info,
                "content": comment["content"],
                "created_at": comment["created_at"],
                "updated_at": comment["updated_at"]
            })

        return comments
    except Exception as e:
        print(f"Error getting comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@app.patch("/api/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(comment_id: str, comment_data: CommentUpdate, token: str = None):
    """
    Ενημερώνει ένα σχόλιο.
    Μόνο ο συγγραφέας του ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε το σχόλιο
        comment_resp = supabase_admin.table("task_comments").select("*").eq("id", comment_id).execute()
        if not comment_resp.data:
            raise HTTPException(status_code=404, detail="Comment not found")

        comment = comment_resp.data[0]

        # Έλεγχος δικαιωμάτων
        if comment["user_id"] != user_id:
            user = await get_user(user_id)
            if user.role.upper() != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to update this comment")

        # Ενημέρωση
        updated_resp = supabase_admin.table("task_comments").update({
            "content": comment_data.content,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", comment_id).execute()

        if not updated_resp.data:
            raise HTTPException(status_code=400, detail="Failed to update comment")

        updated_comment = updated_resp.data[0]

        user_info = await get_user(updated_comment["user_id"])

        return CommentResponse(
            id=updated_comment["id"],
            task_id=updated_comment["task_id"],
            user_id=updated_comment["user_id"],
            user=user_info,
            content=updated_comment["content"],
            created_at=updated_comment["created_at"],
            updated_at=updated_comment["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update comment")


@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str, token: str = None):
    """
    Διαγράφει ένα σχόλιο.
    Μόνο ο συγγραφέας του ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Πάρε το σχόλιο
        comment_resp = supabase_admin.table("task_comments").select("*").eq("id", comment_id).execute()
        if not comment_resp.data:
            raise HTTPException(status_code=404, detail="Comment not found")

        comment = comment_resp.data[0]

        # Έλεγχος δικαιωμάτων
        if comment["user_id"] != user_id:
            user = await get_user(user_id)
            if user.role.upper() != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

        # Διαγραφή
        supabase_admin.table("task_comments").delete().eq("id", comment_id).execute()

        return {"message": "Comment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)