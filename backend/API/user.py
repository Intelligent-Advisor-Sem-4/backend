from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Body
from passlib.context import CryptContext
from pydantic.v1 import EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from core.middleware import logger
from core.security import create_access_token, get_current_active_user
from core.password import pwd_context, verify_password, get_password_hash
from db.dbConnect import get_db
from models import UserModel
from classes.User import UserLogin, LoginResponse, UpdatePassword, UserRegistration, RegistrationResponse
from models.models import AccessLevel

router = APIRouter(prefix='/auth', tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=404, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.access_level.value, "user_id": db_user.id})

    return LoginResponse(username=db_user.username, token=access_token, role=db_user.access_level,
                         user_id=str(db_user.id),
                         name=db_user.name, email=EmailStr(db_user.email), avatar=db_user.avatar)


@router.put("/update-password/{username}", status_code=status.HTTP_200_OK)
async def update_user_password(
        username: str,
        password_: UpdatePassword = Body(...),
        db: Session = Depends(get_db),
        current_user=Depends(get_current_active_user)
):
    user_obj = db.query(UserModel).filter(UserModel.username == username).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    user_obj.password = pwd_context.hash(password_.password)
    db.commit()

    logger.info(f"Password updated for user {username}")
    return {"message": "Password updated successfully"}


@router.post("/user/reg", status_code=status.HTTP_201_CREATED, response_model=RegistrationResponse)
async def register_user(user_data: UserRegistration, db: Session = Depends(get_db)):
    # Check if username already exists
    existing_username = db.query(UserModel).filter(UserModel.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # Check if email already exists
    existing_email = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create new user
    try:
        new_user = UserModel(
            name=user_data.name,
            username=user_data.username,
            email=str(user_data.email),
            password=get_password_hash(user_data.password),
            birthday=user_data.birthday,
            gender=user_data.gender,
            avatar=user_data.avatar,
            access_level=AccessLevel.USER,
            created_at=datetime.now(timezone.utc)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User registered successfully",
            "user_id": str(new_user.id)
        }

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
