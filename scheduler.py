import time
from db import DB_FILE, sqlite3 # We'd need to import db functions

def schedule_3_reminders(appointment_id, scheduled_iso, email, patient_name):
    """
    Simulates the scheduling of 3 automated reminders.
    A real system would add these to a job queue.
    """
    print("\n" + "="*50)
    print(f"--- REMINDER SYSTEM ENGAGED FOR APPOINTMENT {appointment_id} ---")
    
    # We call the functions directly to show what they would do.
    
    print(f"\n[JOB 1] Simulating 1st Reminder (72 hours before):")
    simulate_1st_reminder(appointment_id, email, patient_name)
    
    print(f"\n[JOB 2] Simulating 2nd Reminder (24 hours before):")
    simulate_2nd_reminder(appointment_id, email, patient_name)
    
    print(f"\n[JOB 3] Simulating 3rd Reminder (2 hours before):")
    simulate_3rd_reminder(appointment_id, email, patient_name)
    
    print("\n" + "="*50)

# Simulation Functions 

def simulate_1st_reminder(aid, email, name):
    """(72 hours out) - Regular reminder."""
    print(f"  > ACTION: Sending regular confirmation to {email} for {name}.")
    print(f"  > EMAIL BODY: 'Hi {name}, this is a reminder for your appt (ID: {aid}).'")

def simulate_2nd_reminder(aid, email, name):
    """(24 hours out) - Check forms and confirmation."""
    
    # 1. Check if form is filled (Simulated DB check)
    form_filled = check_if_form_is_filled(aid) 
    
    if not form_filled:
        print(f"  > STATUS: Form for appt {aid} is NOT filled.")
        print(f"  > ACTION: Sending email to {email} asking to fill the form.")
        print(f"  > EMAIL BODY: 'Hi {name}, we see you haven't filled your intake form. Please do so.'")
    else:
        print(f"  > STATUS: Form for appt {aid} is ALREADY FILLED.")
        print(f"  > ACTION: Sending confirmation check to {email}.")
        print(f"  > EMAIL BODY: 'Hi {name}, your appt is tomorrow. Are you still confirmed? [Yes/No]'")

def simulate_3rd_reminder(aid, email, name):
    """(2-hours out) - Final check. If user cancelled, ask why."""
    
    # 1. Check if visit is confirmed (Simulated DB check)
    visit_status = check_visit_status(aid) # This is a simulated function
    
    if visit_status == "confirmed":
        print(f"  > STATUS: Visit for appt {aid} is CONFIRMED.")
        print(f"  > ACTION: Sending final reminder to {email}.")
        print(f"  > EMAIL BODY: 'Hi {name}, see you in 2 hours!'")
        
    elif visit_status == "cancelled":
        print(f"  > STATUS: Visit for appt {aid} was CANCELLED.")
        print(f"  > ACTION: Sending follow-up email to {email} to ask for reason.")
        print(f"  > EMAIL BODY: 'Hi {name}, we're sorry you cancelled. Could you tell us why? [Reason...]'")
        
    else: # "pending"
        print(f"  > STATUS: Visit for appt {aid} is still PENDING.")
        print(f"  > ACTION: Sending urgent final check to {email}.")
        print(f"  > EMAIL BODY: 'Hi {name}, your appt is in 2 hours. Please confirm or it may be cancelled.'")


# Simulated Database Helper Functions 
def check_if_form_is_filled(appointment_id):
    import random
    if random.choice([True, False]):
        return True # Simulate patient filled the form
    else:
        return False 

def check_visit_status(appointment_id):
    import random
    return random.choice(["confirmed", "cancelled", "pending"])