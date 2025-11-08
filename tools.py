import pandas as pd
from db import find_patient_by_name_dob, create_patient, create_appointment
from email_utils import send_email_with_pdf
from scheduler import schedule_3_reminders

DOCTOR_SCHEDULE_FILE = "doctor_schedule.xlsx"

def lookup_patient_tool(first_name, last_name, dob):
    """Find a patient record by last name and date of birth."""
    p = find_patient_by_name_dob(last_name, dob)
    return {"found": bool(p), "patient": p}

def list_available_slots(doctor):
    df = pd.read_excel(DOCTOR_SCHEDULE_FILE)
    free = df[(df['doctor']==doctor) & (df['status']=="available")]
    return free[['date','time']].head(5).to_dict('records')

def book_slot_tool(first_name,last_name,dob,phone,email,doctor,slot_date,slot_time,is_new_patient=True,insurance=None):
    p = find_patient_by_name_dob(last_name, dob)
    if not p:
        pid = create_patient(first_name,last_name,dob,phone,email, insurance or {})
    else:
        pid = p[0] 
    df = pd.read_excel(DOCTOR_SCHEDULE_FILE)
    mask = (df['doctor']==doctor) & (df['date']==slot_date) & (df['time']==slot_time) & (df['status']=="available")
    if mask.any():
        idx = df[mask].index[0]
        df.at[idx,'status']="booked"
        df.to_excel(DOCTOR_SCHEDULE_FILE,index=False)
        scheduled_iso = f"{slot_date} {slot_time}"
        duration = 60 if is_new_patient else 30
        aid = create_appointment(pid, doctor, scheduled_iso, duration)
        
        # Trigger email and reminders
        send_email_with_pdf(email, "Appointment Confirmation", f"Hello {first_name}, your appointment with {doctor} is confirmed for {scheduled_iso}. An intake form is attached.", attach_form=True)
        schedule_3_reminders(aid, scheduled_iso, email, f"{first_name} {last_name}")
        
        return {"status": "success", "message": "Appointment booked successfully", "appointment_id": aid}
    else:
        return {"status": "error", "message": "The selected slot is no longer available."}