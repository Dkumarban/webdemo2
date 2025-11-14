from __future__ import annotations

from datetime import datetime
from typing import List

import click
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///team_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
