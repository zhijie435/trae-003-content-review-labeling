from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, UserRole
from ..schemas import UserCreate, UserResponse
from ..auth import get_current_active_user, require_role, get_password_hash

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("/", response_model=List[UserResponse])
def get_users(
    role: UserRole = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/annotators", response_model=List[UserResponse])
def get_annotators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    annotators = db.query(User).filter(User.role == UserRole.ANNOTATOR).all()
    return annotators


@router.get("/quality-checkers", response_model=List[UserResponse])
def get_quality_checkers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    checkers = db.query(User).filter(User.role == UserRole.QUALITY_CHECKER).all()
    return checkers


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
