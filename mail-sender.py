import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import concurrent.futures  # Import ThreadPoolExecutor for multithreading

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

def send_emails(email_list):
    subject = "Your Email Subject Here"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit each email for sending concurrently
        futures = [executor.submit(send_html_email, email, subject, html_message) for email in email_list]
        
        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Ensure we check for any exceptions
            except Exception as e:
                print(f"An error occurred: {e}")

# Call the function to send emails using ThreadPoolExecutor
send_emails(email_list)

print("All HTML emails sent successfully.")
