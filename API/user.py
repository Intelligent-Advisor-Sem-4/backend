from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from core.middleware import logger
from core.security import pwd_context, verify_password, create_access_token, get_current_active_user
from db.dbConnect import get_db
from models.User import UserModel
from classes.User import User, UserLogin, LoginResponse, UpdatePassword

router = APIRouter()

@router.post("/user/reg", status_code=status.HTTP_201_CREATED)
async def create_user(user: User, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)
    new_user = UserModel(
        username=user.username,
        password=hashed_password,
        employee_id=user.employee_id,
        access_level=user.access_level
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User {user.username} registered successfully.")
    return {"message": "User registered successfully", "user": new_user.username}


@router.post("/login", response_model=LoginResponse)
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=404, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": db_user.username})

    return LoginResponse(username=db_user.username, token=access_token, role=db_user.access_level)


@router.put("/user/{username}", status_code=status.HTTP_200_OK)
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
