#  AI Patient Scheduling Assistant

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-HuggingFace-blue?style=for-the-badge&logo=huggingface)](https://huggingface.co/spaces/Sourav-003/ai-patient-scheduler)

A conversational **AI agent** designed to automate the **new and returning patient appointment scheduling** process.  
This project uses a **LangGraph-powered agent** to manage stateful conversations, look up patient history, check smart scheduling logic (30 vs. 60 min slots), and book appointments.

---

##  Repository Versions

- **Submission Version:** Simulates calendar operations by reading/writing to an Excel file (`doctor_schedule.xlsx`).
- **Upgraded Version:** Integrates directly with the **Google Calendar API** for real-time, per-doctor scheduling.

---

##  Key Features

- **Conversational UI:** A user-friendly Gradio chatbot interface.  
- **Patient Recognition:** Automatically identifies *new* vs. *returning* patients from a SQLite database to determine appointment length.  
- **Smart Scheduling:** Allocates **60-minute slots** for new patients and **30-minute slots** for returning patients.  
- **Real-time Calendar:**  
  - *Upgraded:* Integrates with Google Calendar API to check live availability per doctor.  
  - *Base:* Reads/writes to an Excel file (`doctor_schedule.xlsx`) to simulate scheduling.  
- **Automated Confirmations:** Sends a confirmation email (with attached intake form) upon successful booking.  
- **Simulated Reminder System:** Includes a 3-step reminder logic in `scheduler.py` to check for form completion and visit confirmation.  
- **Full Data Capture:** Stores patient details including contact info and insurance details (carrier, member ID, group #).  
- **Admin Dashboard:** Password-protected admin tab (`admin123`) to view all booked appointments.  
- **Data Export:** Generates an `admin_review.xlsx` file for new appointments.

---

##  Tech Stack

| Component | Technology |
|------------|-------------|
| **LLM** | Google Gemini 1.5 / 2.5 Flash |
| **Agent Framework** | LangGraph |
| **Core AI** | LangChain, LangChain Core |
| **UI** | Gradio |
| **Calendar** | Google Calendar API / Pandas |
| **Database** | SQLite |
| **Notifications** | `smtplib` (Email) |
| **Deployment** | Hugging Face Spaces |

---

##  Agent Architecture

The system revolves around a **stateful LangGraph agent**, guided by a structured system prompt.  
Here’s how it flows:

1. **User Input:** The user chats through the Gradio interface.  
2. **LangGraph Agent (`chat_node`):**  
   - Analyzes the conversation and decides the next step.  
   - May ask for missing info (e.g., “What is your name?”).  
3. **Tool Calls (`tool_node`):** Executes specific functions:  
   - `lookup_patient`: Queries `patients.db`.  
   - `list_available_slots`: Checks Google Calendar or Excel.  
   - `book_slot`: Books appointment, updates DB & Excel, sends confirmation email.  
4. **Loop:** Tool results are fed back to the agent.  
5. **Stop:** Conversation ends with “You’re booked!” message, awaiting new input.

---

##  Usage

1. **Open** the app in your browser.  
2. **Start** with: `"Hi"` or `"I need to book an appointment"`.  
3. **Follow the prompts** to provide:
   -  **Name**  
   -  **Date of Birth**  
   -  **Doctor Preference**
4. **View available slots** and confirm one.  
5. **Provide contact and insurance details** to finalize the booking.  
6. **Admin Access:**  
   - Log in using the password **`admin123`** to view all appointment data.

