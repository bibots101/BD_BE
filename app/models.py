from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="researcher")
    avatar = db.Column(db.String(255))
    active = db.Column(db.Boolean, nullable=False, default=True)

    researcher = db.relationship("Researcher", back_populates="user", uselist=False)


class ResearchAxis(TimestampMixin, db.Model):
    __tablename__ = "research_axes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    lead_researcher_id = db.Column(db.Integer, db.ForeignKey("researchers.id", ondelete="SET NULL"))

    members = db.relationship(
        "Researcher",
        secondary="researcher_axes",
        back_populates="axes",
        lazy="dynamic",
    )


researcher_axes = db.Table(
    "researcher_axes",
    db.Column("researcher_id", db.Integer, db.ForeignKey("researchers.id", ondelete="CASCADE"), primary_key=True),
    db.Column("axis_id", db.Integer, db.ForeignKey("research_axes.id", ondelete="CASCADE"), primary_key=True),
)


class Researcher(TimestampMixin, db.Model):
    __tablename__ = "researchers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    grade = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(255), nullable=False)
    office = db.Column(db.String(120))
    phone = db.Column(db.String(60))
    bio = db.Column(db.Text)
    is_retired = db.Column(db.Boolean, nullable=False, default=False)
    institution_email = db.Column(db.String(255), nullable=False, unique=True)
    orcid = db.Column(db.String(80))
    google_scholar_url = db.Column(db.String(255))
    researchgate_url = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))

    user = db.relationship("User", back_populates="researcher")
    axes = db.relationship(
        "ResearchAxis",
        secondary=researcher_axes,
        back_populates="members",
        lazy="dynamic",
    )
    publications = db.relationship("Publication", back_populates="owner", lazy="dynamic")


class PhDStudent(TimestampMixin, db.Model):
    __tablename__ = "phd_students"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    photo_url = db.Column(db.String(255))
    thesis_topic = db.Column(db.Text, nullable=False)
    thesis_director_id = db.Column(db.Integer, db.ForeignKey("researchers.id", ondelete="SET NULL"))
    start_date = db.Column(db.Date, nullable=False)
    progress_state = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="en_cours")
    defense_date = db.Column(db.Date)
    mention = db.Column(db.String(120))

    thesis_director = db.relationship("Researcher")


class MasterStudent(TimestampMixin, db.Model):
    __tablename__ = "master_students"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    photo_url = db.Column(db.String(255))
    topic = db.Column(db.Text, nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey("researchers.id", ondelete="SET NULL"))
    promotion = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="en_cours")

    supervisor = db.relationship("Researcher")


publication_axes = db.Table(
    "publication_axes",
    db.Column("publication_id", db.Integer, db.ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True),
    db.Column("axis_id", db.Integer, db.ForeignKey("research_axes.id", ondelete="CASCADE"), primary_key=True),
)


publication_authors = db.Table(
    "publication_authors",
    db.Column("publication_id", db.Integer, db.ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True),
    db.Column("researcher_id", db.Integer, db.ForeignKey("researchers.id", ondelete="CASCADE"), primary_key=True),
)


class Publication(TimestampMixin, db.Model):
    __tablename__ = "publications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(400), nullable=False)
    publication_type = db.Column(db.String(60), nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    abstract = db.Column(db.Text)
    doi = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    pdf_path = db.Column(db.String(255))
    venue_name = db.Column(db.String(255))
    ranking = db.Column(db.String(60))
    ranking_source = db.Column(db.String(120))
    keywords = db.Column(db.String(400))
    citations = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), nullable=False, default="draft")

    owner_id = db.Column(db.Integer, db.ForeignKey("researchers.id", ondelete="SET NULL"))
    owner = db.relationship("Researcher", back_populates="publications")

    axes = db.relationship("ResearchAxis", secondary=publication_axes, lazy="dynamic")
    internal_authors = db.relationship("Researcher", secondary=publication_authors, lazy="dynamic")
    external_authors = db.relationship("ExternalAuthor", back_populates="publication", cascade="all, delete-orphan")


class ExternalAuthor(TimestampMixin, db.Model):
    __tablename__ = "external_authors"

    id = db.Column(db.Integer, primary_key=True)
    publication_id = db.Column(db.Integer, db.ForeignKey("publications.id", ondelete="CASCADE"), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)

    publication = db.relationship("Publication", back_populates="external_authors")


class Event(TimestampMixin, db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    program_text = db.Column(db.Text)
    program_pdf_path = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="a_venir")

    photos = db.relationship("Photo", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_event_end_after_start"),)


class Photo(TimestampMixin, db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))
    display_order = db.Column(db.Integer, nullable=False, default=0)

    event = db.relationship("Event", back_populates="photos")


class ContactMessage(TimestampMixin, db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)


class Setting(TimestampMixin, db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(120), nullable=False)
    entity = db.Column(db.String(120), nullable=False)
    entity_id = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("id", name="uq_audit_id"),)
