import json
import os

import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = fastapi.FastAPI()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
AUTH_COOKIE_KEY = "onenote_auth"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.get("/api/onenote/auth/status")
def onenote_auth_status(request: fastapi.Request):
    authenticated = request.cookies.get(AUTH_COOKIE_KEY) == "1"
    return {
        "authenticated": authenticated,
        "user": "Microsoft User" if authenticated else "",
    }


@app.post("/api/onenote/auth/logout")
def onenote_auth_logout():
    response = fastapi.responses.JSONResponse({"ok": True})
    response.delete_cookie(AUTH_COOKIE_KEY)
    return response


@app.get("/api/onenote/auth/callback", response_class=HTMLResponse)
def onenote_auth_callback(code: str = "", state: str = ""):
    """
    OAuth 回调最小实现：
    1) 接收微软返回的 code/state
    2) 将登录态写入 cookie（示例）
    3) 通过 postMessage 通知前端并关闭弹窗
    """
    target_origin = state if state.startswith("http://") or state.startswith("https://") else FRONTEND_ORIGIN
    success = bool(code)
    message = "onenote_auth_success" if success else "onenote_auth_error:missing_code"
    message_json = json.dumps(message)
    origin_json = json.dumps(target_origin)

    html = f"""<!doctype html>
<html>
  <head><meta charset="utf-8"><title>OneNote Auth</title></head>
  <body>{'登录成功，正在返回...' if success else '登录失败，请重试'}</body>
  <script>
    if (window.opener) {{
      window.opener.postMessage({message_json}, {origin_json});
    }}
    window.close();
  </script>
</html>
"""

    response = HTMLResponse(content=html)
    if success:
        # 示例：真实场景应在此处用 code 换取 token，并持久化用户会话。
        response.set_cookie(
            key=AUTH_COOKIE_KEY,
            value="1",
            httponly=True,
            samesite="lax",
        )
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
