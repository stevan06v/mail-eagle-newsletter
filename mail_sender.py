import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import concurrent.futures

context = ssl.create_default_context()

def send_html_email(smtp_server, smtp_port, sender_email, sender_password, recipient_email, subject, html_content, job_id, email_id):
    try:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        # Append the unsubscribe link to the content
        unsubscribe_link = f"<center><p>Diese E-Mail würde gesendet an {recipient_email}.</p></center><br><center><p>Drücke <a href=\"https://sanabau.com/abbestellen/{job_id}/{email_id}\" style=\"color: red; text-decoration: none;\">hier</a> um den Newsletter abzubestellen.</p></center>"
        html_content += unsubscribe_link

        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        # Establish SMTP connection
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")


def send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, content, job_id):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit each email for sending concurrently
        futures = [
            executor.submit(send_html_email, smtp_server, smtp_port, sender_email, sender_password, email, subject, content, job_id, email_id)
            for email_id, email in email_list.items()
        ]
        
        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # Ensure we check for any exceptions
            except Exception as e:
                print(f"An error occurred: {e}")


# Example usage:
if __name__ == "__main__":
    sender_email = "test@webhoch.com"
    sender_password = "PE+ec5er:2^@1%"
    smtp_server = "gnldm1070.siteground.biz"
    smtp_port = 465

    email_list = {
        1: "michael.ruep@gmail.com",
        2: "regeyam414@javnoi.com"
    }

    subject = "Your Email Subject Here 2"

    with open('msg.txt', 'r', encoding='utf-8') as file:
        content = file.read()

    send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, content, 1)
    print("All HTML emails sent successfully.")
