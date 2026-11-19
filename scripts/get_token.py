#!/usr/bin/env python3
"""Одноразове отримання YouTube refresh token (запускати ЛОКАЛЬНО, не в CI).

1. У Google Cloud Console створіть OAuth client типу «Desktop app»
   і завантажте JSON як client_secret.json (він у .gitignore — не комітьте).
2. pip install google-auth-oauthlib
3. python3 scripts/get_token.py [шлях/до/client_secret.json]
4. У браузері увійдіть в акаунт, що володіє каналом NutriCheck, і дозвольте доступ.
5. Скопіюйте виведені значення в GitHub Secrets (див. README-publish.md).

Токен лише друкується в термінал і нікуди не зберігається.
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    secret_path = Path(sys.argv[1] if len(sys.argv) > 1 else "client_secret.json")
    if not secret_path.is_file():
        print(f"Не знайдено {secret_path}. Завантажте OAuth client (Desktop app) з Google Cloud Console.")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), scopes=SCOPES)
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",  # гарантує видачу refresh token навіть при повторній авторизації
        open_browser=True,
    )

    if not creds.refresh_token:
        print("Google не повернув refresh token. Відкличте доступ на myaccount.google.com/permissions і спробуйте ще раз.")
        return 1

    client = json.loads(secret_path.read_text(encoding="utf-8"))
    client = client.get("installed") or client.get("web") or {}

    print("\nДодайте в GitHub → Settings → Secrets and variables → Actions:\n")
    print(f"YT_CLIENT_ID      = {client.get('client_id', '<з client_secret.json>')}")
    print("YT_CLIENT_SECRET  = <значення client_secret з client_secret.json>")
    print(f"YT_REFRESH_TOKEN  = {creds.refresh_token}")
    print("\nНе комітьте ці значення і не пересилайте їх у месенджерах.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
