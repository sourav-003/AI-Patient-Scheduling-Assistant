import pandas as pd
from datetime import datetime, timedelta

DOCTOR_SCHEDULE_FILE = "doctor_schedule.xlsx"

def generate_doctor_schedule():
    print("Checking for doctor schedule file...")
    try:
        pd.read_excel(DOCTOR_SCHEDULE_FILE)
        print("Schedule file already exists. Skipping generation.")
        return
    except FileNotFoundError:
        print("Schedule file not found. Generating new schedule...")

    doctors = ["Dr. Mehta", "Dr. A. Rao", "Dr. Fernandiz", "Dr. Chen"]
    
    # Start from today's date
    start_date = datetime.now().date()
    # Generate schedule for the next 14 days
    num_days = 14
    
    schedule_data = []
    
    # Create time slots from 9:00 to 17:00 in 30-min intervals
    times = pd.date_range("09:00", "17:00", freq="30min").time
    
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() >= 5:
            continue
            
        for doctor in doctors:
            for time in times:
                schedule_data.append({
                    "doctor": doctor,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "time": time.strftime("%H:%M"),
                    "status": "available"
                })

    df = pd.DataFrame(schedule_data)
    df.to_excel(DOCTOR_SCHEDULE_FILE, index=False)
    print(f"Generated new schedule with {len(df)} future slots.")

if __name__ == "__main__":
    generate_doctor_schedule()