# Instagram — автопублікація NutriCheck

Щоденні картки (власний дизайн + фото товару з бази NutriCheck — рішення власника 21.11.2026) для @nutricheck_ua.
- `instagram/YYYY-MM-DD/pod.jpg` — пост «Продукт дня» (1080x1350)
- `instagram/YYYY-MM-DD/quiz_q.jpg`, `quiz_a.jpg` — сторіз «Вгадай бал» (питання і відповідь, 1080x1920)

Як це працює:
1. Заплановане завдання пушить `instagram/YYYY-MM-DD/in.json` (дані з бази + `image_url` фото товару).
2. GitHub Actions (`.github/workflows/ig-cards.yml`) завантажує фото, малює картки `scripts/ig_card.py` і комітить їх; `cards.ok` = `photo` або `no_photo`.
3. Завдання публікує картки через Windsor.ai і пише `published.json`.
