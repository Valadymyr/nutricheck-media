# Instagram — автопублікація NutriCheck

Щоденні картки (власний дизайн, без фото магазинів) для @nutricheck_ua.
- `instagram/YYYY-MM-DD/pod.jpg` — пост «Продукт дня» (1080x1350)
- `instagram/YYYY-MM-DD/quiz_q.jpg`, `quiz_a.jpg` — сторіз «Вгадай бал» (питання і відповідь, 1080x1920)

Генерує `scripts/ig_card.py` із даних бази NutriCheck; публікує заплановане завдання через Windsor.ai.
