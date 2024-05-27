import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import concurrent.futures
import time

context = ssl.create_default_context()

def send_html_email(smtp_server, smtp_port, sender_email, sender_password, recipient_email, subject, content, job_id, email_id):
    try:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        # Append the unsubscribe link to the content
        unsubscribe_link = f"<p>Drücke <a href=\"http://130.61.138.88/abbestellen/{job_id}/{email_id}\" style=\"color: red; text-decoration: none;\">hier</a> um den Newsletter abzubestellen.</p></center>"
        with open(content, 'r', encoding='utf-8') as file:
            html_content = file.read()
        html_content += unsubscribe_link

        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        # Establish SMTP connection
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(f"Email sent to {recipient_email}")
            return True  # Success
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False  # Failure

def send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, content, job_id, batch_size=400, wait_time=3600):
    total_emails = len(email_list)
    batches = [email_list[i:i + batch_size] for i in range(0, total_emails, batch_size)]
    failed_emails = []

    for batch_number, batch in enumerate(batches):
        print(f"Sending batch {batch_number + 1}/{len(batches)} with {len(batch)} emails.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(send_html_email, smtp_server, smtp_port, sender_email, sender_password, email, subject, content, job_id, email_id): email
                for email_id, email in enumerate(batch)
            }

            for future in concurrent.futures.as_completed(futures):
                email = futures[future]
                if not future.result():
                    failed_emails.append(email)

        if batch_number < len(batches) - 1:
            print(f"Waiting for {wait_time / 3600} hour(s) before sending the next batch.")
            time.sleep(wait_time)

    retry_failed_emails(smtp_server, smtp_port, sender_email, sender_password, failed_emails, subject, content, job_id, wait_time)

def retry_failed_emails(smtp_server, smtp_port, sender_email, sender_password, failed_emails, subject, content, job_id, wait_time):
    retry_attempts = 0
    while failed_emails:
        retry_attempts += 1
        print(f"Retrying failed emails, attempt {retry_attempts}.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(send_html_email, smtp_server, smtp_port, sender_email, sender_password, email, subject, content, job_id, email_id): email
                for email_id, email in enumerate(failed_emails)
            }

            failed_emails = [futures[future] for future in concurrent.futures.as_completed(futures) if not future.result()]

        if failed_emails:
            print(f"Failed to send {len(failed_emails)} emails. Retrying after {wait_time / 3600} hour(s).")
            time.sleep(wait_time)
        else:
            print("All emails sent successfully after retry.")

# Example usage:
if __name__ == "__main__":
    sender_email = "test@webhoch.com"
    sender_password = "PE+ec5er:2^@1%"
    smtp_server = "gnldm1070.siteground.biz"
    smtp_port = 465

    email_list = [
        "michael.ruep@gmail.com",
        "stevanvlajic5@gmail.com"
    ]

    subject = "Your Email Subject Here 2"

    send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, 'msg.txt', 1)
    print("All HTML emails sent successfully.")
