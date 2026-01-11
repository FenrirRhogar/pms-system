from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, engine
from db_models import Team, TeamMember, User
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
from models import (
    UserResponse, TeamCreate, TeamUpdate, TeamMemberResponse, TeamResponse, TeamDetailResponse, AddMemberRequest
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
app = FastAPI(title="Team Service")

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


@app.get("/api/teams/admin")
async def get_all_teams(token: str = None, db: Session = Depends(get_db)):
    """
    Get all teams (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if user is admin
    # Need to fetch admin role from user-service or check local DB if duplicated
    # Since we share the DB, we can check local User table
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin or admin.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        teams = db.query(Team).all()
        
        result = []
        for team in teams:
            leader_info = await get_user(str(team.leader_id))
            
            result.append({
                "id": str(team.id),
                "name": team.name,
                "description": team.description,
                "leader_id": str(team.leader_id),
                "leader_info": leader_info,
                "created_at": team.created_at.isoformat(),
                "updated_at": team.updated_at.isoformat()
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/teams/available-members")
async def get_available_team_members(token: str = None, db: Session = Depends(get_db)):
    """
    Επιστρέφει όλους τους users με role MEMBER.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    verify_token(token)

    try:
        users = db.query(User).filter(User.role == "MEMBER").all()
        return [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "role": u.role,
            }
            for u in users
        ]
    except Exception as e:
        print("Error getting available members:", e)
        raise HTTPException(status_code=500, detail="Failed to get available members")


@app.get("/api/teams/{team_id}", response_model=TeamDetailResponse)
async def get_team(team_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Get team details with members
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get team
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get leader info
        leader = await get_user(str(team.leader_id))
        
        # Get team members
        # Using relationship
        members = []
        for member_rel in team.members:
             user = await get_user(str(member_rel.user_id))
             members.append(TeamMemberResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role
            ))
        
        return TeamDetailResponse(
            id=str(team.id),
            name=team.name,
            description=team.description,
            leader=UserResponse(
                id=leader.id,
                username=leader.username,
                email=leader.email,
                role=leader.role,
                is_active=leader.is_active,
                created_at=leader.created_at
            ),
            members=members,
            created_at=team.created_at.isoformat(),
            updated_at=team.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")

@app.get("/api/teams/mine/leader", response_model=TeamDetailResponse)
async def get_leader_team(token: str = None, db: Session = Depends(get_db)):
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
        if user.role.upper() != "TEAM_LEADER":
            raise HTTPException(status_code=403, detail="User is not a team leader")
        
        # Get team where this user is leader
        team = db.query(Team).filter(Team.leader_id == user_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Get leader info
        leader = user
        
        # Get team members
        members = []
        for member_rel in team.members:
             member_user = await get_user(str(member_rel.user_id))
             members.append(TeamMemberResponse(
                id=member_user.id,
                username=member_user.username,
                email=member_user.email,
                role=member_user.role
            ))
        
        return TeamDetailResponse(
            id=str(team.id),
            name=team.name,
            description=team.description,
            leader=leader,
            members=members,
            created_at=team.created_at.isoformat(),
            updated_at=team.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@app.get("/api/teams/mine/member")
async def get_member_teams(token: str = None, db: Session = Depends(get_db)):
    """
    Get all teams where user is a member (for MEMBER role)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Get all teams where this user is a member
        # Using joins or relationships
        # User -> memberships -> team
        user_memberships = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()
        
        teams = []
        for membership in user_memberships:
            team = membership.team
            if team:
                teams.append(TeamResponse(
                    id=str(team.id),
                    name=team.name,
                    description=team.description,
                    leader_id=str(team.leader_id),
                    created_at=team.created_at.isoformat(),
                    updated_at=team.updated_at.isoformat()
                ))
        
        return teams
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get teams: {str(e)}")


@app.post("/api/teams", response_model=TeamResponse)
async def create_team(team_data: TeamCreate, token: str = None, db: Session = Depends(get_db)):
    """
    Create a new team
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    try:
        # Check if leader is already leading a team
        existing_team = db.query(Team).filter(Team.leader_id == team_data.leader_id).first()
        if existing_team:
            raise HTTPException(status_code=400, detail="User is already leading a team")

        # Create team
        new_team = Team(
            name=team_data.name,
            description=team_data.description,
            leader_id=team_data.leader_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        
        # Add leader to team_members
        new_member = TeamMember(
            team_id=new_team.id,
            user_id=new_team.leader_id,
            joined_at=datetime.utcnow()
        )
        db.add(new_member)
        db.commit()
        
        return TeamResponse(
            id=str(new_team.id),
            name=new_team.name,
            description=new_team.description,
            leader_id=str(new_team.leader_id),
            created_at=new_team.created_at.isoformat(),
            updated_at=new_team.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/teams/{team_id}")
async def delete_team(team_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Delete a team
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    verify_token(token)
    
    try:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
             raise HTTPException(status_code=404, detail="Team not found")
        
        db.delete(team)
        db.commit()
        return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/teams/{team_id}/members")
async def add_team_member(team_id: str, body: AddMemberRequest, token: str = None, db: Session = Depends(get_db)):
    """
    Προσθέτει ένα μέλος σε ομάδα.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_token(token)

    try:
        # Έλεγχος αν υπάρχει η ομάδα
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        caller = db.query(User).filter(User.id == user_id).first()
        if not caller:
            raise HTTPException(status_code=404, detail="User not found")

        caller_role = caller.role.upper()
        if caller_role not in ["ADMIN", "TEAM_LEADER"] or (
            caller_role == "TEAM_LEADER" and str(team.leader_id) != user_id
        ):
            raise HTTPException(status_code=403, detail="Not allowed to add members")

        # Πρόσθεσε το μέλος
        # Check if already member
        existing_member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == body.user_id).first()
        if existing_member:
             raise HTTPException(status_code=400, detail="User already in team")

        new_member = TeamMember(
            team_id=team_id,
            user_id=body.user_id,
            joined_at=datetime.utcnow()
        )
        db.add(new_member)
        db.commit()

        return {"message": "Member added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("Error adding member:", e)
        raise HTTPException(status_code=500, detail="Failed to add member")


@app.delete("/api/teams/{team_id}/members/{user_id}")
async def remove_team_member(team_id: str, user_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Αφαιρεί ένα μέλος από την ομάδα.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    caller_id = verify_token(token)

    try:
        # Έλεγχος δικαιωμάτων: μόνο admin ή leader της ομάδας
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        caller = db.query(User).filter(User.id == caller_id).first()
        if not caller:
            raise HTTPException(status_code=404, detail="User not found")

        caller_role = caller.role.upper()
        if caller_role not in ["ADMIN", "TEAM_LEADER"] or (
            caller_role == "TEAM_LEADER" and str(team.leader_id) != caller_id
        ):
            raise HTTPException(status_code=403, detail="Not allowed to remove members")

        # Μην επιτρέπεις να σβήσουν τον leader από την ομάδα του
        if user_id == str(team.leader_id):
            raise HTTPException(status_code=400, detail="Cannot remove team leader")

        # Διαγραφή από team_members
        member = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first()
        if member:
            db.delete(member)
            db.commit()

        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("Error removing member:", e)
        raise HTTPException(status_code=500, detail="Failed to remove member")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
