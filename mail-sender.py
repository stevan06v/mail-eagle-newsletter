import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl

sender_email = "test@webhoch.com"
password = "y4E4-11@m#1"
smtp_server = "gnldm1070.siteground.biz"
smtp_port = 465

# Load email list from file
with open('emaillist.txt', 'r') as file:
    email_list = [line.strip() for line in file if line.strip()]

# Read email message from file
with open('msg.txt', 'r', encoding='utf-8') as file:
    html_message = file.read()

context = ssl.create_default_context()

def send_html_email(recipient_email, subject, html_content):
    try:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        # Establish SMTP connection
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")

for recipient_email in email_list:
    send_html_email(recipient_email, "Your Email Subject Here", html_message)

print("All HTML emails sent successfully.")
