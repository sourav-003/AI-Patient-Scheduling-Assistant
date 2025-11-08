import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
INTAKE_FORM = "New Patient Intake Form.pdf"

def send_email_with_pdf(to_email, subject, body, attach_form=True):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, "plain"))
    if attach_form and os.path.exists(INTAKE_FORM):
        with open(INTAKE_FORM, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(INTAKE_FORM))
            msg.attach(part)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "sent"
    except Exception as e:
        return False, str(e)
