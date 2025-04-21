from fastapi import APIRouter
from db.dbConnect import create_tables, reset_database, seed_database  # Import your create_tables function properly

router = APIRouter(prefix='/config')


@router.post('/create-tables')
async def create_tables_endpoint():
    create_tables()
    return {"message": "Tables created successfully."}


@router.post("/reset-database")
async def reset_database_endpoint():
    reset_database()
    return {"message": "Database reset successfully."}


@router.post("/seed-database")
async def seed_database_endpoint():
    seed_database()
