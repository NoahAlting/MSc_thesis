import smtplib
from email.message import EmailMessage
import inspect
import os

def send_email_notification():
    script_path = inspect.stack()[1].filename
    script_name = os.path.basename(script_path)

    msg = EmailMessage()
    msg.set_content(f"""
                    Hi Noah!
                    Your python script {script_name} has finished.
                    
                    Love,
                    Luna
                    """)
    
    msg["Subject"] = "Your code has finished!"
    msg["From"] = "assistingluna@gmail.com"
    msg["To"] = "noahalting@gmail.com"

    # Login with app password
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("assistingluna@gmail.com", "iqxkwlkazejuagkf")
        smtp.send_message(msg)


if __name__ == "__main__":
    send_email_notification()
