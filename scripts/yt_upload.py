#!/usr/bin/env python3
"""Завантаження відео NutriCheck у YouTube (Shorts) через YouTube Data API v3.

Використання:
  python3 scripts/yt_upload.py media/2026-11-19-e250-bot.mp4 [ще.mp4 ...]
  python3 scripts/yt_upload.py --require-flag media/*.mp4   # лише ті, де "youtube": true
  python3 scripts/yt_upload.py --dry-run media/x.mp4        # показати запит, нічого не вантажити

Метадані беруться з сусіднього файлу media/<name>.json:
{
  "youtube": true,                     # прапорець автопублікації (для --require-flag)
  "title": "Що таке E250? #Shorts",    # ≤100 символів; #Shorts додається, якщо його немає
  "description": "...",
  "tags": ["NutriCheck", "склад"],
  "privacyStatus": "public",           # public | unlisted | private (за замовчуванням public)
  "publishAt": "2026-11-20T09:00:00Z", # необов'язково; ISO 8601, у майбутньому
  "containsSyntheticMedia": false,     # ОБОВ'ЯЗКОВО: чи є реалістичний синтетичний/AI-контент
  "categoryId": "22",                  # необов'язково (22 = People & Blogs)
  "defaultLanguage": "uk"              # необов'язково
}

Після успіху у JSON дописується "youtube_id". Відео з наявним youtube_id пропускаються.

Авторизація — лише зі змінних середовища (GitHub Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
CHUNK_SIZE = 8 * 1024 * 1024  # 8 МБ, кратне 256 КБ
MAX_RETRIES = 8
RETRIABLE_STATUS = {500, 502, 503, 504}
PRIVACY = {"public", "unlisted", "private"}
TITLE_MAX = 100
DESC_MAX = 5000
TAGS_MAX_TOTAL = 500


class MetaError(ValueError):
    pass


def log(msg):
    print(msg, flush=True)


def load_meta(json_path: Path) -> dict:
    if not json_path.is_file():
        raise MetaError(f"немає файлу метаданих {json_path}")
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise MetaError(f"{json_path}: некоректний JSON: {e}") from e


def build_body(meta: dict) -> dict:
    title = str(meta.get("title", "")).strip()
    if not title:
        raise MetaError("поле title порожнє")
    if "#shorts" not in title.lower():
        title = f"{title} #Shorts"
    if len(title) > TITLE_MAX:
        raise MetaError(f"title довший за {TITLE_MAX} символів ({len(title)}): {title!r}")

    description = str(meta.get("description", ""))
    if len(description.encode("utf-8")) > DESC_MAX:
        raise MetaError(f"description довший за {DESC_MAX} байт")
    for field, value in (("title", title), ("description", description)):
        if "<" in value or ">" in value:
            raise MetaError(f"{field} не може містити символи < або >")

    tags = meta.get("tags") or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise MetaError("tags має бути списком рядків")
    tags = [t.strip() for t in tags if t.strip()]
    # YouTube рахує теги з пробілами як обгорнуті в лапки (+2) і кому між ними
    total = sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)
    if total > TAGS_MAX_TOTAL:
        raise MetaError(f"сумарна довжина tags {total} > {TAGS_MAX_TOTAL}")

    if "containsSyntheticMedia" not in meta or not isinstance(meta["containsSyntheticMedia"], bool):
        raise MetaError("поле containsSyntheticMedia (true/false) обов'язкове")

    privacy = meta.get("privacyStatus", "public")
    if privacy not in PRIVACY:
        raise MetaError(f"privacyStatus має бути одним із {sorted(PRIVACY)}")

    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": meta["containsSyntheticMedia"],
        "embeddable": True,
    }

    publish_at = meta.get("publishAt")
    if publish_at:
        try:
            dt = datetime.fromisoformat(str(publish_at).replace("Z", "+00:00"))
        except ValueError as e:
            raise MetaError(f"publishAt не ISO 8601: {publish_at!r}") from e
        if dt.tzinfo is None:
            raise MetaError("publishAt має містити часовий пояс (напр. 2026-11-20T09:00:00Z)")
        if dt <= datetime.now(timezone.utc):
            raise MetaError(f"publishAt у минулому: {publish_at}")
        # API приймає publishAt лише для private-відео; YouTube сам опублікує в цей час
        if privacy != "private":
            log(f"  publishAt задано → privacyStatus змінено з {privacy} на private (відкриється автоматично)")
        status["privacyStatus"] = "private"
        status["publishAt"] = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    snippet = {
        "title": title,
        "description": description,
        "tags": tags,
        "categoryId": str(meta.get("categoryId", "22")),
    }
    if meta.get("defaultLanguage"):
        snippet["defaultLanguage"] = meta["defaultLanguage"]
        snippet["defaultAudioLanguage"] = meta["defaultLanguage"]

    return {
        "snippet": snippet,
        "status": status,
        "paidProductPlacementDetails": {"hasPaidProductPlacement": False},
    }


def youtube_client():
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Не задано змінні середовища: {', '.join(missing)}")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def resumable_upload(youtube, video: Path, body: dict) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=CHUNK_SIZE, resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
        notifySubscribers=True,
    )

    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                log(f"  завантажено {int(status.progress() * 100)}%")
            retry = 0
        except HttpError as e:
            if e.resp.status not in RETRIABLE_STATUS:
                raise
            err = f"HTTP {e.resp.status}"
        except (ConnectionError, TimeoutError, OSError) as e:
            err = f"{type(e).__name__}: {e}"
        else:
            continue

        retry += 1
        if retry > MAX_RETRIES:
            raise RuntimeError(f"завантаження не вдалося після {MAX_RETRIES} спроб ({err})")
        sleep = min(2 ** retry, 64) + random.random()
        log(f"  тимчасова помилка ({err}), повтор {retry}/{MAX_RETRIES} через {sleep:.1f} с")
        time.sleep(sleep)

    if "id" not in response:
        raise RuntimeError(f"неочікувана відповідь API: {response}")
    return response["id"]


def write_github_output(key: str, value: str):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+", help="шляхи до .mp4 (або .json поруч із ними)")
    ap.add_argument("--require-flag", action="store_true", help='вантажити лише якщо в JSON "youtube": true')
    ap.add_argument("--dry-run", action="store_true", help="лише перевірити метадані й показати запит")
    args = ap.parse_args()

    youtube = None
    uploaded, failed = [], []

    for arg in args.videos:
        p = Path(arg)
        video = p.with_suffix(".mp4")
        meta_path = p.with_suffix(".json")
        log(f"▶ {video}")

        try:
            if not video.is_file():
                raise MetaError(f"немає відеофайлу {video}")
            meta = load_meta(meta_path)
            if args.require_flag and meta.get("youtube") is not True:
                log('  пропуск: у JSON немає "youtube": true')
                continue
            if meta.get("youtube_id"):
                log(f"  пропуск: вже завантажено (youtube_id={meta['youtube_id']})")
                continue
            body = build_body(meta)
        except MetaError as e:
            log(f"  ПОМИЛКА метаданих: {e}")
            failed.append(str(video))
            continue

        if args.dry_run:
            log(json.dumps(body, ensure_ascii=False, indent=2))
            continue

        try:
            if youtube is None:
                youtube = youtube_client()
            video_id = resumable_upload(youtube, video, body)
        except Exception as e:  # noqa: BLE001 — логуємо і переходимо до наступного
            log(f"  ПОМИЛКА завантаження: {type(e).__name__}: {e}")
            failed.append(str(video))
            continue

        meta["youtube_id"] = video_id
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"  ✓ https://youtube.com/shorts/{video_id}")
        uploaded.append(f"{video}={video_id}")

    write_github_output("uploaded", str(len(uploaded)))
    log(f"Готово: завантажено {len(uploaded)}, помилок {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
