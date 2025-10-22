from tkinter import *

def addProject():
    projectNumber = input("Enter project number: ").split()
    buildingAddress = input("Enter building address: ").split()
    client = input("Enter client name: ").split()
    clientnum = input("Enter client phone number: ").split()
    clientemail = input("Enter client email: ").split()
    size = input("Enter estimated size of project: (s, m, l) ").split()
    startDate = 0 #current time of when create project button is clicked
    lastWorkedOn = 0 #last date of events added to this project
    employee = 0 #name of employee signed in when create project button was clicked
    print(projectNumber)
    print(buildingAddress) 
    print(client) 
    print(clientnum)
    print(clientemail)
    print(size)

def taskDone():
    Proposal.config(bg='#FF0000')
    Survey.config(bg='#FF0000')
    Asbuilt.config(bg='#FF0000')
    

application = Tk()

createProjectButton = Button(application, text='Create New Project')
Proposal = Button(application, text='Proposal sent to client')
Survey = Button(application, text='Survey of building completed')
Asbuilt = Button(application, text='Asbuilt finished')

createProjectButton.config(command=addProject)
createProjectButton.pack()

Proposal.config(command=taskDone)
Proposal.pack()

Survey.config(command=taskDone)
Survey.pack()

Asbuilt.config(command=taskDone)
Asbuilt.pack()

application.mainloop()