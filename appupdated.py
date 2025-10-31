# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user, login_required, UserMixin, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, func
from datetime import datetime, date
import os

# -------------------------
# App & Config
# -------------------------
app = Flask(__name__)

# Secret key for sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")

# Choose a single, explicit database path.
# Priority:
# 1) DATABASE_URL (e.g., mysql+pymysql://user:pass@host/dbname)
# 2) SQLITE_PATH (absolute file path)
# 3) ./pms_demo.db in the app folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sqlite_default = os.path.join(BASE_DIR, "pms_demo.db")
sqlite_from_env = os.environ.get("SQLITE_PATH", "").strip()

if os.environ.get("DATABASE_URL"):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
elif sqlite_from_env:
    # Ensure folder exists
    os.makedirs(os.path.dirname(sqlite_from_env), exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_from_env}"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_default}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

# -------------------------
# Models
# -------------------------
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    __tablename__ = "client"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    contact = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Backref "projects" defined on Project

class Building(db.Model):
    __tablename__ = "building"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    street = db.Column(db.String(120))
    city = db.Column(db.String(80))
    state = db.Column(db.String(20))
    zip = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Project(db.Model):
    __tablename__ = "project"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id", ondelete="RESTRICT"), index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="Planned")
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    client = db.relationship("Client", backref=db.backref("projects", lazy="dynamic"))

class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id", ondelete="CASCADE"), index=True)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # If a project is deleted, its events are also deleted
    project = db.relationship(
        "Project",
        backref=db.backref("events", cascade="all, delete-orphan", passive_deletes=True)
    )

# -------------------------
# Login loader
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# -------------------------
# DB bootstrap (creates tables once)
# -------------------------
_tables_ready = False

@app.before_request
def ensure_tables_exist():
    global _tables_ready
    if not _tables_ready:
        with app.app_context():
            db.create_all()
        _tables_ready = True

# -------------------------
# CLI commands (optional)
# -------------------------
@app.cli.command("init-db")
def init_db():
    """Create tables if they don't exist. No demo seeding by default."""
    db.create_all()
    print("Initialized the database.")

@app.cli.command("drop-db")
def drop_db():
    """Drop ALL tables (wipe database)."""
    db.drop_all()
    print("Dropped all tables.")

@app.cli.command("reset-db")
def reset_db():
    """Drop and recreate all tables (empty fresh DB)."""
    db.drop_all()
    db.create_all()
    print("Database reset complete (all data removed).")

@app.cli.command("seed-demo")
def seed_demo():
    """Optional: add one demo user and sample records (for testing)."""
    if not User.query.filter_by(email="demo@pms.local").first():
        u = User(email="demo@pms.local", name="Demo User")
        u.set_password("demo123")
        db.session.add(u)
    c = Client(name="Bruce Wayne", contact="bwayne.enterprises@gmail.com", notes="VIP client")
    db.session.add(c)
    p = Project(
        name="Wayne Residential Complex",
        client=c,
        description="Refresh UI",
        status="In Progress",
        due_date=date(2025, 12, 23),
    )
    db.session.add(p)
    e = Event(title="Pre-Construction Planning", project=p, start=datetime.utcnow())
    db.session.add(e)
    db.session.commit()
    print("Seeded demo content (user: demo@pms.local / demo123)")

# -------------------------
# Helpers
# -------------------------
def parse_date_or_none(value: str):
    value = (value or "").strip()
    if not value:
        return None
    # Accept ISO (YYYY-MM-DD) or common formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # As a last resort, try fromisoformat
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None

def parse_dt_or_none(value: str):
    value = (value or "").strip()
    if not value:
        return None
    # Accept ISO first
    try:
        return datetime.fromisoformat(value)
    except Exception:
        pass
    # Try a few common patterns
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")

        if not email or not name or not password:
            flash("Name, email, and password are required.", "warning")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))

        u = User(email=email, name=name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash("Registered! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("email", "").strip()  # field named 'email' in form (can be email or name)
        password   = request.form.get("password", "")

        # Normalize for case-insensitive matching
        ident_lower = identifier.lower()

        # Support either email (exact) or name (case-insensitive)
        user = User.query.filter(
            or_(func.lower(User.email) == ident_lower, func.lower(User.name) == ident_lower)
        ).first()

        # SECURITY: Never reveal whether email/name exists. Generic message only.
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html"), 401

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    # Light dashboard; you can re-enable a template if you have one
    return redirect(url_for("main_menu"))

@app.route("/main")
@login_required
def main_menu():
    return render_template("main_menu.html")

# ---- Clients ----
@app.route("/clients")
@login_required
def clients():
    return render_template("clients.html", clients=Client.query.order_by(Client.id.desc()).all())

@app.route("/clients/create", methods=["POST"])
@login_required
def clients_create():
    name = request.form.get("name", "").strip()
    contact = request.form.get("contact", "").strip()
    notes = request.form.get("notes", "").strip()
    if not name:
        flash("Client name is required.", "warning")
        return redirect(url_for("clients"))

    db.session.add(Client(name=name, contact=contact, notes=notes))
    db.session.commit()
    flash("Client added.", "success")
    return redirect(url_for("clients"))

@app.route("/clients/<int:id>/delete", methods=["POST"])
@login_required
def clients_delete(id):
    c = Client.query.get_or_404(id)
    # Prevent deleting clients that still have projects
    if Project.query.filter_by(client_id=c.id).count() > 0:
        flash("Cannot delete: this client still has projects.", "warning")
        return redirect(url_for("clients"))
    db.session.delete(c)
    db.session.commit()
    flash("Client deleted.", "info")
    return redirect(url_for("clients"))

# ---- Buildings ----
@app.route("/buildings")
@login_required
def buildings():
    return render_template("buildings.html", buildings=Building.query.order_by(Building.id.desc()).all())

@app.route("/buildings/create", methods=["POST"])
@login_required
def buildings_create():
    name = request.form.get("name", "").strip()
    street = request.form.get("street", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    zipc = request.form.get("zip", "").strip()
    notes = request.form.get("notes", "").strip()

    if not name:
        flash("Building name is required.", "warning")
        return redirect(url_for("buildings"))

    b = Building(name=name, street=street, city=city, state=state, zip=zipc, notes=notes)
    db.session.add(b)
    db.session.commit()
    flash("Building added.", "success")
    return redirect(url_for("buildings"))

@app.route("/buildings/<int:id>/update", methods=["POST"])
@login_required
def buildings_update(id):
    b = Building.query.get_or_404(id)
    b.name = request.form.get("name", "").strip()
    b.street = request.form.get("street", "").strip()
    b.city = request.form.get("city", "").strip()
    b.state = request.form.get("state", "").strip()
    b.zip = request.form.get("zip", "").strip()
    b.notes = request.form.get("notes", "").strip()
    db.session.commit()
    flash("Building updated.", "success")
    return redirect(url_for("buildings"))

@app.route("/buildings/<int:id>/delete", methods=["POST"])
@login_required
def buildings_delete(id):
    b = Building.query.get_or_404(id)
    db.session.delete(b)
    db.session.commit()
    flash("Building deleted.", "info")
    return redirect(url_for("buildings"))

# ---- Projects ----
@app.route("/projects")
@login_required
def projects():
    return render_template(
        "projects.html",
        projects=Project.query.order_by(Project.id.desc()).all(),
        clients=Client.query.order_by(Client.name.asc()).all()
    )

@app.route("/projects/create", methods=["POST"])
@login_required
def projects_create():
    name = request.form.get("name", "").strip()
    client_id = request.form.get("client_id")
    description = request.form.get("description", "").strip()
    due_date_raw = request.form.get("due_date", "").strip()
    status = request.form.get("status", "Planned").strip()

    if not name:
        flash("Project name is required.", "warning")
        return redirect(url_for("projects"))

    p = Project(
        name=name,
        client_id=int(client_id) if client_id else None,
        description=description,
        status=status,
        due_date=parse_date_or_none(due_date_raw),
    )
    db.session.add(p)
    db.session.commit()
    flash("Project created.", "success")
    return redirect(url_for("projects"))

@app.route("/projects/<int:id>/delete", methods=["POST"])
@login_required
def projects_delete(id):
    p = Project.query.get_or_404(id)
    # Prevent deleting if events exist (cascade is enabled, but this keeps UX explicit)
    if Event.query.filter_by(project_id=p.id).count() > 0:
        flash("Cannot delete: this project still has events.", "warning")
        return redirect(url_for("projects"))
    db.session.delete(p)
    db.session.commit()
    flash("Project deleted.", "info")
    return redirect(url_for("projects"))

# ---- Events ----
@app.route("/events")
@login_required
def events():
    return render_template(
        "events.html",
        events=Event.query.order_by(Event.start.desc()).all(),
        projects=Project.query.order_by(Project.name.asc()).all()
    )

@app.route("/events/create", methods=["POST"])
@login_required
def events_create():
    title = request.form.get("title", "").strip()
    project_id = request.form.get("project_id")
    start_raw = request.form.get("start", "").strip()
    end_raw = request.form.get("end", "").strip()

    if not title:
        flash("Title is required.", "warning")
        return redirect(url_for("events"))

    start_dt = parse_dt_or_none(start_raw)
    if not start_dt:
        flash("Start datetime is required and must be valid.", "warning")
        return redirect(url_for("events"))

    end_dt = parse_dt_or_none(end_raw) if end_raw else None

    ev = Event(
        title=title,
        project_id=int(project_id) if project_id else None,
        start=start_dt,
        end=end_dt
    )
    db.session.add(ev)
    db.session.commit()
    flash("Event created.", "success")
    return redirect(url_for("events"))

@app.route("/events/<int:id>/delete", methods=["POST"])
@login_required
def events_delete(id):
    e = Event.query.get_or_404(id)
    db.session.delete(e)
    db.session.commit()
    flash("Event deleted.", "info")
    return redirect(url_for("events"))

# -------------------------
# Error handlers (nicer UX)
# -------------------------
@app.errorhandler(401)
def unauthorized(_):
    flash("Please log in to continue.", "warning")
    return redirect(url_for("login"))

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    # Avoid leaking details to users; log in real apps.
    flash("An unexpected error occurred. Please try again.", "danger")
    return redirect(url_for("index"))

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    # IMPORTANT:
    # Flask's debug reloader runs the module twice. Data is safe because we
    # don't auto-seed. If you seed with "flask seed-demo", it runs once.
    app.run(debug=True)
