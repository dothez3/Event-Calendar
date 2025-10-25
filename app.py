from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")

#Leave this commented for now
#app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pms_demo.db"

#This is to make sure either database works, sql lite or MySQL
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv (
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'pms_demo.db')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

#Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(120))
    notes = db.Column(db.Text)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="Planned")
    due_date = db.Column(db.Date)
    client = db.relationship("Client", backref="projects")

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    project = db.relationship("Project", backref="events")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#CLI to init DB
@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    # Seed demo data
    if not User.query.filter_by(email="demo@pms.local").first():
        u = User(email="demo@pms.local", name="Demo User")
        u.set_password("demo123")
        db.session.add(u)
    c = Client(name="Bruce Wayne", contact="bwayne.enterprises@gmail.com", notes="VIP client")
    db.session.add(c)
    p = Project(name="Wayne Residential Complex", client=c, description="Refresh UI", status="In Progress", due_date=datetime(2025,12,23).date())
    db.session.add(p)
    e = Event(title="Pre-Construction Planning", project=p, start=datetime.now())
    db.session.add(e)
    db.session.commit()
    print("Initialized the database. Login with demo@pms.local / demo123")

#Routes
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name = request.form["name"].strip()
        password = request.form["password"]
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

from sqlalchemy import or_, func  # add this import at the top


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["email"].strip()
        password   = request.form["password"]

        # normalize once for case-insensitive name match
        ident_lower = identifier.lower()

        # Try exact email match OR case-insensitive name match
        user = User.query.filter(
            or_(
                User.email == ident_lower,
                func.lower(User.name) == ident_lower
            )
        ).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.order_by(Project.id.desc()).limit(5).all()
    events = Event.query.order_by(Event.start.desc()).limit(5).all()
    stats = {
        "projects": Project.query.count(),
        "clients": Client.query.count(),
        "events": Event.query.count()
    }
    return redirect(url_for("main_menu"))
    #return render_template("dashboard.html", projects=projects, events=events, stats=stats)
#Main Menu
@app.route("/main")
@login_required
def main_menu():
        return render_template("main_menu.html")

# ---- Clients CRUD (minimal) ----
@app.route("/clients")
@login_required
def clients():
    return render_template("clients.html", clients=Client.query.all())

@app.route("/clients/create", methods=["POST"])
@login_required
def clients_create():
    name = request.form["name"].strip()
    contact = request.form.get("contact","").strip()
    notes = request.form.get("notes","").strip()
    if not name:
        flash("Client name required", "warning")
    else:
        db.session.add(Client(name=name, contact=contact, notes=notes))
        db.session.commit()
        flash("Client added", "success")
    return redirect(url_for("clients"))

# ---- Projects CRUD (minimal) ----
@app.route("/projects")
@login_required
def projects():
    return render_template("projects.html", projects=Project.query.all(), clients=Client.query.all())

@app.route("/projects/create", methods=["POST"])
@login_required
def projects_create():
    name = request.form["name"].strip()
    client_id = request.form.get("client_id")
    description = request.form.get("description","").strip()
    due_date = request.form.get("due_date","").strip()
    status = request.form.get("status","Planned").strip()
    if not name:
        flash("Project name required", "warning")
    else:
        p = Project(name=name, client_id=int(client_id) if client_id else None, description=description, status=status,
                    due_date=datetime.fromisoformat(due_date).date() if due_date else None)
        db.session.add(p)
        db.session.commit()
        flash("Project created", "success")
    return redirect(url_for("projects"))

#Events (minimal)
@app.route("/events")
@login_required
def events():
    return render_template("events.html", events=Event.query.order_by(Event.start.desc()).all(), projects=Project.query.all())

@app.route("/events/create", methods=["POST"])
@login_required
def events_create():
    title = request.form["title"].strip()
    project_id = request.form.get("project_id")
    start = request.form.get("start")
    end = request.form.get("end","").strip()
    if not title or not start:
        flash("Title and start are required", "warning")
    else:
        ev = Event(title=title, project_id=int(project_id) if project_id else None,
                   start=datetime.fromisoformat(start),
                   end=datetime.fromisoformat(end) if end else None)
        db.session.add(ev)
        db.session.commit()
        flash("Event created", "success")
    return redirect(url_for("events"))

if __name__ == "__main__":
    app.run(debug=True)
