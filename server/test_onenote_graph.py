"""
OneNote / Microsoft Graph 测试脚本

用法（推荐，从 venv 跑）：
  1) 先获取 token（你已有 services/onenote_generate.py）
  2) 设置环境变量 GRAPH_ACCESS_TOKEN
  3) 运行：.\venv\Scripts\python.exe .\test_onenote_graph.py

PowerShell 示例：
  $env:GRAPH_ACCESS_TOKEN="eyJ..."
  .\venv\Scripts\python.exe .\test_onenote_graph.py
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import requests


GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

os.environ['http_proxy'] = 'http://localhost:7897'
os.environ['https_proxy'] = 'http://localhost:7897'


def graph_get(path: str, token: str, *, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    url = f"{GRAPH_ROOT}{path}"
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        params=params,
        timeout=30,
    )
    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}
    if not resp.ok:
        raise RuntimeError(f"Graph 请求失败 {resp.status_code} {resp.reason}: {json.dumps(data, ensure_ascii=False)}")
    return data


def pick_first(items: list[dict[str, Any]], *, key: str = "id") -> str:
    if not items:
        return ""
    v = items[0].get(key) or ""
    return str(v)


def main() -> None:
    token = os.getenv("GRAPH_ACCESS_TOKEN", "").strip()
    token="eyJ0eXAiOiJKV1QiLCJub25jZSI6Ijl0d0tuZmVyZTV0QklBaVdiQlNzYU0tRTdMcUpDWk5mSEtSekE0Q1I2ek0iLCJhbGciOiJSUzI1NiIsIng1dCI6IlUxc1g4WUZIUzdaNlZsN1ZITEl6VGVqYnZqMCIsImtpZCI6IlUxc1g4WUZIUzdaNlZsN1ZITEl6VGVqYnZqMCJ9.eyJhdWQiOiJodHRwczovL2dyYXBoLm1pY3Jvc29mdC5jb20iLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9kYTMzNDE1NS00N2Q0LTRiMDctOTJiNy02NDA1ZmY2Y2I5OGMvIiwiaWF0IjoxNzc2NDEzNTQ2LCJuYmYiOjE3NzY0MTM1NDYsImV4cCI6MTc3NjQxNzQ0NiwiYWlvIjoiQVNRQTIvOGJBQUFBbHFZWUtIdkVRcVBvbmRhRUNzd3g5ZTNCNkE3cVNnMFpFM3dqcHp6akdyaz0iLCJhcHBfZGlzcGxheW5hbWUiOiJub3RlIiwiYXBwaWQiOiJkYzgwNDMyNC1jMDY5LTRiZTUtYmQ5MS03ZjY3NzllNDIzMmYiLCJhcHBpZGFjciI6IjEiLCJpZHAiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC9kYTMzNDE1NS00N2Q0LTRiMDctOTJiNy02NDA1ZmY2Y2I5OGMvIiwiaWR0eXAiOiJhcHAiLCJvaWQiOiIxOTFmYjdmMS0zYjJkLTQ3YzQtODNkNy00N2E1ODJiM2I4YWEiLCJyaCI6IjEuQVVrQVZVRXoydFJIQjB1U3QyUUZfMnk1akFNQUFBQUFBQUFBd0FBQUFBQUFBQUFBQUFCSkFBLiIsInJvbGVzIjpbIk5vdGVzLlJlYWQuQWxsIiwiTm90ZXMuUmVhZFdyaXRlLkFsbCJdLCJzdWIiOiIxOTFmYjdmMS0zYjJkLTQ3YzQtODNkNy00N2E1ODJiM2I4YWEiLCJ0ZW5hbnRfcmVnaW9uX3Njb3BlIjoiQVMiLCJ0aWQiOiJkYTMzNDE1NS00N2Q0LTRiMDctOTJiNy02NDA1ZmY2Y2I5OGMiLCJ1dGkiOiJxQ1BzYzB5RU9VbUJUNllpY09BVEFBIiwidmVyIjoiMS4wIiwid2lkcyI6WyIwOTk3YTFkMC0wZDFkLTRhY2ItYjQwOC1kNWNhNzMxMjFlOTAiXSwieG1zX2FjZCI6MTc0Mjk2NTQ0NCwieG1zX2FjdF9mY3QiOiIzIDkiLCJ4bXNfZnRkIjoiNGVnOW54NUpWM1dtaU9ncWhSLVVNUF96VVJOTWVrLTB3blEteThzOTBXb0JhMjl5WldGalpXNTBjbUZzTFdSemJYTSIsInhtc19pZHJlbCI6IjcgMiIsInhtc19wZnRleHAiOjE3NzY1MDM4NDYsInhtc19yZCI6IjAuNDJMbFlCSmk5QlFTNFdBWEVwaHNQVTh0WERQV3JmOTUxLU5reTExemhVUTRPSVVFUkJkV2xYLWJYLUc2NDlGR3J2UEgxMTRRRXVIZ0VCSmdab0NBQTFCYVNJU0RXMGdnWTdyUHhUUlZ4Zmo4TGM1RSVVFUkJkV2xYLWJYLUc2NDlGR3J2UEgxMTRRRXVIZ0VCSmdab0NBQTFCYVNJU0RXMGdnWTdyUHhUUlZ4Zmo4TGM1RlM5WnVPZzRBIiwieG1zX3N1Yl9mY3QiOiI5IDMiLCJ4bXNfdGNkdCI6MTU3NTU5MDcyMSwieG1zX3RudF9mY3QiOiIzIDQifQ.Q22Tvm3dUS8hdDn0KgZZWsTe10ls0qSvBGn893j8p3ItZmZb8IHxjsqLE_CAmT-SbcxYPvEuQNQA_UN6Cfa9prAPaQ-VEEIvTpmLqMu282FYESkuoq1RsaY2cDsVRBx0OasBuklCsf9CcuFlK378jyiU7D038pJIA5PWLr1IbZTgEWf-_GYLz56Or4PC3qi9oxz-EP8FMMmJAasBoxyzOIrdrgnWnCeqwqtD0cqrkz7ovi3eT9UU-ZTAiBeWA  "
    if not token:
        raise SystemExit("请先设置环境变量 GRAPH_ACCESS_TOKEN（值为 access_token）")

    # 1) 基本信息
    me = graph_get("/me", token)
    print("== /me ==")
    print(json.dumps({k: me.get(k) for k in ["id", "displayName", "userPrincipalName", "mail"]}, ensure_ascii=False))

    # 2) 列出 notebooks
    notebooks = graph_get("/me/onenote/notebooks", token, params={"$top": 10})
    nb_items = notebooks.get("value", [])
    print("\n== /me/onenote/notebooks (top 10) ==")
    for nb in nb_items:
        print(f"- {nb.get('displayName')}  id={nb.get('id')}")

    notebook_id = pick_first(nb_items)
    if not notebook_id:
        print("\n没有找到任何 notebook。你可以先在 OneNote 创建一个笔记本后再试。")
        return

    # 3) 列出 sections
    sections = graph_get(f"/me/onenote/notebooks/{notebook_id}/sections", token, params={"$top": 10})
    sec_items = sections.get("value", [])
    print("\n== sections (top 10) ==")
    for s in sec_items:
        print(f"- {s.get('displayName')}  id={s.get('id')}")

    section_id = pick_first(sec_items)
    if not section_id:
        print("\n该 notebook 下没有 section。你可以先创建一个分区（Section）后再试。")
        return

    # 4) 列出 pages
    pages = graph_get(f"/me/onenote/sections/{section_id}/pages", token, params={"$top": 10})
    page_items = pages.get("value", [])
    print("\n== pages (top 10) ==")
    for p in page_items:
        print(f"- {p.get('title')}  id={p.get('id')}  created={p.get('createdDateTime')}")


if __name__ == "__main__":
    main()

