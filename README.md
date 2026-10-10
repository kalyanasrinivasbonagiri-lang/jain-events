# Jain Events

A small event booking website built with FastAPI, MongoDB, and plain HTML, CSS, and JavaScript. Students can browse events, reserve or cancel a seat, and look up their registrations. An admin can manage events and inspect attendees. Every change is written to MongoDB immediately.

## Requirements

- Python 3.10 or later
- MongoDB Community Server running locally on `mongodb://localhost:27017`
- MongoDB Compass (optional, for viewing the collections)

## Run locally (Windows PowerShell)

Open PowerShell in the repository root, then run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a private admin password. The default local database setting is:

```dotenv
MONGO_URI=mongodb://localhost:27017/event_portal
ADMIN_PASSWORD=choose-a-private-password
```

Insert or refresh the four sample events, then start the website:

```powershell
py -m backend.seed
uvicorn backend.app:app --reload
```

Open <http://127.0.0.1:8000>. The home page is student sign-in and account creation; public event browsing is at `/events`. For administrator access, type `http://127.0.0.1:8000/admin` directly in the address bar. The sign-in screen opens without an admin link in the public site. After signing in with the password from `.env`, the management dashboard opens at `/admin/dashboard`. To stop the server, press `Ctrl+C`. If PowerShell blocks venv activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. You can also run the environment's Python directly without activation: `\.venv\Scripts\python.exe -m backend.seed` and `\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload`.

## MongoDB Compass demonstration

1. Connect Compass to `mongodb://localhost:27017`.
2. Open the `event_portal` database, then the `events` collection. Each document contains its event details and current `totalSeats` and `availableSeats` values.
3. Create a student account with name, email, USN, branch, year, and password. Sign in and reserve an event seat. Refresh `events`: `availableSeats` decreases by one. Open `registrations` to see the registration and student details, and `students` to see the account profile (passwords are stored as salted hashes).
4. Cancel the registration from **My registrations**. Refresh both collections: the registration disappears and the event's available seat count increases.
5. Sign in at `/admin` and add, edit, or delete an event. Refresh the `events` collection. Deleting an event also removes its registration documents.
6. The site's **MongoDB view** is an admin-protected, auto-refreshing JSON view of both collections. Compass reads the same persisted data directly from MongoDB.

Sample seed events are safe to refresh: seeding updates their details and capacity while retaining registrations already made for those events. Capacity will not be reduced below the number of existing registrations.

## API overview

Admin routes require the `X-Admin-Token` header. Obtain the token with `POST /api/admin/login` and a JSON body containing the configured password.

- `GET /api/health` — API and MongoDB status
- `GET /api/events` — browse events; optional `q` and `date` filters
- `POST /api/events` — admin: create an event
- `PUT /api/events/{id}` — admin: update event details/capacity
- `DELETE /api/events/{id}` — admin: delete an event and its registrations
- `POST /api/student/signup` and `POST /api/student/login` — create or sign in to a student account
- `POST /api/events/{id}/register` — register the signed-in student
- `DELETE /api/events/{id}/register?email=...` — cancel a registration
- `GET /api/events/{id}/registrations` — admin: list an event's registrations
- `GET /api/my-registrations` — list the signed-in student's registrations
- `GET /api/stats` — admin: event and registration totals for the dashboard chart
- `POST /api/admin/login` — validate the admin password and return a token
- `GET /api/student/me` — profile for the signed-in student
- `GET /api/admin/db-view` — admin: live-demo JSON for both MongoDB collections

Registration claims a seat with a single atomic MongoDB update, so concurrent requests cannot exceed event capacity. If the unique `(eventId, email)` index rejects a duplicate registration, the seat claim is rolled back. Past events cannot accept registrations.

## Project layout

```text
backend/          FastAPI application, MongoDB access, models, routes, and seed script
frontend/         HTML pages, responsive CSS, and vanilla JavaScript
.env.example      Local configuration template
requirements.txt
README.md
```
