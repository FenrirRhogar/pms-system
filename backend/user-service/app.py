from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, engine, SessionLocal
from db_models import User
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta
import bcrypt
from models import UserSignUp, UserLogin, UserResponse, TokenResponse
from db_models import Base
from sqlalchemy.exc import OperationalError
import time

load_dotenv()

# Retry logic for DB connection
def wait_for_db():
    retries = 0
    while retries < 30:
        try:
            # Try to connect to the database
            with engine.connect() as connection:
                print("Database connected.")
                return
        except OperationalError:
            retries += 1
            print(f"Database not ready. Retrying {retries}/30...")
            time.sleep(2)
    raise Exception("Could not connect to database after 30 retries")

wait_for_db()

# Initialize Tables (Handle concurrency safely)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Table creation warning (might be handled by another service): {e}")

# Seed Default Admin
def seed_admin():
    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            print(f"Seeding default admin: {admin_email}")
            hashed_pw = bcrypt.hashpw("adminpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            new_admin = User(
                username="admin",
                email=admin_email,
                password_hash=hashed_pw,
                role="ADMIN",
                is_active=True
            )
            db.add(new_admin)
            db.commit()
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

seed_admin()

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
        "sub": str(user_id), # Ensure UUID is string
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
async def signup(user_data: UserSignUp, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Insert user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            role="MEMBER",
            is_active=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return UserResponse(
            id=str(new_user.id),
            username=new_user.username,
            email=new_user.email,
            role=new_user.role,
            created_at=new_user.created_at.isoformat(),
            is_active=new_user.is_active
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    """
    try:
        # Find user
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Check if user is active
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User not activated by admin")

        # Create token
        token = create_access_token(user.id, user.email)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=user.role,
                created_at=user.created_at.isoformat(),
                is_active=user.is_active
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user(token: str = None, db: Session = Depends(get_db)):
    """
    Get current user profile
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_id = verify_token(token)
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
async def get_all_users(token: str = None, db: Session = Depends(get_db)):
    """
    Get all users (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_id = verify_token(token)
    
    # Check if user is admin
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = db.query(User).all()
    # Manual conversion because created_at needs isoformat
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        } for u in users
    ]

@app.patch("/api/users/{user_id}/activate", response_model=UserResponse)
async def toggle_user_status(user_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Toggle user active/inactive status (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin or admin.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Get current user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deactivating admins
        if user.role == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot deactivate an administrator")
        
        # Toggle status
        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(user_id: str, role_data: dict, token: str = None, db: Session = Depends(get_db)):
    """
    Update user role (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin or admin.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent changing admin role
        if user.role == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot change role of an administrator")

        new_role = role_data.get("role")
        if new_role not in ["ADMIN", "TEAM_LEADER", "MEMBER"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        user.role = new_role
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, token: str = None, db: Session = Depends(get_db)):
    """
    Delete a user (admin only)
    """
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    admin_id = verify_token(token)
    
    # Check if requester is admin
    admin = db.query(User).filter(User.id == admin_id).first()
    if not admin or admin.role.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent deleting admins
        if user.role == "ADMIN":
            raise HTTPException(status_code=403, detail="Cannot delete an administrator")
        
        db.delete(user)
        db.commit()
        
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    """
    Get user by ID.
    NOTE: This endpoint should be protected and only accessible by other services.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
