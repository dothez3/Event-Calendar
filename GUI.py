
from tkinter import *
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- DATABASE CONNECTION ---
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root1!',  # change this
            database='ArchitectureDB'
        )
        if connection.is_connected():
            print("✅ Connected to MySQL Database")
            return connection
    except Error as e:
        print(f"❌ Error: {e}")
        return None

# --- FUNCTIONS ---
def addProject():
    # Connect to DB
    conn = connect_to_database()
    if conn is None:
        print("Database connection failed.")
        return
    cursor = conn.cursor()

    # Get data from form
    projectNumber = entry_projectNumber.get()
    streetAddress = entry_buildingAddress.get()
    client = entry_client.get()
    clientnum = entry_clientnum.get()
    clientemail = entry_clientemail.get()
    size = entry_size.get().upper()
    startDate = datetime.now().strftime("%Y-%m-%d")
    lastWorkedOn = startDate
    employee = "Edwin"  # Example placeholder

    try:
        # Insert address first
        insert_address = """
            INSERT INTO Address (street_name, city, state, postal_code, country)
            VALUES (%s, %s, %s, %s, %s)
        """
        # Here we just fill minimal values for testing
        address_data = (streetAddress, 'Unknown', 'Unknown', '00000', 'USA')
        cursor.execute(insert_address, address_data)
        address_id = cursor.lastrowid  # get auto ID

        # Insert project linked to that address
        insert_project = """
            INSERT INTO Project (address_id, client, size, start_date, last_interaction_date, employee_creator)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        project_data = (address_id, client, size, startDate, lastWorkedOn, employee)
        cursor.execute(insert_project, project_data)

        conn.commit()
        print("✅ New project added to database!")

    except Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

def taskDone(button):
    button.config(bg='#FF0000')

# --- TKINTER UI ---
application = Tk()
application.title("Architecture Project Tracker")
application.geometry("400x400")

Label(application, text="Project Number").pack()
entry_projectNumber = Entry(application)
entry_projectNumber.pack()

Label(application, text="Building Address").pack()
entry_buildingAddress = Entry(application)
entry_buildingAddress.pack()

Label(application, text="Client Name").pack()
entry_client = Entry(application)
entry_client.pack()

Label(application, text="Client Phone Number").pack()
entry_clientnum = Entry(application)
entry_clientnum.pack()

Label(application, text="Client Email").pack()
entry_clientemail = Entry(application)
entry_clientemail.pack()

Label(application, text="Project Size (S/M/L)").pack()
entry_size = Entry(application)
entry_size.pack()

createProjectButton = Button(application, text='Create New Project', command=addProject)
createProjectButton.pack(pady=10)

Label(application, text="Project Tasks").pack(pady=5)

Proposal = Button(application, text='Proposal sent to client', command=lambda: taskDone(Proposal))
Proposal.pack()

Survey = Button(application, text='Survey of building completed', command=lambda: taskDone(Survey))
Survey.pack()

Asbuilt = Button(application, text='Asbuilt finished', command=lambda: taskDone(Asbuilt))
Asbuilt.pack()

application.mainloop()
