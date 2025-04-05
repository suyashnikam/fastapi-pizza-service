from dotenv import load_dotenv
import os
import requests
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status
from starlette.requests import Request

# Load environment variables
load_dotenv()
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            excluded_paths = ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
            if any(request.url.path.startswith(path) for path in excluded_paths):
                return await call_next(request)

            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return JSONResponse(
                    content={"detail": "Authorization token required"},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            token = auth_header
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

            is_valid, user_data = await self.is_valid_token(token)
            if not is_valid:
                return JSONResponse(
                    content={"detail": "Invalid or expired token"},
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            request.state.user = user_data or {}
            response = await call_next(request)
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(
                content={"detail": f"Internal server error in middleware: {str(e)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    async def is_valid_token(self, token: str):
        import os
        import requests
        from fastapi import status
        print(os.getenv("USER_SERVICE_BASE_URL"))
        user_service_url = os.getenv("USER_SERVICE_BASE_URL", "http://127.0.0.1:8001") + "/auth/validate"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(user_service_url, headers=headers, timeout=5)
            print("AuthService response:", response.status_code, response.text)
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                return data.get("is_valid", False), data.get("user")
            return False, None
        except requests.exceptions.RequestException as e:
            print(f"[AuthMiddleware] Token validation exception: {e}")
            return False, None
