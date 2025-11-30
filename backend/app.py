from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
import bcrypt
from models import (
    UserSignUp, UserLogin, UserResponse, TokenResponse,
    TeamCreate, TeamUpdate, TeamMemberResponse, TeamResponse, TeamDetailResponse,
    AddMemberRequest, TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse, CommentCreate, CommentUpdate, CommentResponse
)

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="User Management API")

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

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ============ HELPER FUNCTIONS ============

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(user_id: str, email: str) -> str:
    """Create JWT token"""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

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

# ============ DATABASE OPERATIONS ============

def create_users_table():
    """Create users table in Supabase (run once)"""
    try:
        supabase.table("users").select("id").limit(1).execute()
    except:
        # Table doesn't exist, create it
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) DEFAULT 'MEMBER',
            is_active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        # Note: Supabase SQL execution requires admin client
        pass

# ============ ENDPOINTS ============

@app.get("/")
def read_root():
    return {"message": "User Management API - Welcome!"}

@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(user_data: UserSignUp):
    """
    Register a new user
    - Username and email must be unique
    - Password is hashed before storage
    - Role defaults to 'MEMBER', activation by admin
    """
    try:
        # Check if user exists
        existing_user = supabase.table("users").select("id").eq("email", user_data.email).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Insert user
        response = supabase.table("users").insert({
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": hashed_password,
            "role": "MEMBER",
            "is_active": False
        }).execute()

        user = response.data[0]
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            created_at=user["created_at"],
            is_active=user["is_active"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login with email and password
    - Returns JWT token if successful
    """
    try:
        # Find user
        response = supabase.table("users").select("*").eq("email", credentials.email).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = response.data[0]

        # Verify password
        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check if user is active
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="User not activated by admin")

        # Create token
        token = create_access_token(user["id"], user["email"])

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                role=user["role"],
                created_at=user["created_at"],
                is_active=user["is_active"]
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user(token: str = None):
    """
    Get current user profile
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_id = verify_token(token)
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = response.data[0]
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
async def get_all_users(token: str = None):
    """
    Get all users (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    # Check if user is admin
    response = supabase.table("users").select("role").eq("id", user_id).execute()
    if not response.data or response.data[0]["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = supabase.table("users").select("*").execute()
    return users.data

@app.get("/api/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(team_id: str, token: str = None):
    """
    Get team details with members
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get team
        team_response = supabase.table("teams").select("*").eq("id", team_id).execute()
        if not team_response.data:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team = team_response.data[0]
        
        # Get leader info
        leader_response = supabase.table("users").select("*").eq(
            "id", team["leader_id"]
        ).execute()
        
        if not leader_response.data:
            raise HTTPException(status_code=404, detail="Leader not found")
        
        leader = leader_response.data[0]
        
        # Get team members
        members_response = supabase.table("team_members").select(
            "user_id, users(id, username, email, role)"
        ).eq("team_id", team_id).execute()
        
        members = []
        if members_response.data:
            for member in members_response.data:
                if member["users"]:
                    user_data = member["users"]
                    if isinstance(user_data, list):
                        user_data = user_data[0]
                    members.append(TeamMemberResponse(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        role=user_data["role"]
                    ))
        
        return TeamDetailResponse(
            id=team["id"],
            name=team["name"],
            description=team["description"],
            leader=UserResponse(
                id=leader["id"],
                username=leader["username"],
                email=leader["email"],
                role=leader["role"],
                is_active=leader["is_active"],
                created_at=leader["created_at"]
            ),
            members=members,
            created_at=team["created_at"],
            updated_at=team["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")

@app.patch("/api/users/{user_id}/activate", response_model=UserResponse)
async def toggle_user_status(user_id: str, token: str = None):
    """
    Toggle user active/inactive status (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    response = supabase.table("users").select("role").eq("id", admin_id).execute()
    if not response.data or response.data[0]["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get current user
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_user = user_response.data[0]
        
        # Toggle status
        new_status = not current_user["is_active"]
        
        # Update user
        updated = supabase.table("users").update({
            "is_active": new_status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not updated.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = updated.data[0]
        
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(user_id: str, role_data: dict, token: str = None):
    """
    Update user role (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    response = supabase.table("users").select("role").eq("id", admin_id).execute()
    if not response.data or response.data[0]["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        new_role = role_data.get("role")
        if new_role not in ["ADMIN", "TEAM_LEADER", "MEMBER"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Update user
        updated = supabase.table("users").update({
            "role": new_role,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        if not updated.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = updated.data[0]
        
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/team", response_model=TeamDetailResponse)
async def get_leader_team(token: str = None):
    """
    Get the team where user is leader (for TEAM_LEADER role)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get user
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_response.data[0]
        
        # If not a leader, return error
        if user["role"] != "TEAM_LEADER":
            raise HTTPException(status_code=403, detail="User is not a team leader")
        
        # Get team where this user is leader
        team_response = supabase.table("teams").select("*").eq("leader_id", user_id).execute()
        if not team_response.data:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team = team_response.data[0]
        
        # Get leader info
        leader = user_response.data[0]
        
        # Get team members
        members_response = supabase.table("team_members").select(
            "user_id, users(id, username, email, role)"
        ).eq("team_id", team["id"]).execute()
        
        members = []
        if members_response.data:
            for member in members_response.data:
                if member["users"]:
                    user_data = member["users"]
                    if isinstance(user_data, list):
                        user_data = user_data[0]
                    members.append(TeamMemberResponse(
                        id=user_data["id"],
                        username=user_data["username"],
                        email=user_data["email"],
                        role=user_data["role"]
                    ))
        
        return TeamDetailResponse(
            id=team["id"],
            name=team["name"],
            description=team["description"],
            leader=UserResponse(
                id=leader["id"],
                username=leader["username"],
                email=leader["email"],
                role=leader["role"],
                is_active=leader["is_active"],
                created_at=leader["created_at"]
            ),
            members=members,
            created_at=team["created_at"],
            updated_at=team["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@app.get("/api/users/me/teams")
async def get_member_teams(token: str = None):
    """
    Get all teams where user is a member (for MEMBER role)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get user
        user_response = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = user_response.data[0]
        
        # Get all teams where this user is a member
        teams_response = supabase.table("team_members").select(
            "team_id, teams(id, name, description, leader_id, created_at, updated_at, users(id, username, email, role))"
        ).eq("user_id", user_id).execute()
        
        teams = []
        if teams_response.data:
            for item in teams_response.data:
                if item["teams"]:
                    team_data = item["teams"]
                    if isinstance(team_data, list):
                        team_data = team_data[0]
                    
                    leader_info = team_data["users"]
                    if isinstance(leader_info, list):
                        leader_info = leader_info[0]
                    
                    teams.append(TeamResponse(
                        id=team_data["id"],
                        name=team_data["name"],
                        description=team_data["description"],
                        leader_id=team_data["leader_id"],
                        created_at=team_data["created_at"],
                        updated_at=team_data["updated_at"]
                    ))
        
        return teams
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")


@app.get("/api/admin/teams")
async def get_all_teams(token: str = None):
    """
    Get all teams (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    try:
        teams_response = supabase.table("teams").select("*").execute()
        
        teams = []
        for team in teams_response.data:
            # Get leader info
            leader_response = supabase.table("users").select("id, username, email").eq(
                "id", team["leader_id"]
            ).execute()
            
            leader_info = leader_response.data[0] if leader_response.data else None
            
            teams.append({
                "id": team["id"],
                "name": team["name"],
                "description": team["description"],
                "leader_id": team["leader_id"],
                "leader_info": leader_info,
                "created_at": team["created_at"],
                "updated_at": team["updated_at"]
            })
        
        return teams
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/teams", response_model=TeamResponse)
async def create_team(team_data: TeamCreate, token: str = None):
    """
    Create a new team
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Create team
        response = supabase.table("teams").insert({
            "name": team_data.name,
            "description": team_data.description,
            "leader_id": team_data.leader_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create team")
        
        team = response.data[0]
        
        # Add leader to team_members
        supabase.table("team_members").insert({
            "team_id": team["id"],
            "user_id": team["leader_id"],
            "joined_at": datetime.utcnow().isoformat()
        }).execute()
        
        return TeamResponse(
            id=team["id"],
            name=team["name"],
            description=team["description"],
            leader_id=team["leader_id"],
            created_at=team["created_at"],
            updated_at=team["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: str, token: str = None):
    """
    Delete a team
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    verify_token(token)
    
    try:
        supabase.table("teams").delete().eq("id", team_id).execute()
        return {"message": "Team deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/teams/{team_id}/members")
async def add_team_member(team_id: str, body: AddMemberRequest, token: str = None):
    """
    Προσθέτει ένα μέλος σε ομάδα.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η ομάδα
        team_resp = supabase.table("teams").select("leader_id").eq("id", team_id).execute()
        if not team_resp.data:
            raise HTTPException(status_code=404, detail="Team not found")

        team = team_resp.data[0]

        caller_resp = supabase.table("users").select("role").eq("id", user_id).execute()
        if not caller_resp.data:
            raise HTTPException(status_code=404, detail="User not found")

        caller_role = caller_resp.data[0]["role"]
        if caller_role not in ["ADMIN", "TEAM_LEADER"] or (
            caller_role == "TEAM_LEADER" and team["leader_id"] != user_id
        ):
            raise HTTPException(status_code=403, detail="Not allowed to add members")

        # Πρόσθεσε το μέλος
        supabase.table("team_members").insert({
            "team_id": team_id,
            "user_id": body.user_id,
            "joined_at": datetime.utcnow().isoformat()
        }).execute()

        return {"message": "Member added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print("Error adding member:", e)
        raise HTTPException(status_code=500, detail="Failed to add member")


@app.delete("/api/teams/{team_id}/members/{user_id}")
async def remove_team_member(team_id: str, user_id: str, token: str = None):
    """
    Αφαιρεί ένα μέλος από την ομάδα.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    caller_id = verify_token(token)

    try:
        # Έλεγχος δικαιωμάτων: μόνο admin ή leader της ομάδας
        team_resp = supabase.table("teams").select("leader_id").eq("id", team_id).execute()
        if not team_resp.data:
            raise HTTPException(status_code=404, detail="Team not found")

        team = team_resp.data[0]

        caller_resp = supabase.table("users").select("role").eq("id", caller_id).execute()
        if not caller_resp.data:
            raise HTTPException(status_code=404, detail="User not found")

        caller_role = caller_resp.data[0]["role"]
        if caller_role not in ["ADMIN", "TEAM_LEADER"] or (
            caller_role == "TEAM_LEADER" and team["leader_id"] != caller_id
        ):
            raise HTTPException(status_code=403, detail="Not allowed to remove members")

        # Μην επιτρέπεις να σβήσουν τον leader από την ομάδα του
        if user_id == team["leader_id"]:
            raise HTTPException(status_code=400, detail="Cannot remove team leader")

        # Διαγραφή από team_members
        supabase.table("team_members").delete().eq("team_id", team_id).eq("user_id", user_id).execute()

        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print("Error removing member:", e)
        raise HTTPException(status_code=500, detail="Failed to remove member")


@app.get("/api/teams/members/available")
async def get_available_team_members(token: str = None):
    """
    Επιστρέφει όλους τους users με role MEMBER.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        resp = supabase.table("users").select(
            "id, username, email, role"
        ).eq("role", "MEMBER").execute()
        users = resp.data or []
        print("AVAILABLE MEMBERS:", users)
        return [
            {
                "id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "role": u["role"],
            }
            for u in users
        ]
    except Exception as e:
        print("Error getting available members:", e)
        raise HTTPException(status_code=500, detail="Failed to get available members")

# ============ TASKS ENDPOINTS ============

@app.post("/api/teams/{team_id}/tasks", response_model=TaskDetailResponse)
async def create_task(team_id: str, task_data: TaskCreate, token: str = None):
    """
    Δημιουργεί μια νέα εργασία σε ομάδα.
    Μόνο leader της ομάδας ή admin.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η ομάδα
        team_resp = supabase.table("teams").select("leader_id").eq("id", team_id).execute()
        if not team_resp.data:
            raise HTTPException(status_code=404, detail="Team not found")

        team = team_resp.data[0]

        # Έλεγχος δικαιωμάτων
        user_resp = supabase.table("users").select("role").eq("id", user_id).execute()
        if not user_resp.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_role = user_resp.data[0]["role"]
        if user_role not in ["ADMIN", "TEAM_LEADER"] or (
            user_role == "TEAM_LEADER" and team["leader_id"] != user_id
        ):
            raise HTTPException(status_code=403, detail="Not allowed to create tasks")

        # Δημιουργία εργασίας
        task_insert = supabase.table("tasks").insert({
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

        # Πάρε created_by user
        created_by_user_resp = supabase.table("users").select("*").eq("id", task["created_by"]).execute()
        created_by_user = created_by_user_resp.data[0] if created_by_user_resp.data else None

        # Πάρε assigned_to user αν υπάρχει
        assigned_to_user = None
        if task["assigned_to"]:
            assigned_to_user_resp = supabase.table("users").select("*").eq("id", task["assigned_to"]).execute()
            assigned_to_user = assigned_to_user_resp.data[0] if assigned_to_user_resp.data else None

        return TaskDetailResponse(
            id=task["id"],
            team_id=task["team_id"],
            title=task["title"],
            description=task["description"],
            status=task["status"],
            priority=task["priority"],
            created_by=task["created_by"],
            created_by_user=UserResponse(
                id=created_by_user["id"],
                username=created_by_user["username"],
                email=created_by_user["email"],
                role=created_by_user["role"],
                is_active=created_by_user["is_active"],
                created_at=created_by_user["created_at"]
            ) if created_by_user else None,
            assigned_to=task["assigned_to"],
            assigned_to_user=UserResponse(
                id=assigned_to_user["id"],
                username=assigned_to_user["username"],
                email=assigned_to_user["email"],
                role=assigned_to_user["role"],
                is_active=assigned_to_user["is_active"],
                created_at=assigned_to_user["created_at"]
            ) if assigned_to_user else None,
            due_date=task["due_date"],
            created_at=task["created_at"],
            updated_at=task["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.get("/api/teams/{team_id}/tasks")
async def get_team_tasks(team_id: str, token: str = None):
    """
    Επιστρέφει όλες τις εργασίες της ομάδας.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        tasks_resp = supabase.table("tasks").select("*").eq("team_id", team_id).order("created_at", desc=True).execute()

        tasks = []
        for task in (tasks_resp.data or []):
            # Πάρε created_by user
            created_by_user_resp = supabase.table("users").select("*").eq("id", task["created_by"]).execute()
            created_by_user = created_by_user_resp.data[0] if created_by_user_resp.data else None

            # Πάρε assigned_to user
            assigned_to_user = None
            if task["assigned_to"]:
                assigned_to_user_resp = supabase.table("users").select("*").eq("id", task["assigned_to"]).execute()
                assigned_to_user = assigned_to_user_resp.data[0] if assigned_to_user_resp.data else None

            tasks.append({
                "id": task["id"],
                "team_id": task["team_id"],
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
                "priority": task["priority"],
                "created_by": task["created_by"],
                "created_by_user": {
                    "id": created_by_user["id"],
                    "username": created_by_user["username"],
                    "email": created_by_user["email"],
                    "role": created_by_user["role"]
                } if created_by_user else None,
                "assigned_to": task["assigned_to"],
                "assigned_to_user": {
                    "id": assigned_to_user["id"],
                    "username": assigned_to_user["username"],
                    "email": assigned_to_user["email"],
                    "role": assigned_to_user["role"]
                } if assigned_to_user else None,
                "due_date": task["due_date"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"]
            })

        return tasks
    except Exception as e:
        print(f"Error getting tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get tasks")


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
        task_resp = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_resp.data[0]

        # Πάρε την ομάδα
        team_resp = supabase.table("teams").select("leader_id").eq("id", task["team_id"]).execute()
        team = team_resp.data[0] if team_resp.data else None

        # Έλεγχος δικαιωμάτων
        user_resp = supabase.table("users").select("role").eq("id", user_id).execute()
        user_role = user_resp.data[0]["role"] if user_resp.data else "MEMBER"

        can_update = (
            user_role == "ADMIN" or
            (team and team["leader_id"] == user_id) or
            task["assigned_to"] == user_id
        )

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

        updated_resp = supabase.table("tasks").update(update_data).eq("id", task_id).execute()

        if not updated_resp.data:
            raise HTTPException(status_code=400, detail="Failed to update task")

        updated_task = updated_resp.data[0]

        # Πάρε created_by user
        created_by_user_resp = supabase.table("users").select("*").eq("id", updated_task["created_by"]).execute()
        created_by_user = created_by_user_resp.data[0] if created_by_user_resp.data else None

        # Πάρε assigned_to user
        assigned_to_user = None
        if updated_task["assigned_to"]:
            assigned_to_user_resp = supabase.table("users").select("*").eq("id", updated_task["assigned_to"]).execute()
            assigned_to_user = assigned_to_user_resp.data[0] if assigned_to_user_resp.data else None

        return TaskDetailResponse(
            id=updated_task["id"],
            team_id=updated_task["team_id"],
            title=updated_task["title"],
            description=updated_task["description"],
            status=updated_task["status"],
            priority=updated_task["priority"],
            created_by=updated_task["created_by"],
            created_by_user=UserResponse(
                id=created_by_user["id"],
                username=created_by_user["username"],
                email=created_by_user["email"],
                role=created_by_user["role"],
                is_active=created_by_user["is_active"],
                created_at=created_by_user["created_at"]
            ) if created_by_user else None,
            assigned_to=updated_task["assigned_to"],
            assigned_to_user=UserResponse(
                id=assigned_to_user["id"],
                username=assigned_to_user["username"],
                email=assigned_to_user["email"],
                role=assigned_to_user["role"],
                is_active=assigned_to_user["is_active"],
                created_at=assigned_to_user["created_at"]
            ) if assigned_to_user else None,
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
        task_resp = supabase.table("tasks").select("*").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        task = task_resp.data[0]

        # Πάρε την ομάδα
        team_resp = supabase.table("teams").select("leader_id").eq("id", task["team_id"]).execute()
        team = team_resp.data[0] if team_resp.data else None

        # Έλεγχος δικαιωμάτων
        user_resp = supabase.table("users").select("role").eq("id", user_id).execute()
        user_role = user_resp.data[0]["role"] if user_resp.data else "MEMBER"

        can_delete = user_role == "ADMIN" or (team and team["leader_id"] == user_id)

        if not can_delete:
            raise HTTPException(status_code=403, detail="Not allowed to delete this task")

        # Διαγραφή
        supabase.table("tasks").delete().eq("id", task_id).execute()

        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

# backend/app.py - Προσθέστε πριν το if __name__:

# ============ COMMENTS ENDPOINTS ============

@app.post("/api/tasks/{task_id}/comments", response_model=CommentResponse)
async def create_comment(task_id: str, comment_data: CommentCreate, token: str = None):
    """
    Δημιουργεί ένα νέο σχόλιο σε μια εργασία.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η εργασία
        task_resp = supabase.table("tasks").select("id").eq("id", task_id).execute()
        if not task_resp.data:
            raise HTTPException(status_code=404, detail="Task not found")

        # Δημιουργία σχολίου
        comment_insert = supabase.table("task_comments").insert({
            "task_id": task_id,
            "user_id": user_id,
            "content": comment_data.content,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

        if not comment_insert.data:
            raise HTTPException(status_code=400, detail="Failed to create comment")

        comment = comment_insert.data[0]

        # Πάρε user info
        user_resp = supabase.table("users").select("*").eq("id", comment["user_id"]).execute()
        user_info = user_resp.data[0] if user_resp.data else None

        return CommentResponse(
            id=comment["id"],
            task_id=comment["task_id"],
            user_id=comment["user_id"],
            user=UserResponse(
                id=user_info["id"],
                username=user_info["username"],
                email=user_info["email"],
                role=user_info["role"],
                is_active=user_info["is_active"],
                created_at=user_info["created_at"]
            ) if user_info else None,
            content=comment["content"],
            created_at=comment["created_at"],
            updated_at=comment["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.get("/api/tasks/{task_id}/comments")
async def get_task_comments(task_id: str, token: str = None):
    """
    Επιστρέφει όλα τα σχόλια μιας εργασίας.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        comments_resp = supabase.table("task_comments").select("*").eq("task_id", task_id).order("created_at", desc=False).execute()

        comments = []
        for comment in (comments_resp.data or []):
            # Πάρε user info
            user_resp = supabase.table("users").select("*").eq("id", comment["user_id"]).execute()
            user_info = user_resp.data[0] if user_resp.data else None

            comments.append({
                "id": comment["id"],
                "task_id": comment["task_id"],
                "user_id": comment["user_id"],
                "user": {
                    "id": user_info["id"],
                    "username": user_info["username"],
                    "email": user_info["email"],
                    "role": user_info["role"]
                } if user_info else None,
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
        comment_resp = supabase.table("task_comments").select("*").eq("id", comment_id).execute()
        if not comment_resp.data:
            raise HTTPException(status_code=404, detail="Comment not found")

        comment = comment_resp.data[0]

        # Έλεγχος δικαιωμάτων
        if comment["user_id"] != user_id:
            user_resp = supabase.table("users").select("role").eq("id", user_id).execute()
            if not user_resp.data or user_resp.data[0]["role"] != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to update this comment")

        # Ενημέρωση
        updated_resp = supabase.table("task_comments").update({
            "content": comment_data.content,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", comment_id).execute()

        if not updated_resp.data:
            raise HTTPException(status_code=400, detail="Failed to update comment")

        updated_comment = updated_resp.data[0]

        # Πάρε user info
        user_resp = supabase.table("users").select("*").eq("id", updated_comment["user_id"]).execute()
        user_info = user_resp.data[0] if user_resp.data else None

        return CommentResponse(
            id=updated_comment["id"],
            task_id=updated_comment["task_id"],
            user_id=updated_comment["user_id"],
            user=UserResponse(
                id=user_info["id"],
                username=user_info["username"],
                email=user_info["email"],
                role=user_info["role"],
                is_active=user_info["is_active"],
                created_at=user_info["created_at"]
            ) if user_info else None,
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
        comment_resp = supabase.table("task_comments").select("*").eq("id", comment_id).execute()
        if not comment_resp.data:
            raise HTTPException(status_code=404, detail="Comment not found")

        comment = comment_resp.data[0]

        # Έλεγχος δικαιωμάτων
        if comment["user_id"] != user_id:
            user_resp = supabase.table("users").select("role").eq("id", user_id).execute()
            if not user_resp.data or user_resp.data[0]["role"] != "ADMIN":
                raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

        # Διαγραφή
        supabase.table("task_comments").delete().eq("id", comment_id).execute()

        return {"message": "Comment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete comment")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
