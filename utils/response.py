from fastapi.responses import JSONResponse

def success_response(message: str, detail=None, status_code: int = 200):
    """
    Standardized success response format for mobile app
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status_code": status_code,
            "message": message,
            "detail": detail
        }
    )

def error_response(message: str, detail: str = None, status_code: int = 400):
    """
    Standardized error response format for mobile app
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "status_code": status_code,
            "message": message,
            "detail": detail or message
        }
    )