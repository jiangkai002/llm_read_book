import json
import os
import time
import uuid
from typing import Any, Optional, Union

import fastapi
import msal
import requests
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

onenote_router = APIRouter(prefix="/api/onenote", tags=["OneNote"])

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
AUTH_SESSION_COOKIE_KEY = "onenote_session_id"
MS_TENANT = os.getenv("MS_TENANT_ID", "common")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "").strip()
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "").strip()
REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "http://localhost:8000/api/onenote/auth/callback")
GRAPH_SCOPES = [
    "openid",
    "profile",
    "offline_access",
    "User.Read",
    "Notes.ReadWrite.All",
]
AUTHORITY = f"https://login.microsoftonline.com/{MS_TENANT}"

# 演示阶段使用进程内会话存储；生产环境请改为 Redis/数据库。
SESSION_STORE: dict[str, dict[str, Any]] = {}


class OneNoteCreatePageRequest(BaseModel):
    section_id: str
    title: str
    html_content: str


def _build_msal_client() -> msal.ConfidentialClientApplication:
    if not MS_CLIENT_ID or not MS_CLIENT_SECRET:
        raise fastapi.HTTPException(
            status_code=500,
            detail="Missing MS_CLIENT_ID or MS_CLIENT_SECRET in backend environment",
        )
    return msal.ConfidentialClientApplication(
        client_id=MS_CLIENT_ID,
        authority=AUTHORITY,
        client_credential=MS_CLIENT_SECRET,
    )


def _token_expires_at(expires_in: Optional[Union[int, str]]) -> int:
    seconds = int(expires_in or 0)
    # 提前 60 秒视为过期，减少边界失败。
    return int(time.time()) + max(0, seconds - 60)


def _is_expired(expires_at: Optional[int]) -> bool:
    return not expires_at or expires_at <= int(time.time())


def _refresh_if_needed(session_data: dict[str, Any]) -> dict[str, Any]:
    if not _is_expired(session_data.get("expires_at")):
        return session_data
    refresh_token = session_data.get("refresh_token")
    if not refresh_token:
        raise fastapi.HTTPException(status_code=401, detail="Login expired, please login again")

    msal_client = _build_msal_client()
    result = msal_client.acquire_token_by_refresh_token(refresh_token=refresh_token, scopes=GRAPH_SCOPES)
    if "access_token" not in result:
        raise fastapi.HTTPException(status_code=401, detail=result.get("error_description") or "Failed to refresh token")

    session_data["access_token"] = result["access_token"]
    session_data["refresh_token"] = result.get("refresh_token", refresh_token)
    session_data["expires_at"] = _token_expires_at(result.get("expires_in"))
    return session_data


def _get_session(request: fastapi.Request) -> dict[str, Any]:
    sid = request.cookies.get(AUTH_SESSION_COOKIE_KEY, "")
    session_data = SESSION_STORE.get(sid)
    if not session_data:
        raise fastapi.HTTPException(status_code=401, detail="Not logged in")
    return _refresh_if_needed(session_data)


def _graph_get(
    session_data: dict[str, Any], path: str, params: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    resp = requests.get(
        f"{GRAPH_ROOT}{path}",
        headers={
            "Authorization": f"Bearer {session_data['access_token']}",
            "Accept": "application/json",
        },
        params=params,
        timeout=30,
    )
    payload = resp.json() if resp.content else {}
    if not resp.ok:
        raise fastapi.HTTPException(status_code=resp.status_code, detail=payload)
    return payload


def _graph_post(
    session_data: dict[str, Any],
    path: str,
    *,
    json_body: Optional[dict[str, Any]] = None,
    data: Optional[str] = None,
    content_type: str = "application/json",
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {session_data['access_token']}",
        "Accept": "application/json",
    }
    if content_type:
        headers["Content-Type"] = content_type

    resp = requests.post(
        f"{GRAPH_ROOT}{path}",
        headers=headers,
        json=json_body,
        data=data,
        timeout=30,
    )
    payload = resp.json() if resp.content else {}
    if not resp.ok:
        raise fastapi.HTTPException(status_code=resp.status_code, detail=payload)
    return payload


def _build_popup_html(success: bool, target_origin: str, error_message: str = "") -> HTMLResponse:
    message = "onenote_auth_success" if success else f"onenote_auth_error:{error_message or 'unknown_error'}"
    message_json = json.dumps(message)
    origin_json = json.dumps(target_origin)
    body_msg = "登录成功，正在返回..." if success else "登录失败，请重试"

    html = f"""<!doctype html>
<html>
  <head><meta charset="utf-8"><title>OneNote Auth</title></head>
  <body>{body_msg}</body>
  <script>
    if (window.opener) {{
      window.opener.postMessage({message_json}, {origin_json});
    }}
    window.close();
  </script>
</html>
"""
    return HTMLResponse(content=html)


@onenote_router.get("/auth/status")
def onenote_auth_status(request: fastapi.Request):
    sid = request.cookies.get(AUTH_SESSION_COOKIE_KEY, "")
    if not sid or sid not in SESSION_STORE:
        return {"authenticated": False, "user": ""}
    try:
        session_data = _refresh_if_needed(SESSION_STORE[sid])
    except fastapi.HTTPException:
        SESSION_STORE.pop(sid, None)
        return {"authenticated": False, "user": ""}
    return {
        "authenticated": True,
        "user": session_data.get("user", ""),
    }


@onenote_router.post("/auth/logout")
def onenote_auth_logout(request: fastapi.Request):
    sid = request.cookies.get(AUTH_SESSION_COOKIE_KEY, "")
    if sid:
        SESSION_STORE.pop(sid, None)
    response = fastapi.responses.JSONResponse({"ok": True})
    response.delete_cookie(AUTH_SESSION_COOKIE_KEY)
    return response


@onenote_router.get("/auth/callback", response_class=HTMLResponse)
def onenote_auth_callback(code: str = "", state: str = ""):
    target_origin = state if state.startswith("http://") or state.startswith("https://") else FRONTEND_ORIGIN
    if not code:
        return _build_popup_html(False, target_origin, "missing_code")

    try:
        msal_client = _build_msal_client()
        result = msal_client.acquire_token_by_authorization_code(
            code=code,
            scopes=GRAPH_SCOPES,
            redirect_uri=REDIRECT_URI,
        )
    except fastapi.HTTPException as e:
        return _build_popup_html(False, target_origin, str(e.detail))
    except Exception as e:
        return _build_popup_html(False, target_origin, str(e))

    if "access_token" not in result:
        return _build_popup_html(False, target_origin, result.get("error_description") or "token_exchange_failed")

    access_token = result["access_token"]
    refresh_token = result.get("refresh_token", "")
    expires_at = _token_expires_at(result.get("expires_in"))

    me = requests.get(
        f"{GRAPH_ROOT}/me",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        timeout=30,
    )
    if not me.ok:
        return _build_popup_html(False, target_origin, "fetch_user_failed")

    me_data = me.json()
    user_display = me_data.get("displayName") or me_data.get("userPrincipalName") or "Microsoft User"
    sid = str(uuid.uuid4())
    SESSION_STORE[sid] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "user": user_display,
    }

    response = _build_popup_html(True, target_origin)
    response.set_cookie(
        key=AUTH_SESSION_COOKIE_KEY,
        value=sid,
        httponly=True,
        samesite="lax",
    )
    return response


@onenote_router.get("/notebooks")
def onenote_notebooks(request: fastapi.Request):
    session_data = _get_session(request)
    return _graph_get(session_data, "/me/onenote/notebooks", params={"$top": 100})


@onenote_router.get("/sections")
def onenote_sections(request: fastapi.Request, notebook_id: str):
    session_data = _get_session(request)
    return _graph_get(
        session_data,
        f"/me/onenote/notebooks/{notebook_id}/sections",
        params={"$top": 100},
    )


@onenote_router.get("/pages")
def onenote_pages(request: fastapi.Request, section_id: str):
    session_data = _get_session(request)
    return _graph_get(
        session_data,
        f"/me/onenote/sections/{section_id}/pages",
        params={"$top": 100},
    )


@onenote_router.get("/pages/{page_id}/content")
def onenote_page_content(request: fastapi.Request, page_id: str):
    session_data = _get_session(request)
    resp = requests.get(
        f"{GRAPH_ROOT}/me/onenote/pages/{page_id}/content",
        headers={"Authorization": f"Bearer {session_data['access_token']}", "Accept": "text/html"},
        timeout=30,
    )
    if not resp.ok:
        detail = resp.text
        raise fastapi.HTTPException(status_code=resp.status_code, detail=detail)
    return {"content": resp.text}


@onenote_router.post("/pages")
def onenote_create_page(request: fastapi.Request, payload: OneNoteCreatePageRequest):
    session_data = _get_session(request)
    title = payload.title.strip() or "Untitled"
    # Graph 创建 OneNote 页面要求 XHTML 文档。
    html = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{title}</title>
    <meta name="created" content="2026-01-01T00:00:00.000Z" />
  </head>
  <body>
    {payload.html_content}
  </body>
</html>"""
    return _graph_post(
        session_data,
        f"/me/onenote/sections/{payload.section_id}/pages",
        data=html,
        content_type="application/xhtml+xml",
    )
