from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import date, datetime

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
    # Address fields - added for better client information management
    street = db.Column(db.String(120))
    city = db.Column(db.String(80))
    state = db.Column(db.String(20))
    zip = db.Column(db.String(20))
    
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
    building_id = db.Column(db.Integer, db.ForeignKey("building.id"))  # NEW
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="Planned")
    due_date = db.Column(db.Date)
    client = db.relationship("Client", backref="projects")
    building = db.relationship("Building", backref="projects")  # NEW

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



class TimeEntry(db.Model):
    __tablename__ = 'time_entry'  
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', backref='time_entries')
    user = db.relationship('User', backref='time_entries')



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

#  changes: New Notification model for client-to-employee communication
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # None = broadcast to all employees, non-null = direct to one employee
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    sender = db.relationship('User',
                             foreign_keys=[sender_id],
                             backref='sent_notifications')
    recipient = db.relationship('User',
                                foreign_keys=[recipient_id],
                                backref='received_notifications')
    project = db.relationship('Project', backref='notifications')

#CLI to init DB
@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    
    # Seed demo user
    if not User.query.filter_by(email="demo@pms.local").first():
        u = User(email="demo@pms.local", name="Demo User", role="employee")  #  changes: Set demo user as employee
        u.set_password("demo123")
        db.session.add(u)
    
    # Add multiple clients with addresses (their home/office addresses - where they receive mail)
    c1 = Client(
        name="Bruce Wayne", 
        contact="bwayne.enterprises@gmail.com", 
        phone="555-01234",
        street="Wayne Enterprises, 1 Wayne Tower",  # His corporate office
        city="Gotham",
        state="NJ",
        zip="08402"
    )
    c2 = Client(
        name="Tony Stark", 
        contact="tstark@starkindustries.com", 
        phone="555-99999",
        street="10880 Malibu Point",  # His Malibu house (different from project site)
        city="Malibu",
        state="CA",
        zip="90265"
    )
    c3 = Client(
        name="Peter Parker", 
        contact="pparker@dailybugle.com", 
        phone="555-77777",
        street="178 Bleecker Street",  # His apartment (different from project site)
        city="New York",
        state="NY",
        zip="10012"
    )
    db.session.add_all([c1, c2, c3])
    
    # Add multiple buildings
    b1 = Building(name="Wayne Manor", street="1007 Mountain Drive", city="Gotham", state="NJ", zip="08401")
    b2 = Building(name="Stark Tower", street="200 Park Avenue", city="New York", state="NY", zip="10166")
    b3 = Building(name="Parker Residence", street="20 Ingram Street", city="Queens", state="NY", zip="11375")
    db.session.add_all([b1, b2, b3])
    
    # Commit buildings first so they have IDs
    db.session.commit()
    
    # Add multiple projects (NOW with building links)
    p1 = Project(name="Wayne Residential Complex", client=c1, building=b1, description="Luxury residential development", status="In Progress", due_date=datetime(2025,12,23).date())
    p2 = Project(name="Stark Industries HQ Renovation", client=c2, building=b2, description="Modern office renovation", status="Planned", due_date=datetime(2026,3,15).date())
    p3 = Project(name="Parker Family Home Remodel", client=c3, building=b3, description="Small home renovation project", status="In Progress", due_date=datetime(2025,11,30).date())
    db.session.add_all([p1, p2, p3])
    
    # Add multiple events
    e1 = Event(title="Pre-Construction Planning", event_type="Client Meeting", project=p1, start=datetime(2025,11,13,12,31))
    e2 = Event(title="Site Inspection", event_type="Survey", project=p1, start=datetime(2025,11,20,9,0), end=datetime(2025,11,20,11,0))
    e3 = Event(title="Blueprint Review", event_type="Design", project=p2, start=datetime(2025,11,25,14,0))
    db.session.add_all([e1, e2, e3])
    
    db.session.commit()
    print("Initialized the database. Login with demo@pms.local / demo123")

from sqlalchemy import or_, func, desc  # add this import at the top

#Routes
# Made client_login the default login page for all users
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
    
    #client_login template as the unified login page
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
        
        # Unified registration redirect to single login page
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("index"))
    
    return render_template("register.html", account_type=account_type)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    now = datetime.now()

    if current_user.role == 'employee':
        recent_projects = (
            db.session.query(Project)
            .join(Activity, Activity.project_id == Project.id)
            .filter(Activity.user_id == current_user.id)
            .order_by(desc(Activity.happened_at))
            .limit(6)
            .all()
        )

        base_events = Event.query.order_by(Event.start.desc()).all()

    else:
        assigned_ids = [pa.project_id for pa in current_user.project_assignments]

        if assigned_ids:
            recent_projects = (
                Project.query
                .filter(Project.id.in_(assigned_ids))
                .limit(6)
                .all()
            )

            base_events = (
                Event.query
                .filter(Event.project_id.in_(assigned_ids))
                .order_by(Event.start.desc())
                .all()
            )
        else:
            recent_projects = []
            base_events = []

    recent_events = [e for e in base_events if e.start <= now][:5]
    future_events = sorted([e for e in base_events if e.start > now], key=lambda e: e.start)[:5]

    return render_template(
        "dashboard.html",
        recent_projects=recent_projects,
        recent_events=recent_events,
        future_events=future_events
    )

#Main Menu
@app.route("/main")
@login_required
def main_menu():
        return render_template("main_menu.html")

# ---- Clients CRUD ----
@app.route("/clients")
@login_required
@employee_required  #  changes: Only employees can manage clients
def clients():
    # Get search query and sort option from URL parameters
    search_query = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "name")  # Default sort by name
    
    # Start with base query
    query = Client.query
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            or_(
                Client.name.ilike(f"%{search_query}%"),
                Client.contact.ilike(f"%{search_query}%"),
                Client.phone.ilike(f"%{search_query}%"),
                Client.street.ilike(f"%{search_query}%"),
                Client.city.ilike(f"%{search_query}%"),
                Client.state.ilike(f"%{search_query}%"),
                Client.zip.ilike(f"%{search_query}%")
            )
        )
    
    # Apply sorting
    if sort_by == "name":
        query = query.order_by(Client.name)
    elif sort_by == "city":
        query = query.order_by(Client.city)
    elif sort_by == "state":
        query = query.order_by(Client.state)
    
    clients_list = query.all()
    
    # Count projects for each client
    for client in clients_list:
        client.project_count = Project.query.filter_by(client_id=client.id).count()
    
    return render_template("clients.html", clients=clients_list, search_query=search_query, sort_by=sort_by)

@app.route("/clients/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create clients
def clients_create():
    name = request.form["name"].strip()
    contact = request.form.get("contact","").strip()
    phone = request.form.get("phone","").strip()
    # Get address fields from form
    street = request.form.get("street","").strip()
    city = request.form.get("city","").strip()
    state = request.form.get("state","").strip()
    zip_code = request.form.get("zip","").strip()
    
    if not name:
        flash("Client name required", "warning")
    else:
        # Create client with all fields including address
        db.session.add(Client(
            name=name, 
            contact=contact, 
            phone=phone,
            street=street,
            city=city,
            state=state,
            zip=zip_code
        ))
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
    # Update address fields
    c.street = request.form.get("street", "").strip()
    c.city = request.form.get("city", "").strip()
    c.state = request.form.get("state", "").strip()
    c.zip = request.form.get("zip", "").strip()
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

@app.route("/clients/<int:id>")
@login_required
@employee_required  #  changes: Only employees can view client details
def client_detail(id):
    """View detailed information about a specific client"""
    client = Client.query.get_or_404(id)
    
    # Get all projects for this client
    projects = Project.query.filter_by(client_id=id).all()
    
    # Get all events related to this client's projects
    project_ids = [p.id for p in projects]
    events = Event.query.filter(Event.project_id.in_(project_ids)).order_by(Event.start.desc()).all() if project_ids else []
    
    # Calculate stats
    total_projects = len(projects)
    active_projects = len([p for p in projects if p.status == "In Progress"])
    completed_projects = len([p for p in projects if p.status == "Done"])
    upcoming_events = len([e for e in events if e.start > datetime.now()])
    
    stats = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'upcoming_events': upcoming_events
    }
    
    return render_template("client_detail.html", 
                         client=client, 
                         projects=projects, 
                         events=events,
                         stats=stats)
    
# ---- Buildings CRUD (minimal) ----
@app.route("/buildings")
@login_required
@employee_required  #  changes: Only employees can manage buildings
def buildings():
    """Display all buildings with optional search and sort"""
    search_query = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "name")  # Default sort by name
    
    # Start with base query
    query = Building.query
    
    # Apply search filter if provided
    if search_query:
        query = query.filter(
            or_(
                Building.name.ilike(f"%{search_query}%"),
                Building.street.ilike(f"%{search_query}%"),
                Building.city.ilike(f"%{search_query}%"),
                Building.state.ilike(f"%{search_query}%"),
                Building.zip.ilike(f"%{search_query}%")
            )
        )
    
    # Apply sorting
    if sort_by == "name":
        query = query.order_by(Building.name)
    elif sort_by == "city":
        query = query.order_by(Building.city)
    elif sort_by == "state":
        query = query.order_by(Building.state)
    
    buildings_list = query.all()
    
    return render_template("buildings.html", 
                         buildings=buildings_list,
                         search_query=search_query,
                         sort_by=sort_by)

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
    sort_by = request.args.get("sort", "name")  # Get sort parameter, default to 'name'
    page = request.args.get("page", 1, type=int)  # Get page number, default to 1
    per_page = 15  # Projects per page
    
    if current_user.role == 'employee':
        # Employees see all projects
        query = Project.query.join(Client, isouter=True)
    else:
        # Clients only see assigned projects
        assigned_project_ids = [pa.project_id for pa in current_user.project_assignments]
        if not assigned_project_ids:
            # No projects assigned, show empty list
            return render_template("projects.html", projects=[], pagination=None, q=q, sort_by=sort_by, clients=Client.query.all(), buildings=Building.query.all(), users=[])
        query = Project.query.join(Client, isouter=True).filter(Project.id.in_(assigned_project_ids))

    # Apply search filter
    if q:
        query = query.filter(
            or_(
                Project.name.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%"),
                Client.name.ilike(f"%{q}%")
            )
        )

    # Apply sorting
    if sort_by == "name":
        query = query.order_by(Project.name)
    elif sort_by == "due_date":
        query = query.order_by(Project.due_date.desc().nullslast())
    elif sort_by == "status":
        query = query.order_by(Project.status)
    elif sort_by == "client":
        query = query.order_by(Client.name.nullslast())
    else:
        query = query.order_by(Project.id.desc())  # Default fallback

    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    projects = pagination.items
    
    # Mark overdue projects
    from datetime import date
    today = date.today()
    for project in projects:
        if project.due_date and project.due_date < today and project.status != "Done":
            project.is_overdue = True
        else:
            project.is_overdue = False
    
    # MERGED: Pass all users to template for client assignment dropdown (your feature)
    # AND pass buildings for building associations (teammate's feature)
    all_users = User.query.filter_by(role='client').all() if current_user.role == 'employee' else []
    return render_template("projects.html", projects=projects, pagination=pagination, q=q, sort_by=sort_by, clients=Client.query.all(), buildings=Building.query.all(), users=all_users)

@app.route("/projects/create", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can create projects
def projects_create():
    name = request.form["name"].strip()
    client_id = request.form.get("client_id")
    building_id = request.form.get("building_id")  # NEW
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
        building_id=int(building_id) if building_id else None,  # NEW
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

@app.route("/projects/<int:id>/update", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can update projects
def projects_update(id):
    """Update project information"""
    p = Project.query.get_or_404(id)
    
    p.name = request.form.get("name", "").strip()
    p.status = request.form.get("status", "Planned")
    p.description = request.form.get("description", "").strip() or None
    
    # Handle due date
    due_str = request.form.get("due_date", "").strip()
    if due_str:
        p.due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
    else:
        p.due_date = None
    
    # Handle client
    client_id = request.form.get("client_id", "").strip()
    p.client_id = int(client_id) if client_id else None
    
    # Handle building
    building_id = request.form.get("building_id", "").strip()
    p.building_id = int(building_id) if building_id else None
    
    db.session.commit()
    flash("Project updated successfully!", "success")
    return redirect(url_for("project_detail", id=id))

@app.route("/projects/<int:id>")
@login_required
def project_detail(id):
    """View detailed information about a specific project"""
    project = Project.query.get_or_404(id)
    
    # Check permissions - employees see all, clients only see assigned projects
    if current_user.role == 'client':
        # Check if this client user is assigned to this project
        assignment = ProjectAssignment.query.filter_by(project_id=id, user_id=current_user.id).first()
        if not assignment:
            flash("Access denied. You are not assigned to this project.", "danger")
            return redirect(url_for("dashboard"))
    
    # Get all events for this project
    events = Event.query.filter_by(project_id=id).order_by(Event.start.desc()).all()
    
    # Get assigned users (client users)
    assigned_users = [assignment.user for assignment in project.assignments]
    
    # Get all clients and buildings for edit form (employees only)
    clients = Client.query.order_by(Client.name).all() if current_user.role == 'employee' else []
    buildings = Building.query.order_by(Building.name).all() if current_user.role == 'employee' else []
    
    # Calculate stats
    total_events = len(events)
    upcoming_events = len([e for e in events if e.start > datetime.now()])
    
    # Days until due date - ONLY calculate if project is NOT done
    days_until_due = None
    if project.due_date and project.status != "Done":
        delta = project.due_date - datetime.now().date()
        days_until_due = delta.days
    
    stats = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'days_until_due': days_until_due,
        'status': project.status
    }

    time_entries = TimeEntry.query.filter_by(project_id=id).all()
    total_hours = sum(entry.hours for entry in time_entries)
    
    return render_template("project_detail.html",
                         project=project,
                         events=events,
                         assigned_users=assigned_users,
                         clients=clients,
                         buildings=buildings,
                         stats=stats,
                         time_entries=time_entries,
                         total_hours=total_hours)
    
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

#  changes: Notification Routes for client-to-employee communication
@app.route("/notifications")
@login_required
@employee_required
def notifications():
    """Inbox for employees: broadcast client messages + direct employee messages"""

    base_query = Notification.query.filter(
        or_(
            Notification.recipient_id == current_user.id,   # direct to me
            Notification.recipient_id.is_(None)             # broadcast
        )
    )

    notifications = base_query.order_by(Notification.created_at.desc()).all()
    unread_count = base_query.filter_by(is_read=False).count()

    # list of employees for the "send to employee" dropdown
    employees = User.query.filter_by(role="employee").order_by(User.name).all()

    return render_template(
        "notifications.html",
        notifications=notifications,
        unread_count=unread_count,
        employees=employees,
    )

@app.route("/notifications/send", methods=["POST"])
@login_required
@employee_required
def notifications_send():
    """Send an internal message from one employee to another"""
    recipient_id = request.form.get("recipient_id")
    message = request.form.get("message", "").strip()
    project_id = request.form.get("project_id")  # optional hidden field, can stay empty

    if not recipient_id or not message:
        flash("Recipient and message are required.", "warning")
        return redirect(url_for("notifications"))

    n = Notification(
        sender_id=current_user.id,
        recipient_id=int(recipient_id),
        project_id=int(project_id) if project_id else None,
        message=message,
        is_read=False,
    )

    db.session.add(n)
    db.session.commit()
    flash("Message sent to employee.", "success")
    return redirect(url_for("notifications"))

@app.route("/notifications/create", methods=["POST"])
@login_required
def notifications_create():
    """Create a new notification (clients send broadcast to all employees)"""
    message = request.form.get("message", "").strip()
    project_id = request.form.get("project_id")

    if not message:
        flash("Message cannot be empty.", "warning")
        return redirect(request.referrer or url_for("dashboard"))

    notification = Notification(
        sender_id=current_user.id,
        recipient_id=None,  # broadcast to all employees
        project_id=int(project_id) if project_id else None,
        message=message,
        is_read=False,
    )
    db.session.add(notification)
    db.session.commit()

    flash("Notification sent successfully!", "success")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/notifications/<int:notification_id>/mark-read", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can mark as read
def notification_mark_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return redirect(url_for("notifications"))

@app.route("/notifications/<int:notification_id>/delete", methods=["POST"])
@login_required
@employee_required  #  changes: Only employees can delete notifications
def notification_delete(notification_id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(notification_id)
    db.session.delete(notification)
    db.session.commit()
    flash("Notification deleted.", "info")
    return redirect(url_for("notifications"))

@app.route("/notifications/mark-all-read", methods=["POST"])
@login_required
@employee_required
def notifications_mark_all_read():
    """Mark all notifications in THIS employee's inbox as read"""
    Notification.query.filter(
        Notification.is_read == False,
        or_(
            Notification.recipient_id == None,               # broadcasts
            Notification.recipient_id == current_user.id     # direct to this employee
        )
    ).update({Notification.is_read: True}, synchronize_session=False)

    db.session.commit()
    flash("All your notifications marked as read.", "success")
    return redirect(url_for("notifications"))

@app.route("/notifications/<int:notification_id>")
@login_required
@employee_required
def notification_detail(notification_id):
    """Show one notification with the full message"""
    n = Notification.query.get_or_404(notification_id)

    # Permission check
    if n.recipient_id is not None and n.recipient_id != current_user.id:
        flash("Access denied for this notification.", "danger")
        return redirect(url_for("notifications"))

    # Mark as read when opened
    if not n.is_read:
        n.is_read = True
        db.session.commit()

    return render_template("notification_detail.html", notification=n)

def unread_notification_count():
    if not current_user.is_authenticated or current_user.role != 'employee':
        return 0

    return Notification.query.filter(
        Notification.is_read == False,
        or_(
            Notification.recipient_id == None,
            Notification.recipient_id == current_user.id
        )
    ).count()

@app.context_processor
def inject_notification_count():
    return {
        'unread_notifications': unread_notification_count()
    }


@app.route('/timecard', methods=['GET', 'POST'])
@login_required
def timecard():
    projects = Project.query.all()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        hours = request.form.get('hours')
        description = request.form.get('description')

        if project_id and hours:
            entry = TimeEntry(
                user_id=current_user.id,
                project_id=int(project_id),
                hours=float(hours),
                description=description
            )
            db.session.add(entry)
            db.session.commit()
            flash('Time entry logged!', 'success')
            return redirect(url_for('timecard'))

    return render_template('timecard.html', projects=projects)





if __name__ == "__main__":
    app.run(debug=True)
