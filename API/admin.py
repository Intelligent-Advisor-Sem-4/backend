from core.middleware import logger
from db.dbConnect import get_db
from core.security import get_current_active_user
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()


@router.get("/all_admins")
async def admin_list(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, _ = db

    try:
        # Check if the current user is an admin (can be done before fetching admins)
        cursor.callproc("is_admin", [current_user.username])
        admin_record = next(cursor.stored_results()).fetchone()
        is_admin = admin_record["is_admin"] if admin_record else False

        if not is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to view admin list")

        # Fetch all admin details using the 'admins' stored procedure
        cursor.callproc("admins")
        admin_records = next(cursor.stored_results()).fetchall()

        if not admin_records:
            raise HTTPException(status_code=404, detail="No admins found")

        # Map the SQL result to a response list of dictionaries
        admin_list = [
            {
                "first_name": record["first_name"],
                "last_name": record["last_name"],
                "employee_id": record["employee_id"]
            }
            for record in admin_records
        ]

        return admin_list

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching admin details: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")

@router.get("/supervisors", response_model=List[supervisor.supervisor_])
async def all_supervisors(db=Depends(get_db), current_user=Depends(get_current_active_user)):
    cursor, connection = db
    try:
        # Check admin status
        cursor.execute("SELECT is_admin FROM user_access WHERE username = %s", (current_user.username,))
        is_admin = cursor.fetchone()

        # Log admin status to verify the fetch
        logger.info(f"Admin status for user {current_user.username}: {is_admin}")

        # Ensure the user has admin rights
        if not is_admin :
            raise HTTPException(status_code=403, detail="Not authorized to view this information")

        # Call the stored procedure `show_supervisor`
        logger.info("Calling stored procedure 'show_supervisor'")
        cursor.callproc('show_supervisor')

        # Fetch the results from the procedure
        result_cursor = next(cursor.stored_results(), None)

        if result_cursor is None:
            logger.error("No result set returned from stored procedure 'show_supervisor'")
            raise HTTPException(status_code=500, detail="No results returned from the stored procedure")

        supervisors = result_cursor.fetchall()

        # Log fetched supervisors for debugging
        logger.info(f"Supervisors fetched: {supervisors}")

        # Build the response
        all_supervisor_response = [
            supervisor_(
                supervisor_id=row['supervisor_id'],
                first_name=row['first_name'],
                last_name = row['last_name']
            ) for row in supervisors
        ]

        return all_supervisor_response

    except mysql.connector.Error as e:
        logger.error(f"Database error while fetching supervisors: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {str(e)}")