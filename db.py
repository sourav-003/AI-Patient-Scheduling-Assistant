import sqlite3
import json 

DB_FILE = "patients.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT, last_name TEXT,
        dob TEXT, phone TEXT, email TEXT,
        insurance_company TEXT, member_id TEXT, group_number TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor TEXT,
        scheduled_time TEXT,
        duration INTEGER,
        status TEXT,
        reminders_sent INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit(); conn.close()

def find_patient_by_name_dob(last_name, dob):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("SELECT * FROM patients WHERE last_name=? AND dob=? LIMIT 1",(last_name,dob))
    row = c.fetchone(); conn.close()
    return row

def create_patient(first_name,last_name,dob,phone,email,insurance):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    
    c.execute("""INSERT INTO patients (first_name,last_name,dob,phone,email,
                 insurance_company,member_id,group_number) VALUES (?,?,?,?,?,?,?,?)""",
              (first_name,last_name,dob,phone,email,
               insurance.get("carrier"), # <-- Was "company"
               insurance.get("member_id"),
               insurance.get("group_number")))
    
    pid = c.lastrowid
    conn.commit(); conn.close()
    return pid

def create_appointment(patient_id, doctor, scheduled_time, duration):
    conn = sqlite3.connect(DB_FILE); c = conn.cursor()
    c.execute("""INSERT INTO appointments (patient_id,doctor,scheduled_time,duration,status)
                 VALUES (?,?,?,?,?)""", (patient_id,doctor,scheduled_time,duration,"confirmed"))
    aid = c.lastrowid; conn.commit(); conn.close()
    return aid