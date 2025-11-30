from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from models import (
    UserResponse, TeamCreate, TeamUpdate, TeamMemberResponse, TeamResponse, TeamDetailResponse, AddMemberRequest
)

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Team Service")

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
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"http://user-service:8080/api/users/{user_id}")
            response.raise_for_status()
            return UserResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Error getting user {user_id} from user-service: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching user {user_id}: {str(e)}")

# ============ ENDPOINTS ============

@app.get("/")
def read_root():
    return {"message": "Team Service - Welcome!"}

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
        leader = await get_user(team["leader_id"])
        
        # Get team members
        members_response = supabase.table("team_members").select("user_id").eq("team_id", team_id).execute()
        
        members = []
        if members_response.data:
            for member_data in members_response.data:
                user = await get_user(member_data["user_id"])
                members.append(TeamMemberResponse(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    role=user.role
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

@app.get("/api/teams/mine/leader", response_model=TeamDetailResponse)
async def get_leader_team(token: str = None):
    """
    Get the team where user is leader (for TEAM_LEADER role)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get user
        user = await get_user(user_id)
        
        # If not a leader, return error
        if user.role != "TEAM_LEADER":
            raise HTTPException(status_code=403, detail="User is not a team leader")
        
        # Get team where this user is leader
        team_response = supabase.table("teams").select("*").eq("leader_id", user_id).execute()
        if not team_response.data:
            raise HTTPException(status_code=404, detail="Team not found")
        
        team = team_response.data[0]
        
        # Get leader info
        leader = user
        
        # Get team members
        members_response = supabase.table("team_members").select("user_id").eq("team_id", team["id"]).execute()
        
        members = []
        if members_response.data:
            for member_data in members_response.data:
                member_user = await get_user(member_data["user_id"])
                members.append(TeamMemberResponse(
                    id=member_user.id,
                    username=member_user.username,
                    email=member_user.email,
                    role=member_user.role
                ))
        
        return TeamDetailResponse(
            id=team["id"],
            name=team["name"],
            description=team["description"],
            leader=leader,
            members=members,
            created_at=team["created_at"],
            updated_at=team["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@app.get("/api/teams/mine/member")
async def get_member_teams(token: str = None):
    """
    Get all teams where user is a member (for MEMBER role)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get all teams where this user is a member
        memberships_response = supabase.table("team_members").select("team_id").eq("user_id", user_id).execute()
        
        teams = []
        if memberships_response.data:
            for membership in memberships_response.data:
                team_id = membership['team_id']
                team_response = supabase.table("teams").select("*").eq("id", team_id).execute()
                if team_response.data:
                    team_data = team_response.data[0]
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


@app.get("/api/teams/admin")
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
            leader_info = await get_user(team["leader_id"])
            
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


@app.get("/api/teams/available-members")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
