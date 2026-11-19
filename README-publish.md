# Автопублікація у YouTube Shorts

Workflow `.github/workflows/youtube-publish.yml` вантажить відео з `media/` через YouTube Data API v3.

## 1. Отримати облікові дані (один раз, локально)

1. [Google Cloud Console](https://console.cloud.google.com/) → новий проєкт → **APIs & Services → Library** → увімкнути **YouTube Data API v3**.
2. **OAuth consent screen**: тип External, додати scope `youtube.upload`. Перевести застосунок у статус **In production** — у статусі *Testing* refresh token діє лише 7 днів.
3. **Credentials → Create credentials → OAuth client ID → Desktop app** → завантажити JSON як `client_secret.json` у корінь репо (він у `.gitignore`).
4. Запустити:
   ```bash
   pip install google-auth-oauthlib
   python3 scripts/get_token.py client_secret.json
   ```
   Увійти в Google-акаунт, якому належить канал NutriCheck, і дозволити доступ.

## 2. Додати 3 секрети в GitHub

Репозиторій → **Settings → Secrets and variables → Actions → New repository secret**:

| Секрет | Звідки |
|---|---|
| `YT_CLIENT_ID` | `client_id` з `client_secret.json` |
| `YT_CLIENT_SECRET` | `client_secret` з `client_secret.json` |
| `YT_REFRESH_TOKEN` | виведений `scripts/get_token.py` |

Після цього `client_secret.json` можна видалити з диска.

## 3. Публікація

Покласти поруч `media/<name>.mp4` і `media/<name>.json` та запушити в `main`:

```json
{
  "youtube": true,
  "title": "Що ховається за E250? #Shorts",
  "description": "Розбір добавки за даними NutriCheck.",
  "tags": ["NutriCheck", "склад продуктів", "E250"],
  "privacyStatus": "public",
  "publishAt": "2026-11-20T09:00:00Z",
  "containsSyntheticMedia": false
}
```

- `title` ≤ 100 символів; `#Shorts` додається автоматично, якщо його немає.
- `containsSyntheticMedia` — обов'язкове: `true`, якщо є реалістичний AI-голос/зображення.
- `publishAt` (необов'язково) — відео завантажується як private і відкривається в цей час.
- Завжди передається `hasPaidProductPlacement=false` і `selfDeclaredMadeForKids=false`.
- Після успіху бот дописує в JSON `youtube_id`; повторно таке відео не вантажиться.

Ручний запуск: **Actions → YouTube Shorts publish → Run workflow**, поле `file` = `media/<name>.mp4`.
