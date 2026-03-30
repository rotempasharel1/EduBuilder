EduBuilder chat/course fix

Replace this file in your repo:
- poseai_backend/main.py

Then restart the stack:
- docker compose down
- docker compose up --build

What this fix adds:
- /chat/generate_course
- /chat/draft (GET/POST/DELETE)
- /courses (POST/PUT/DELETE)
- /courses/my
- /courses/shared
- /admin/courses

Notes:
- The existing frontend/app.py can stay as-is.
- This fix maps course content into the existing Plan table, so no model or migration change is required.
- Drafts are stored in Redis when available, with an in-memory fallback.
