import os
import gradio as gr
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
import pandas as pd
import json

from db import init_db, find_patient_by_name_dob, create_patient, create_appointment
from data_gen import generate_doctor_schedule
from email_utils import send_email_with_pdf
from scheduler import schedule_3_reminders

# Load environment variables from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
assert GOOGLE_API_KEY, "❌ Please set GOOGLE_API_KEY in your .env"

# 1. DEFINE LANGGRAPH STATE
class AgentState(TypedDict):
    """Represents the state of our graph."""
    messages: Annotated[list[BaseMessage], lambda x, y: x + y]

# 2. DEFINE TOOLS
class PatientLookupInput(BaseModel):
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    dob: str = Field(..., description="Patient's date of birth in YYYY-MM-DD format")

class ListSlotsInput(BaseModel):
    doctor: str = Field(..., description="Name of the doctor to check for available slots")
    duration_minutes: int = Field(..., description="The required appointment duration (either 30 or 60 minutes)")

### NEW REQUIREMENT: INSURANCE 
class BookSlotInput(BaseModel):
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    dob: str = Field(..., description="Patient's date of birth in YYYY-MM-DD format")
    phone: str = Field(..., description="Patient's phone number")
    email: str = Field(..., description="Patient's email address")
    doctor: str = Field(..., description="Name of the doctor")
    slot_date: str = Field(..., description="The date of the appointment in YYYY-MM-DD format")
    slot_time: str = Field(..., description="The time of the appointment in HH:MM format")
    duration_minutes: int = Field(..., description="The appointment duration (either 30 or 60 minutes)")
    insurance_carrier: str = Field(..., description="Patient's insurance carrier name")
    member_id: str = Field(..., description="Patient's insurance member ID")
    group_number: str = Field(..., description="Patient's insurance group number")

@tool("lookup_patient", args_schema=PatientLookupInput)
def lookup_patient_tool(first_name: str, last_name: str, dob: str) -> dict:
    """
    Find a patient record by first name, last name and date of birth.
    This is the *first step* to determine if they are a new (60 min) or returning (30 min) patient.
    """
    patient = find_patient_by_name_dob(last_name, dob)
    is_new = not bool(patient)
    duration = 60 if is_new else 30
    return {
        "found": bool(patient),
        "patient_details": patient,
        "is_new_patient": is_new,
        "required_duration": duration
    }

@tool("list_available_slots", args_schema=ListSlotsInput)
def list_available_slots_tool(doctor: str, duration_minutes: int) -> list:
    """
    List available appointment slots for a specified doctor and duration.
    Assumes schedule has 30-minute blocks. For 60-min slots, it finds two consecutive 30-min blocks.
    """
    DOCTOR_SCHEDULE_FILE = "doctor_schedule.xlsx"
    try:
        df = pd.read_excel(DOCTOR_SCHEDULE_FILE)
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
        df = df.sort_values(by=['doctor', 'datetime'])
        
        available = df[(df['doctor'].str.lower() == doctor.lower()) & (df['status'] == "available")]
        
        if duration_minutes == 30:
            return available[['date', 'time']].head(5).to_dict('records')
        
        elif duration_minutes == 60:
            slots_60min = []
            available_indices = available.index.tolist()
            for i in range(len(available_indices) - 1):
                idx1 = available_indices[i]
                idx2 = available_indices[i+1]
                
                row1 = available.loc[idx1]
                row2 = available.loc[idx2]
                
                if (row2['datetime'] - row1['datetime'] == pd.Timedelta(minutes=30)):
                    slots_60min.append(row1)

            if not slots_60min:
                return []
            
            return [{'date': s['date'], 'time': s['time']} for s in slots_60min][:5]
        
        else:
            return [] 
            
    except Exception as e:
        print(f"Error in list_available_slots: {e}")
        return []

# We update the function definition to accept the new insurance fields
@tool("book_slot", args_schema=BookSlotInput)
def book_slot_tool(first_name, last_name, dob, phone, email, doctor, slot_date, slot_time, duration_minutes, insurance_carrier, member_id, group_number) -> dict:
    """Book a specific appointment slot for a patient, handling 30 or 60 minute durations."""
    
    insurance_data = {
        "carrier": insurance_carrier,
        "member_id": member_id,
        "group_number": group_number
    }

    patient = find_patient_by_name_dob(last_name, dob)
    if patient:
        pid = patient[0] 
    else:
        pid = create_patient(first_name, last_name, dob, phone, email, insurance_data)
    
    DOCTOR_SCHEDULE_FILE = "doctor_schedule.xlsx"
    try:
        df = pd.read_excel(DOCTOR_SCHEDULE_FILE)
        df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
        
        slot_datetime = pd.to_datetime(f"{slot_date} {slot_time}")
        
        mask1 = (df['doctor'].str.lower() == doctor.lower()) & (df['datetime'] == slot_datetime) & (df['status'] == "available")

        if duration_minutes == 30:
            if mask1.any():
                idx1 = df[mask1].index[0]
                df.at[idx1, 'status'] = "booked"
                df.drop(columns=['datetime']).to_excel(DOCTOR_SCHEDULE_FILE, index=False)
            else:
                return {"status": "error", "message": "The selected 30-minute slot is no longer available."}
        
        elif duration_minutes == 60:
            slot_datetime_plus_30 = slot_datetime + pd.Timedelta(minutes=30)
            mask2 = (df['doctor'].str.lower() == doctor.lower()) & (df['datetime'] == slot_datetime_plus_30) & (df['status'] == "available")
            
            if mask1.any() and mask2.any():
                idx1 = df[mask1].index[0]
                idx2 = df[mask2].index[0]
                df.at[idx1, 'status'] = "booked"
                df.at[idx2, 'status'] = "booked (part 2)"
                df.drop(columns=['datetime']).to_excel(DOCTOR_SCHEDULE_FILE, index=False)
            else:
                return {"status": "error", "message": "The full 60-minute slot is not available."}
        
        else:
            return {"status": "error", "message": "Invalid duration."}

        # If booking was successful, continue 
        scheduled_iso = f"{slot_date} {slot_time}"
        aid = create_appointment(pid, doctor, scheduled_iso, duration_minutes)
        
        send_email_with_pdf(
            email,
            "Appointment Confirmation",
            f"Hello {first_name}, your {duration_minutes}-minute appointment with {doctor} is confirmed for {scheduled_iso}. An intake form is attached.",
            attach_form=True
        )
        schedule_3_reminders(aid, scheduled_iso, email, f"{first_name} {last_name}")
        
        # ADMIN EXPORT LOGIC 
        try:
            ADMIN_REPORT_FILE = "admin_review.xlsx"
            new_appointment_data = {
                'patient_name': f"{first_name} {last_name}",
                'patient_email': email,
                'patient_phone': phone,
                'doctor': doctor,
                'appointment_date': slot_date,
                'appointment_time': slot_time,
                'duration': duration_minutes,
                'insurance_carrier': insurance_carrier,
                'member_id': member_id,
                'group_number': group_number
            }
            
            # Try to read the existing file, or create a new dataframe
            try:
                admin_df = pd.read_excel(ADMIN_REPORT_FILE)
            except FileNotFoundError:
                admin_df = pd.DataFrame()
                
            # Append the new appointment and save
            admin_df = pd.concat([admin_df, pd.DataFrame([new_appointment_data])], ignore_index=True)
            admin_df.to_excel(ADMIN_REPORT_FILE, index=False)
            
        except Exception as e:
            print(f"Error in admin export: {e}") # Don't crash the whole booking if this fails
        
        # END ADMIN EXPORT LOGIC 
        return {"status": "success", "message": f"Appointment ({duration_minutes} min) booked successfully", "appointment_id": aid}
        
    except Exception as e:
        print(f"Error in book_slot_tool: {e}")
        return {"status": "error", "message": str(e)}

tools = [lookup_patient_tool, list_available_slots_tool, book_slot_tool]

# 3. DEFINE LANGGRAPH NODES
base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # Your working model
    temperature=0.5
)

model = base_llm.bind_tools(tools)


def chat_node(state: AgentState):
    messages = state['messages']
    
    ### NEW REQUIREMENT: INSURANCE PROMPT 
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a friendly and precise patient scheduling assistant. Your goal is to book an appointment. You MUST follow these steps in order:

        1.  **Greet** the user.
        2.  **Lookup Patient:** Ask for their **first name**, **last name**, and **date of birth** (YYYY-MM-DD). Then, *immediately* use the `lookup_patient` tool.
        3.  **Find Slots:** The `lookup_patient` tool will return `is_new_patient` (true/false) and `required_duration` (30 or 60).
            -   Inform the user: "Since you are a [new/returning] patient, your appointment will be [60/30] minutes."
            -   Then, ask for their desired **doctor**.
            -   Once you have the doctor, *immediately* use the `list_available_slots` tool with the `doctor` and `duration_minutes` (30 or 60).
        4.  **Present Slots:** Show the user the available slots.
        5.  **Gather Final Details:** Once they pick a slot (e.g., "2025-10-20 at 10:30"), you MUST ask for their **phone number** and **email address**.
        6.  **Gather Insurance:** After getting the phone and email, you MUST ask for their **insurance carrier**, **member ID**, and **group number**.
        7.  **Book:** Once you have ALL information (first_name, last_name, dob, doctor, slot_date, slot_time, phone, email, duration, AND all three insurance details), you MUST call the `book_slot` tool.
        8.  **Confirm:** Tell the user the booking is complete and say goodbye.
        
        IMPORTANT: Do not ask for insurance until *after* phone/email. Do not call `book_slot` until you have *all* pieces of information.
        """),
        ("placeholder", "{messages}")
    ])
    
    chain = prompt | model
    response = chain.invoke({"messages": messages})
    
    return {"messages": [response]}

def tool_node(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    tool_outputs = []
    
    for tool_call in getattr(last_message, "tool_calls", []):
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        
        tool_dispatcher = {
            "lookup_patient": lookup_patient_tool,
            "list_available_slots": list_available_slots_tool,
            "book_slot": book_slot_tool
        }
        
        if tool_name in tool_dispatcher:
            tool_output = tool_dispatcher[tool_name].invoke(tool_args)
            tool_outputs.append(ToolMessage(tool_call_id=tool_call['id'], content=str(tool_output)))
        else:
            tool_outputs.append(ToolMessage(tool_call_id=tool_call['id'], content=f"Tool '{tool_name}' not found."))
    
    return {"messages": tool_outputs}

# 4. DEFINE LANGGRAPH EDGES
def should_continue(state: AgentState):
    last_message = state['messages'][-1]
    if getattr(last_message, "tool_calls", None):
        return "tool_call"
    return "continue"

graph_builder = StateGraph(AgentState)
graph_builder.add_node("chat_node", chat_node)
graph_builder.add_node("tool_node", tool_node)

graph_builder.set_entry_point("chat_node")
graph_builder.add_conditional_edges(
    "chat_node",
    should_continue,
    {"tool_call": "tool_node", "continue": END} # This stops the infinite loop
)
graph_builder.add_edge("tool_node", "chat_node")

# Compile the graph
graph = graph_builder.compile()

# 5. GRADIO INTERFACE
def process_message(user_message, history):
    chat_history = []
    for msg in history:
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history.append(AIMessage(content=msg["content"]))
    
    input_messages = chat_history + [HumanMessage(content=user_message)]
    
    try:
        response = graph.invoke({"messages": input_messages})
        
        last_message = response['messages'][-1]
        
        if isinstance(last_message.content, list):
            assistant_text = last_message.content[0]['text']
        else:
            assistant_text = last_message.content # Failsafe for simple strings

    except Exception as e:
        print(f"An error occurred in the agent: {e}")
        assistant_text = "I'm sorry, an error occurred while processing your request. Please try again or rephrase."

    # Append the new user message and the *clean* AI response to Gradio's history
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_text})
    
    # Return the updated history for the chatbot and an empty string for the textbox
    return history, ""

### NEW ADMIN FUNCTION 
def load_admin_data():
    """
    Reads the admin_review.xlsx file and returns it as a DataFrame.
    """
    ADMIN_REPORT_FILE = "admin_review.xlsx"
    try:
        df = pd.read_excel(ADMIN_REPORT_FILE)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            'patient_name', 'patient_email', 'patient_phone', 'doctor', 
            'appointment_date', 'appointment_time', 'duration', 
            'insurance_carrier', 'member_id', 'group_number'
        ])
    except Exception as e:
        print(f"Error loading admin data: {e}")
        return pd.DataFrame({"Error": [str(e)]})

###  NEW ADMIN LOGIN FUNCTION 
def admin_login(password):
    """
    Checks the admin password and updates tab visibility.
    """
    ADMIN_PASSWORD = "admin123" 
    
    if password == ADMIN_PASSWORD:
        return {
            admin_tab: gr.Tab(visible=True),
            login_tab: gr.Tab(visible=False)
        }
    else:
        return {
            admin_tab: gr.Tab(visible=False),
            login_tab: gr.Tab(visible=True)
        }

# 6. APP STARTUP
if __name__ == "__main__":
    init_db()
    generate_doctor_schedule()

    with gr.Blocks() as demo:
        gr.Markdown("# AI Patient Scheduling Assistant")
        
        with gr.Tabs():
            with gr.Tab("Chatbot") as chatbot_tab:
                chatbot = gr.Chatbot(type="messages", height=600)
                txt = gr.Textbox(placeholder="Hi, I need to book an appointment.")
                
                txt.submit(
                    fn=process_message,
                    inputs=[txt, chatbot],
                    outputs=[chatbot, txt]
                )
            
            with gr.Tab("Admin Dashboard", visible=False) as admin_tab:
                gr.Markdown("## Booked Appointments (Admin View)")
                gr.Markdown("Click 'Refresh Data' to see the latest bookings from `admin_review.xlsx`.")
                
                admin_dataframe = gr.DataFrame(headers=[
                    'patient_name', 'doctor', 'appointment_date', 'appointment_time', 
                    'duration', 'patient_email', 'patient_phone', 
                    'insurance_carrier', 'member_id', 'group_number'
                ])
                
                refresh_button = gr.Button("Refresh Data")

                refresh_button.click(
                    fn=load_admin_data,
                    inputs=None,
                    outputs=[admin_dataframe]
                )
            
            with gr.Tab("Admin Login") as login_tab:
                gr.Markdown("## Admin Access")
                gr.Markdown("Please enter the admin password to view the dashboard.")
                
                password_box = gr.Textbox(label="Password", type="password")
                login_button = gr.Button("Login")

        login_button.click(
            fn=admin_login,
            inputs=[password_box],
            # This updates the visibility of the two tabs
            outputs=[admin_tab, login_tab] 
        )
        
    demo.launch()