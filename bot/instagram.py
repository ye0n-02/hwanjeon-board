"""Instagram Graph API로 캐러셀 게시."""
from __future__ import annotations

import os
import time

import requests

HOST = os.environ.get("IG_GRAPH_HOST", "graph.facebook.com")
VERSION = os.environ.get("IG_GRAPH_VERSION", "v25.0")


class IGError(RuntimeError):
    pass


def _api(path: str) -> str:
    return f"https://{HOST}/{VERSION}/{path}"


def _call(method: str, path: str, token: str, **params) -> dict:
    params["access_token"] = token
    r = requests.request(method, _api(path), data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    body = r.json() if r.headers.get("content-type", "").startswith(("application/json", "text/javascript")) else {"raw": r.text}
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", body)
        raise IGError(f"{method} {path} 실패: {err.get('message', err) if isinstance(err, dict) else err}")
    return body


def whoami(token: str, user_id: str) -> dict:
    return _call("GET", user_id, token, fields="id,username")


def _wait_ready(container: str, token: str, timeout: int = 300) -> None:
    start = time.time()
    while time.time() - start < timeout:
        st = _call("GET", container, token, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"미디어 처리 실패: {container} {st}")
        time.sleep(5)
    raise IGError(f"미디어 처리 시간 초과: {container}")


def publish_carousel(user_id: str, token: str, media: list[dict], caption: str) -> str:
    """media: [{"type": "image"|"video", "url": "https://..."}] (최대 10개)"""
    children = []
    for m in media:
        if m["type"] == "video":
            c = _call("POST", f"{user_id}/media", token, media_type="VIDEO", video_url=m["url"], is_carousel_item="true")
        else:
            c = _call("POST", f"{user_id}/media", token, image_url=m["url"], is_carousel_item="true")
        children.append(c["id"])
    for cid in children:
        _wait_ready(cid, token)
    parent = _call("POST", f"{user_id}/media", token, media_type="CAROUSEL", children=",".join(children), caption=caption)
    _wait_ready(parent["id"], token)
    res = _call("POST", f"{user_id}/media_publish", token, creation_id=parent["id"])
    return res["id"]
