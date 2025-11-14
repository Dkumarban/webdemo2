# Team Management Web App

A full-stack team management system built with Flask, SQLite, and vanilla JavaScript. Create teams, manage their details, and add members from an intuitive web interface.

## Features

- Create, update, and delete teams with descriptions
- View team rosters and member counts at a glance
- Add, edit, and remove team members with roles and contact information
- Optional GitHub sync to import organization teams and members
- Responsive layout with polished styling and instant feedback to user actions

## Getting started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize the database (optional)

Tables are created automatically when the server receives its first request, but you can prepare the database ahead of time with:

```bash
flask --app app.py init-db
```

### 3. Run the development server

```bash
flask --app app.py run --debug
```

The application stores data in a local SQLite database file named `team_management.db`. Tables are created automatically the first time the server receives a request (or when you run `flask --app app.py init-db`).

### 4. Open the app

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to start managing teams.

### 5. (Optional) Sync teams from GitHub

Set the following environment variables before starting the server if you want to import teams from a GitHub organization:

```bash
export GITHUB_ORG="your-org"
# Optional but recommended for higher rate limits and private organizations
export GITHUB_TOKEN="ghp_exampletoken"
```

With the variables set, you can pull the latest teams and members with either the command line or the web UI:

- **CLI:** `flask --app app.py sync-github`
- **Web UI:** Click **Sync from GitHub** in the Teams panel (the button appears only when `GITHUB_ORG` is configured)

Members imported from GitHub use the noreply email format (`<login>@users.noreply.github.com`) when no public email is available.

## API reference

All endpoints return JSON and expect a `Content-Type: application/json` header for POST/PUT requests.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| `GET` | `/api/teams` | List all teams |
| `POST` | `/api/teams` | Create a new team. Body: `{ "name": "", "description": "" }` |
| `GET` | `/api/teams/<id>` | Retrieve team details including members |
| `PUT` | `/api/teams/<id>` | Update team name/description |
| `DELETE` | `/api/teams/<id>` | Delete a team and its members |
| `GET` | `/api/teams/<id>/members` | List members for a team |
| `POST` | `/api/teams/<id>/members` | Add a member. Body: `{ "name": "", "email": "", "role": "" }` |
| `PUT` | `/api/members/<id>` | Update member information |
| `DELETE` | `/api/members/<id>` | Remove a member |

## Project structure

```
.
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── main.js
```

## Development notes

- The server runs with `debug` enabled for convenience; disable it for production.
- SQLite keeps data between restarts. Delete `team_management.db` if you need a fresh database.
