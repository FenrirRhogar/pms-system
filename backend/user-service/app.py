from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
import bcrypt
from models import UserSignUp, UserLogin, UserResponse, TokenResponse

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="User Service")

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

# ============ ENDPOINTS ============

@app.get("/")
def read_root():
    return {"message": "User Service - Welcome!"}

@app.post("/api/users/signup", response_model=UserResponse)
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

@app.post("/api/users/login", response_model=TokenResponse)
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
    if not response.data or response.data[0]["role"].upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = supabase_admin.table("users").select("*").execute()
    return users.data

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
    if not response.data or response.data[0]["role"].upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get current user
        user_response = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_user = user_response.data[0]
        
        # Prevent deactivating admins
        if current_user["role"] == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot deactivate an administrator")
        
        # Toggle status
        new_status = not current_user["is_active"]
        
        # Update user
        updated = supabase_admin.table("users").update({
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
    if not response.data or response.data[0]["role"].upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get current user
        user_response = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_user = user_response.data[0]

        # Prevent changing admin role
        if current_user["role"] == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot change role of an administrator")

        new_role = role_data.get("role")
        if new_role not in ["ADMIN", "TEAM_LEADER", "MEMBER"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        # Update user
        updated = supabase_admin.table("users").update({
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


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, token: str = None):
    """
    Delete a user (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    response = supabase.table("users").select("role").eq("id", admin_id).execute()
    if not response.data or response.data[0]["role"].upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get target user to check if they are an admin
        user_response = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        target_user = user_response.data[0]
        
        # Prevent deleting admins
        if target_user["role"] == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot delete an administrator")
        
        # Delete user
        supabase_admin.table("users").delete().eq("id", user_id).execute()
        
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str):
    """
    Get user by ID.
    NOTE: This endpoint should be protected and only accessible by other services.
    """
    try:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
