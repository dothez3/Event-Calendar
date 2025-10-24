from tkinter import *
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# -------------------------------
# DATABASE CONNECTION
# -------------------------------
def connect_to_database():
    try:
        # Connect without specifying DB to create it if needed
        root_conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1!'  # 👈 change this to your MySQL password
        )
        cursor = root_conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS ArchitectureDB;")
        print("✅ Database checked/created successfully")
        root_conn.close()

        # Connect to the actual database
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1!',
            database='ArchitectureDB'
        )
        print("✅ Connected to ArchitectureDB")
        return connection

    except Error as e:
        print(f"❌ Error: {e}")
        return None


# -------------------------------
# DATABASE INITIALIZATION (TABLES) street_number VARCHAR(10),postal_code VARCHAR(20),country VARCHAR(50)
# -------------------------------






def initialize_database(connection):
    try:
        cursor = connection.cursor()

        # Address Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Address (
            address_id INT AUTO_INCREMENT PRIMARY KEY,
            street_address VARCHAR(100),
            city VARCHAR(50),
            state VARCHAR(50)
        );
        """)

        # Project Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Project (
            project_number INT AUTO_INCREMENT PRIMARY KEY,
            address_id INT,
            client VARCHAR(100),
            client_phone VARCHAR(20),
            client_email VARCHAR(100),
            size ENUM('S', 'M', 'L'),
            start_date DATE,
            last_interaction_date DATE,
            employee_creator VARCHAR(100),
            FOREIGN KEY (address_id) REFERENCES Address(address_id),
            M1 INT DEFAULT 0,
            M2 INT DEFAULT 0,
            M3 INT DEFAULT 0
        );
        """)

        connection.commit()
        print("✅ Tables checked/created successfully")

    except Error as e:
        print(f"❌ Error creating tables: {e}")











# -------------------------------
# DO NOT USE THIS CODE, IT WILL DELETE THE DATABASE. LEAVE AS QUOTES UNLESS ABSOLUTELY NECESSARY
# -------------------------------
'''
import mysql.connector
from mysql.connector import Error

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root1!'  # ← your MySQL password
    )
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS ArchitectureDB;")
    print("✅ Database 'ArchitectureDB' dropped successfully!")

except Error as e:
    print(f"❌ Error: {e}")

finally:
    if conn.is_connected():
        cursor.close()
        conn.close()

'''












# -------------------------------
# ADD PROJECT FUNCTION
# -------------------------------
def addProject():
    conn = connect_to_database()
    if conn is None:
        print("Database connection failed.")
        return

    initialize_database(conn)
    cursor = conn.cursor()

    # Get data from GUI fields
    street_address = entry_street_address.get()
    city = entry_city.get()
    state = entry_state.get()

    client = entry_client.get()
    client_phone = entry_clientPhone.get()
    client_email = entry_clientEmail.get()

    size = entry_size.get().upper()
    startDate = datetime.now().strftime("%Y-%m-%d")
    lastWorkedOn = startDate
    employee = "Edwin"

    try:
        # Insert into Address
        insert_address = """
            INSERT INTO Address (street_address, city, state)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_address, (street_address, city, state))
        address_id = cursor.lastrowid

        # Insert into Project
        insert_project = """
            INSERT INTO Project (address_id, client, client_phone, client_email, size, start_date, last_interaction_date, employee_creator)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_project, (address_id, client, client_phone, client_email, size, startDate, lastWorkedOn, employee))

        conn.commit()
        print("✅ New project added successfully!")

        from tkinter import messagebox
        messagebox.showinfo("Success", "New project added successfully!")

    except Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()


# -------------------------------
# VIEW PROJECTS FUNCTION
# -------------------------------


from tkinter import *
from tkinter import ttk, messagebox
from mysql.connector import Error
from datetime import datetime

def viewProjects():
    conn = connect_to_database()
    if conn is None:
        print("Database connection failed.")
        return

    cursor = conn.cursor()

    try:
        # Join Project and Address tables
        cursor.execute("""
            SELECT 
                p.project_number,
                p.client,
                p.client_phone,
                p.client_email,
                p.size,
                p.start_date,
                p.last_interaction_date,
                p.employee_creator,
                a.street_address,
                a.city,
                a.state,
                p.M1,
                p.M2,
                p.M3  
                         
            FROM Project p
            JOIN Address a ON p.address_id = a.address_id;
        """)


        results = cursor.fetchall()

        if not results:
            messagebox.showinfo("No Data", "No projects found in the database.")
            return

        # --- Create main popup window ---
        popup = Toplevel(application)
        popup.title("All Projects")
        popup.geometry("1000x400")

        # --- Create Treeview widget ---
        columns = (
            "Project #", "Client", "Phone", "Email", "Size", "Start Date", "Last Updated",
            "Employee", "Street", "City", "State", "Postal", "Country"
        )
        tree = ttk.Treeview(popup, columns=columns, show='headings', selectmode='browse')
        tree.pack(fill=BOTH, expand=True)

        # Set column headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor=CENTER)

        # Insert data into Treeview
        for row in results:
            tree.insert("", "end", values=row)

        # --- Add scrollbar ---
        scrollbar = ttk.Scrollbar(popup, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        # --- Define function to open detail window ---
        def open_project_details(event):
            selected_item = tree.selection()
            if not selected_item:
                return

            # Extract row values
            project_data = tree.item(selected_item[0], "values")
            openProjectDetailsWindow(project_data)

        # Bind double-click event
        tree.bind("<Double-1>", open_project_details)

    except Error as e:
        print(f"❌ Database error while fetching data: {e}")

    finally:
        cursor.close()
        conn.close()






def openProjectDetailsWindow(project_data):
    # Create a new popup window
    detail_win = Toplevel(application)
    detail_win.title(f"Project Details — #{project_data[0]}")
    detail_win.geometry("500x600")

    # Labels for the project details
    labels = [
        "Project Number", "Client", "Phone", "Email", "Size", "Start Date",
        "Last Interaction", "Employee", "Street", "City", "State"
    ]

    # Display project details in a grid layout
    for i, label in enumerate(labels):
        Label(detail_win, text=f"{label}:", font=("Arial", 10, "bold")).grid(
            row=i, column=0, sticky="e", padx=10, pady=5
        )
        Label(detail_win, text=str(project_data[i])).grid(
            row=i, column=1, sticky="w", padx=10, pady=5
        )

    # --- Divider / Title for Project Tasks ---
    Label(detail_win, text="--- Project Tasks ---", font=("Arial", 12, "bold")).grid(
        row=len(labels) + 1, column=0, columnspan=2, pady=10
    )

    m1 = int(project_data[11])
    m2 = int(project_data[12])
    m3 = int(project_data[13])
    
    # Check M1, M2, M3 values from project_data
    m1 = int(project_data[11]) if len(project_data) > 11 else 0
    m2 = int(project_data[12]) if len(project_data) > 12 else 0
    m3 = int(project_data[13]) if len(project_data) > 13 else 0

    # Proposal Button (M1)
    Proposal = Button(detail_win, text='Proposal sent to client', bg="#00ff00" if m1 == 1 else "#f0f0f0")
    Proposal.grid(row=len(labels) + 2, column=0, columnspan=2, pady=5, sticky="ew")
    Proposal.config(command=lambda: taskDone(Proposal, project_data[0], 'M1'))

    # Survey Button (M2)
    Survey = Button(detail_win, text='Survey of building completed', bg="#00ff00" if m2 == 1 else "#f0f0f0")
    Survey.grid(row=len(labels) + 3, column=0, columnspan=2, pady=5, sticky="ew")
    Survey.config(command=lambda: taskDone(Survey, project_data[0], 'M2'))

    # Asbuilt Button (M3)
    Asbuilt = Button(detail_win, text='Asbuilt finished', bg="#00ff00" if m3 == 1 else "#f0f0f0")
    Asbuilt.grid(row=len(labels) + 4, column=0, columnspan=2, pady=5, sticky="ew")
    Asbuilt.config(command=lambda: taskDone(Asbuilt, project_data[0], 'M3'))



    # --- Close Button ---
    Button(
        detail_win, text="Close", command=detail_win.destroy, bg="#e74c3c", fg="white"
    ).grid(row=len(labels) + 5, column=0, columnspan=2, pady=15, ipadx=5)










# -------------------------------
# TASK BUTTON COLOR CHANGE
# -------------------------------
def taskDone(button, project_number, column, tree=None, tree_item=None):
    """
    Updates the project table column (M1, M2, M3) to 1 and changes the button color.
    Optionally updates the Treeview immediately.

    :param button: Tkinter button
    :param project_number: Project ID
    :param column: Column to update ('M1', 'M2', 'M3')
    :param tree: Optional Treeview widget
    :param tree_item: Optional Treeview item ID
    """
    button.config(bg="#00ff00")  # turn button green

    # Update database
    conn = connect_to_database()
    if conn is None:
        return
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE Project SET {column} = 1 WHERE project_number = %s", (project_number,))
        conn.commit()
        print(f"✅ {column} for project #{project_number} set to 1")
    except Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    # Update Treeview immediately if provided
    if tree is not None and tree_item is not None:
        values = list(tree.item(tree_item, "values"))
        # M1, M2, M3 are at the end of the row
        if column == "M1":
            values[11] = 1
        elif column == "M2":
            values[12] = 1
        elif column == "M3":
            values[13] = 1
        tree.item(tree_item, values=values)



# -------------------------------
# TKINTER UI
# -------------------------------
application = Tk()
application.title("Architecture Project Tracker")
application.geometry("400x500")

Label(application, text="--- Address Information ---", font=("Arial", 12, "bold")).pack(pady=5)

Label(application, text="Street Addrress").pack()
entry_street_address = Entry(application)
entry_street_address.pack()

Label(application, text="City").pack()
entry_city = Entry(application)
entry_city.pack()

Label(application, text="State").pack()
entry_state = Entry(application)
entry_state.pack()

Label(application, text="--- Project Information ---", font=("Arial", 12, "bold")).pack(pady=5)
Label(application, text="Client Name").pack()
entry_client = Entry(application)
entry_client.pack()

Label(application, text="Client Phone").pack()
entry_clientPhone = Entry(application)
entry_clientPhone.pack()

Label(application, text="Client Email").pack()
entry_clientEmail = Entry(application)
entry_clientEmail.pack()

Label(application, text="Project Size (S/M/L)").pack()
entry_size = Entry(application)
entry_size.pack()

createProjectButton = Button(application, text='Create New Project', command=addProject, bg="#4CAF50", fg="white")
createProjectButton.pack(pady=10)

viewProjectButton = Button(application, text='View New Project', command=viewProjects, bg="#4CAF50", fg="white")
viewProjectButton.pack(pady=10)

application.mainloop()
