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
login_manager.login_view = "index"

#Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='client', nullable=False)  # changes: Added role field ('client' or 'employee')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(120))
    phone = db.Column(db.String(50)) 
    
class Building(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    street = db.Column(db.String(120))
    city = db.Column(db.String(80))
    state = db.Column(db.String(20))
    zip = db.Column(db.String(20))
    notes = db.Column(db.Text)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="Planned")
    due_date = db.Column(db.Date)
    client = db.relationship("Client", backref="projects")

#  changes: New model to track which client users are assigned to which projects
class ProjectAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', backref='assignments')
    user = db.relationship('User', backref='project_assignments')

#Improved Event class:
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50))  # e.g., 'Site Visit', 'Client Meeting'
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Upcoming')  # Upcoming / Completed / Cancelled
    notes = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref='events')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#  changes: Helper functions for role-based access control
from functools import wraps

def employee_required(f):
    """Decorator to require employee role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'employee':
            flash("Access denied. Employee privileges required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_projects():
    """Get projects accessible to current user based on role"""
    if current_user.role == 'employee':
        # Employees see all projects
        return Project.query.all()
    else:
        # Clients only see assigned projects
        assigned_project_ids = [pa.project_id for pa in current_user.project_assignments]
        return Project.query.filter(Project.id.in_(assigned_project_ids)).all() if assigned_project_ids else []

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), index=True, nullable=False)
    happened_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)

    user = db.relationship('User', backref='activities')
    project = db.relationship('Project', backref='activities')

#CLI to init DB
@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    # Seed demo data
    if not User.query.filter_by(email="demo@pms.local").first():
        u = User(email="demo@pms.local", name="Demo User", role="employee")  #  changes: Set demo user as employee
        u.set_password("demo123")
        db.session.add(u)
    c = Client(name="Bruce Wayne", contact="bwayne.enterprises@gmail.com", phone="555-01234")
    db.session.add(c)
    p = Project(name="Wayne Residential Complex", client=c, description="Refresh UI", status="In Progress", due_date=datetime(2025,12,23).date())
    db.session.add(p)
    e = Event(title="Pre-Construction Planning", project=p, start=datetime.now())
    db.session.add(e)
    db.session.commit()
    print("Initialized the database. Login with demo@pms.local / demo123")

#Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    
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

@app.route("/client-login", methods=["GET", "POST"])
def client_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    
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
    
    return render_template("client_login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    # Get the type from query parameter (employee or client)
    account_type = request.args.get('type', 'client')
    
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        name = request.form["name"].strip()
        password = request.form["password"]
        role = request.form.get("role", account_type)
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register", type=account_type))
        
        # Create user with the specified role
        u = User(email=email, name=name, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        
        if role == 'employee':
            flash("Registered as employee! Please login.", "success")
            return redirect(url_for("index"))
        else:
            flash("Registered as client! Please login.", "success")
            return redirect(url_for("client_login"))
    
    return render_template("register.html", account_type=account_type)

from sqlalchemy import or_, func , desc # add this import at the top

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == 'employee':
        # Employees see all data
        recent_projects = (
            db.session.query(Project)
            .join(Activity, Activity.project_id == Project.id)
            .filter(Activity.user_id == current_user.id)
            .order_by(desc(Activity.happened_at))
            .limit(6)
            .all()
        )
        events = Event.query.order_by(Event.start.desc()).limit(5).all()
        stats = {
            "projects": Project.query.count(),
            "clients": Client.query.count(),
            "events": Event.query.count()
        }
    else:
        # Clients only see their assigned projects and related events
        assigned_project_ids = [pa.project_id for pa in current_user.project_assignments]
        
        if assigned_project_ids:
            recent_projects = Project.query.filter(Project.id.in_(assigned_project_ids)).limit(6).all()
            events = Event.query.filter(Event.project_id.in_(assigned_project_ids)).order_by(Event.start.desc()).limit(5).all()
            stats = {
                "projects": len(assigned_project_ids),
                "clients": 0,  # Clients don't see client count
                "events": Event.query.filter(Event.project_id.in_(assigned_project_ids)).count()
            }
        else:
            recent_projects = []
            events = []
            stats = {
                "projects": 0,
                "clients": 0,
                "events": 0
            }

    return render_template(
        "dashboard.html",
        recent_projects=recent_projects,
        events=events,
        stats=stats
    )
#Main Menu
@app.route("/main")
@login_required
def main_menu():
        return render_template("main_menu.html")

# ---- Clients CRUD (minimal) ----
@app.route("/clients")
@login_required
@employee_required  #  changes: Only employees can manage clients
def clients():
    return render_template("clients.html", clients=Client.query.all())

@app.route("/clients/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create clients
def clients_create():
    name = request.form["name"].strip()
    contact = request.form.get("contact","").strip()
    phone = request.form.get("phone","").strip()
    if not name:
        flash("Client name required", "warning")
    else:
        db.session.add(Client(name=name, contact=contact, phone=phone))
        db.session.commit()
        flash("Client added", "success")
    return redirect(url_for("clients"))
    
@app.route("/clients/<int:id>/update", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can update clients
def clients_update(id):
    c = Client.query.get_or_404(id)
    c.name = request.form["name"].strip()
    c.contact = request.form.get("contact", "").strip()
    c.phone = request.form.get("phone", "").strip()
    db.session.commit()
    flash("Client updated successfully.", "success")
    return redirect(url_for("clients"))
    
@app.route("/clients/<int:id>/delete", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete clients
def clients_delete(id):
    """Delete a client unless they still have projects."""
    c = Client.query.get_or_404(id)

    # Safety: prevent deleting clients who still have projects
    if Project.query.filter_by(client_id=c.id).count() > 0:
        flash("Cannot delete: this client still has projects.", "warning")
        return redirect(url_for("clients"))

    db.session.delete(c)
    db.session.commit()
    flash("Client deleted successfully.", "info")
    return redirect(url_for("clients"))
    
# ---- Buildings CRUD (minimal) ----
@app.route("/buildings")
@login_required
@employee_required  #  changes: Only employees can manage buildings
def buildings():
    return render_template("buildings.html", buildings=Building.query.all())

@app.route("/buildings/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create buildings
def buildings_create():
    name = request.form["name"].strip()
    street = request.form.get("street", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    zipc = request.form.get("zip", "").strip()
    notes = request.form.get("notes", "").strip()
    if not name:
        flash("Building name required", "warning")
    else:
        b = Building(name=name, street=street, city=city, state=state, zip=zipc, notes=notes)
        db.session.add(b); db.session.commit()
        flash("Building added", "success")
    return redirect(url_for("buildings"))

@app.route("/buildings/<int:id>/update", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can update buildings
def buildings_update(id):
    b = Building.query.get_or_404(id)
    b.name = request.form["name"].strip()
    b.street = request.form.get("street", "").strip()
    b.city = request.form.get("city", "").strip()
    b.state = request.form.get("state", "").strip()
    b.zip = request.form.get("zip", "").strip()
    b.notes = request.form.get("notes", "").strip()
    db.session.commit()
    flash("Building updated", "success")
    return redirect(url_for("buildings"))

@app.route("/buildings/<int:id>/delete", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete buildings
def buildings_delete(id):
    b = Building.query.get_or_404(id)
    db.session.delete(b); db.session.commit()
    flash("Building deleted", "info")
    return redirect(url_for("buildings"))

# ---- Projects CRUD (minimal) ----
@app.route("/projects")
@login_required
def projects():
    #  changes: Filter projects based on user role
    q = request.args.get("q", "").strip()
    
    if current_user.role == 'employee':
        # Employees see all projects
        query = Project.query.join(Client, isouter=True)
    else:
        # Clients only see assigned projects
        assigned_project_ids = [pa.project_id for pa in current_user.project_assignments]
        if not assigned_project_ids:
            # No projects assigned, show empty list
            return render_template("projects.html", projects=[], q=q, clients=Client.query.all())
        query = Project.query.join(Client, isouter=True).filter(Project.id.in_(assigned_project_ids))

    if q:
        query = query.filter(
            or_(
                Project.name.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%"),
                Client.name.ilike(f"%{q}%")
            )
        )

    projects = query.order_by(Project.id.desc()).all()
    #  changes: Pass all users to template for client assignment dropdown
    all_users = User.query.filter_by(role='client').all() if current_user.role == 'employee' else []
    return render_template("projects.html", projects=projects, q=q, clients=Client.query.all(), users=all_users)

@app.route("/projects/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create projects
def projects_create():
    name = request.form["name"].strip()
    client_id = request.form.get("client_id")
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()
    status = request.form.get("status", "Planned").strip()

    if not name:
        flash("Project name required", "warning")
        return redirect(url_for("projects"))

    # --- create Project ---
    p = Project(
        name=name,
        client_id=int(client_id) if client_id else None,
        description=description,
        status=status,
        due_date=datetime.fromisoformat(due_date).date() if due_date else None,
    )
    db.session.add(p)
    db.session.flush()  # ensures p.id exists

    # --- log Activity ---
    new_activity = Activity(user_id=current_user.id, project_id=p.id)
    db.session.add(new_activity)

    db.session.commit()
    flash("Project created", "success")
    return redirect(url_for("projects"))

    
@app.route("/projects/<int:id>/delete", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete projects
def projects_delete(id):
    """Delete a project unless it still has events."""
    p = Project.query.get_or_404(id)

    # Safety: prevent deleting projects that have events
    if Event.query.filter_by(project_id=p.id).count() > 0:
        flash("Cannot delete: this project still has events.", "warning")
        return redirect(url_for("projects"))
    
    Activity.query.filter_by(project_id=p.id).delete(synchronize_session=False)

    db.session.delete(p)
    db.session.commit()
    flash("Project deleted successfully.", "info")
    return redirect(url_for("projects"))
    
#Events
@app.route("/events")
@login_required  #  changes: Allow both employees and clients to view events
def events():
    #  changes: Filter events based on user role
    if current_user.role == 'employee':
        #  changes: Employees see all events
        events_list = Event.query.order_by(Event.start.desc()).all()
        projects_list = Project.query.all()
    else:
        #  changes: Clients only see events for their assigned projects
        assigned_project_ids = [pa.project_id for pa in current_user.project_assignments]
        if assigned_project_ids:
            events_list = Event.query.filter(Event.project_id.in_(assigned_project_ids)).order_by(Event.start.desc()).all()
            projects_list = Project.query.filter(Project.id.in_(assigned_project_ids)).all()
        else:
            events_list = []
            projects_list = []
    
    return render_template("events.html", events=events_list, projects=projects_list)

@app.route("/events/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create events
def events_create():
    title = request.form["title"].strip()
    event_type = request.form.get("event_type")
    project_id = request.form.get("project_id")
    start = request.form.get("start")
    end = request.form.get("end", "").strip()
    notes = request.form.get("notes", "").strip()
    
    if not title or not start:
        flash("Title and start are required", "warning")
    else:
        ev = Event(
            title=title,
            event_type=event_type,
            project_id=int(project_id) if project_id else None,
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end) if end else None,
            notes=notes
        )
        db.session.add(ev)
        db.session.commit()
        flash("Event created", "success")
    return redirect(url_for("events"))

@app.route("/events/edit/<int:event_id>", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can edit events
def events_edit(event_id):
    event = Event.query.get_or_404(event_id)
    event.title = request.form["title"].strip()
    event.event_type = request.form.get("event_type")
    event.project_id = request.form.get("project_id")
    event.start = datetime.fromisoformat(request.form["start"])
    end = request.form.get("end", "").strip()
    event.end = datetime.fromisoformat(end) if end else None
    event.notes = request.form.get("notes", "").strip()
    db.session.commit()
    flash("Event updated successfully.", "success")
    return redirect(url_for("events"))

@app.route("/events/delete/<int:event_id>", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete events
def events_delete(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "info")
    return redirect(url_for("events"))
#Generate Invoice and Proposal
#Invoice route
@app.route("/project/<int:id>/generate_invoice")
def generate_invoice(id):
    project = Project.query.get_or_404(id)
    invoice_text = build_invoice_text(project)
    current_date = datetime.now().strftime("%m/%d/%Y")
    project_number = "2025-37"  # placeholder
    return render_template(
        "invoice.html", 
        project=project, 
        invoice_text=invoice_text, 
        current_date=current_date,
        project_number=project_number
    )
#Proposal route
@app.route("/project/<int:id>/generate_proposal")
def generate_proposal(id):
    project = Project.query.get_or_404(id)
    proposal_text = build_proposal_text(project)
    current_date = datetime.now().strftime("%m/%d/%Y")  # Add current date
    project_number = "2025-37"  # placeholder
    return render_template(
        "proposal.html",
        project=project,
        proposal_text=proposal_text,
        current_date=current_date,
        project_number=project_number
    )

def build_invoice_text(project):
    #later you can replace this with a call to an AI API
    return (
        f"Invoice for project '{project.name}'\n\n"
        f"Client: {project.client.name if project.client else 'N/A'}\n"
        f"Description: {project.description or 'No description provided.'}\n"
        f"Status: {project.status}\n"
    )

def build_proposal_text(project):
    return (
        f"Proposal for {project.name}\n\n"
        f"This document outlines the proposed architectural services for "
        f"{project.client.name if project.client else 'the client'}. "
        "The scope includes design coordination, site review, and documentation. "
        "Fees and schedule to be confirmed upon client approval."
    )

#when ready to use ai, use line below and replace bodies  of two functions above
#return call_ai_api(prompt)

#  changes: User Management Routes (Employee Only)
@app.route("/admin/users")
@login_required
@employee_required
def admin_users():
    """View and manage all users (employees only)"""
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/change_role", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can change user roles
def change_user_role(user_id):
    """Change a user's role between client and employee"""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    
    if new_role not in ['client', 'employee']:
        flash("Invalid role specified.", "danger")
        return redirect(url_for("admin_users"))
    
    user.role = new_role
    db.session.commit()
    flash(f"User {user.name} role changed to {new_role}.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete users
def delete_user(user_id):
    """Delete a user account"""
    user = User.query.get_or_404(user_id)
    
    #  changes: Prevent deleting yourself
    if user.id == current_user.id:
        flash("Cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))
    
    #  changes: Check if user has project assignments
    assignment_count = ProjectAssignment.query.filter_by(user_id=user_id).count()
    if assignment_count > 0:
        flash(f"Cannot delete: {user.name} is assigned to {assignment_count} project(s). Remove assignments first.", "warning")
        return redirect(url_for("admin_users"))
    
    #  changes: Check if user has activities
    activity_count = Activity.query.filter_by(user_id=user_id).count()
    if activity_count > 0:
        flash(f"Cannot delete: {user.name} has {activity_count} activity record(s) in the system.", "warning")
        return redirect(url_for("admin_users"))
    
    user_name = user.name
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user_name} deleted successfully.", "info")
    return redirect(url_for("admin_users"))

@app.route("/admin/projects/<int:project_id>/assign", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can assign clients to projects
def assign_client_to_project(project_id):
    """Assign a client user to a project"""
    project = Project.query.get_or_404(project_id)
    user_id = request.form.get("user_id")
    
    if not user_id:
        flash("Please select a user.", "warning")
        return redirect(url_for("projects"))
    
    user = User.query.get_or_404(int(user_id))
    
    #  changes: Check if already assigned
    existing = ProjectAssignment.query.filter_by(project_id=project_id, user_id=user_id).first()
    if existing:
        flash(f"{user.name} is already assigned to this project.", "info")
        return redirect(url_for("projects"))
    
    #  changes: Create assignment
    assignment = ProjectAssignment(project_id=project_id, user_id=user_id)
    db.session.add(assignment)
    db.session.commit()
    flash(f"{user.name} assigned to {project.name}.", "success")
    return redirect(url_for("projects"))

@app.route("/admin/projects/<int:project_id>/unassign/<int:user_id>", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can unassign clients from projects
def unassign_client_from_project(project_id, user_id):
    """Remove a client user from a project"""
    assignment = ProjectAssignment.query.filter_by(project_id=project_id, user_id=user_id).first_or_404()
    user_name = assignment.user.name
    project_name = assignment.project.name
    
    db.session.delete(assignment)
    db.session.commit()
    flash(f"{user_name} removed from {project_name}.", "info")
    return redirect(url_for("projects"))

if __name__ == "__main__":
    app.run(debug=True)
# new updated file