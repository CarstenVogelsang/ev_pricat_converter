"""Support team models for the ticket system.

This module contains the SupportTeam and SupportTeamMitglied models
for managing support teams and their members.
"""
from datetime import datetime

from app import db


class SupportTeam(db.Model):
    """Support team for handling tickets.

    A team groups multiple users (Mitarbeiter) who can handle support tickets.
    In MVP, there's one default team. In V2, teams can be assigned per module.
    """
    __tablename__ = 'support_team'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    beschreibung = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(120), nullable=True)  # Optional team email
    icon = db.Column(db.String(50), default='ti-users')
    aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    mitglieder = db.relationship(
        'SupportTeamMitglied',
        backref='team',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    tickets = db.relationship(
        'SupportTicket',
        backref='team',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<SupportTeam {self.name}>'

    @property
    def aktive_mitglieder(self):
        """Get all active team members."""
        return [m for m in self.mitglieder if m.user and m.user.aktiv]

    @property
    def mitglieder_mit_benachrichtigung(self):
        """Get team members who should receive email notifications."""
        return [
            m for m in self.mitglieder
            if m.benachrichtigung_aktiv and m.user and m.user.aktiv
        ]

    @property
    def teamleiter(self):
        """Get the team leader(s)."""
        return [m for m in self.mitglieder if m.ist_teamleiter]

    @classmethod
    def get_default_team(cls):
        """Get the default support team (first active team)."""
        return cls.query.filter_by(aktiv=True).first()


class SupportTeamMitglied(db.Model):
    """Junction table for team membership.

    Associates users with support teams. A user can be in multiple teams.
    """
    __tablename__ = 'support_team_mitglied'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('support_team.id'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    ist_teamleiter = db.Column(db.Boolean, default=False)
    benachrichtigung_aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='support_team_mitgliedschaften')

    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='uq_support_team_user'),
    )

    def __repr__(self):
        return f'<SupportTeamMitglied team={self.team_id} user={self.user_id}>'


# V2: Team-Modul assignment (not implemented in MVP)
# class SupportTeamModul(db.Model):
#     """Assignment of teams to modules (V2 feature).
#
#     Defines which team handles tickets for which module.
#     """
#     __tablename__ = 'support_team_modul'
#
#     id = db.Column(db.Integer, primary_key=True)
#     team_id = db.Column(db.Integer, db.ForeignKey('support_team.id'), nullable=False)
#     modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#
#     __table_args__ = (
#         db.UniqueConstraint('team_id', 'modul_id', name='uq_support_team_modul'),
#     )
