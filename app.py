from __future__ import annotations

import os
from datetime import datetime
from typing import List

import click
import requests
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///team_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN", "")
app.config["GITHUB_ORG"] = os.getenv("GITHUB_ORG", "")

db = SQLAlchemy(app)


@app.before_first_request
def initialize_database() -> None:
    """Ensure all database tables exist before handling requests."""
    db.create_all()


@app.cli.command("init-db")
def init_db_command() -> None:
    """Create database tables for the application."""
    db.create_all()
    click.echo("Initialized the database.")


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    members = db.relationship(
        "Member",
        backref="team",
        cascade="all, delete-orphan",
        lazy=True,
    )

    def to_dict(self, include_members: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "created_at": self.created_at.isoformat(),
            "member_count": len(self.members),
        }
        if include_members:
            data["members"] = [member.to_dict() for member in self.members]
        return data


class Member(db.Model):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(120), nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role or "",
            "joined_at": self.joined_at.isoformat(),
            "team_id": self.team_id,
        }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/teams", methods=["GET"])
def list_teams():
    teams: List[Team] = Team.query.order_by(Team.name.asc()).all()
    return jsonify([team.to_dict() for team in teams])


@app.route("/api/teams", methods=["POST"])
def create_team():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"error": "Team name is required."}), 400

    if Team.query.filter_by(name=name).first():
        return jsonify({"error": "A team with this name already exists."}), 400

    team = Team(name=name, description=description)
    db.session.add(team)
    db.session.commit()

    return jsonify(team.to_dict()), 201


@app.route("/api/teams/<int:team_id>", methods=["GET"])
def get_team(team_id: int):
    team = Team.query.get_or_404(team_id)
    return jsonify(team.to_dict(include_members=True))


@app.route("/api/teams/<int:team_id>", methods=["PUT"])
def update_team(team_id: int):
    team = Team.query.get_or_404(team_id)
    data = request.get_json() or {}

    name = (data.get("name") or team.name).strip()
    description = (data.get("description") or "").strip()

    if not name:
        return jsonify({"error": "Team name is required."}), 400

    existing_team = Team.query.filter(Team.id != team_id, Team.name == name).first()
    if existing_team:
        return jsonify({"error": "A team with this name already exists."}), 400

    team.name = name
    team.description = description
    db.session.commit()

    return jsonify(team.to_dict(include_members=True))


@app.route("/api/teams/<int:team_id>", methods=["DELETE"])
def delete_team(team_id: int):
    team = Team.query.get_or_404(team_id)
    db.session.delete(team)
    db.session.commit()
    return jsonify({"status": "deleted"})


@app.route("/api/teams/<int:team_id>/members", methods=["POST"])
def add_member(team_id: int):
    team = Team.query.get_or_404(team_id)
    data = request.get_json() or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    role = (data.get("role") or "").strip()

    if not name or not email:
        return jsonify({"error": "Both name and email are required."}), 400

    member = Member(name=name, email=email, role=role, team=team)
    db.session.add(member)
    db.session.commit()

    return jsonify(member.to_dict()), 201


@app.route("/api/teams/<int:team_id>/members", methods=["GET"])
def list_members(team_id: int):
    team = Team.query.get_or_404(team_id)
    members = [member.to_dict() for member in team.members]
    return jsonify(members)


@app.route("/api/members/<int:member_id>", methods=["PUT"])
def update_member(member_id: int):
    member = Member.query.get_or_404(member_id)
    data = request.get_json() or {}

    name = (data.get("name") or member.name).strip()
    email = (data.get("email") or member.email).strip()
    role = (data.get("role") or "").strip()

    if not name or not email:
        return jsonify({"error": "Both name and email are required."}), 400

    member.name = name
    member.email = email
    member.role = role
    db.session.commit()

    return jsonify(member.to_dict())


@app.route("/api/members/<int:member_id>", methods=["DELETE"])
def delete_member(member_id: int):
    member = Member.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    return jsonify({"status": "deleted"})


class GitHubSyncError(Exception):
    """Raised when synchronizing with GitHub fails."""


def github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = app.config.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_paginated_get(path: str, params: dict | None = None) -> List[dict]:
    """Fetch all pages from a GitHub API endpoint."""

    base_url = "https://api.github.com"
    url = f"{base_url}{path}"
    headers = github_headers()
    results: List[dict] = []
    first_request = True

    while url:
        query_params = params if first_request else None
        first_request = False

        try:
            response = requests.get(
                url,
                headers=headers,
                params=query_params,
                timeout=10,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise GitHubSyncError("Unable to reach GitHub API.") from exc

        if response.status_code >= 400:
            message = response.json().get("message", "GitHub API error.")
            raise GitHubSyncError(message)

        payload = response.json()
        if isinstance(payload, list):
            results.extend(payload)
        else:
            results.append(payload)

        link_header = response.headers.get("Link", "")
        next_url = None
        if link_header:
            parts = [part.strip() for part in link_header.split(",")]
            for part in parts:
                if 'rel="next"' in part:
                    start = part.find("<") + 1
                    end = part.find(">")
                    next_url = part[start:end]
                    break
        url = next_url

    return results


def sync_github(organization: str | None = None) -> dict:
    """Synchronize teams and members from a GitHub organization."""

    org = (organization or app.config.get("GITHUB_ORG", "")).strip()
    if not org:
        raise GitHubSyncError("Set the GITHUB_ORG environment variable to sync with GitHub.")

    teams_payload = github_paginated_get(f"/orgs/{org}/teams", params={"per_page": 100})
    imported_teams = 0
    imported_members = 0

    try:
        for team_payload in teams_payload:
            team_name = team_payload.get("name")
            if not team_name:
                continue

            team = Team.query.filter_by(name=team_name).first()
            if not team:
                team = Team(name=team_name)
                db.session.add(team)

            team.description = team_payload.get("description") or ""
            db.session.flush()

            Member.query.filter_by(team_id=team.id).delete(synchronize_session=False)

            members_payload = github_paginated_get(
                f"/orgs/{org}/teams/{team_payload['slug']}/members",
                params={"per_page": 100, "role": "all"},
            )

            for member_payload in members_payload:
                login = member_payload.get("login")
                if not login:
                    continue

                email = f"{login}@users.noreply.github.com"
                role = member_payload.get("role") or ""
                member = Member(
                    name=member_payload.get("name") or login,
                    email=email,
                    role=role,
                    team=team,
                )
                db.session.add(member)
                imported_members += 1

            imported_teams += 1

        db.session.commit()
    except GitHubSyncError:
        db.session.rollback()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        db.session.rollback()
        raise GitHubSyncError("Failed to import data from GitHub.") from exc

    return {"organization": org, "teams": imported_teams, "members": imported_members}


@app.cli.command("sync-github")
@click.option("--org", "organization", default=None, help="GitHub organization to sync")
def sync_github_command(organization: str | None) -> None:
    """Import teams and members from GitHub into the local database."""

    try:
        summary = sync_github(organization)
    except GitHubSyncError as exc:  # pragma: no cover - CLI surface
        raise click.ClickException(str(exc)) from exc

    click.echo(
        "Imported {teams} teams and {members} members from GitHub organization {org}.".format(
            teams=summary["teams"], members=summary["members"], org=summary["organization"]
        )
    )


@app.route("/api/github/status", methods=["GET"])
def github_status():
    organization = app.config.get("GITHUB_ORG", "").strip()
    configured = bool(organization)
    return jsonify({"configured": configured, "organization": organization})


@app.route("/api/github/sync", methods=["POST"])
def github_sync():
    try:
        summary = sync_github()
    except GitHubSyncError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(summary)


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found."}), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request."}), 400


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
