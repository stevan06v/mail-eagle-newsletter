import json
from mail_sender import send_emails

with open('failed_emails.json', 'r') as file:
    data = json.load(file)

# Extract the emails
email_list = [job['email'] for job in data['jobs']]

# Configuration
sender_email = "noreply@newsletter-sana-bau.com"
sender_password = "1}25))5Pg{2b"
smtp_server = "gfram1028.siteground.biz"
smtp_port = 465

subject = "Herzliche Einladung!"

send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, 'failed.html', -404)