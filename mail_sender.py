from urllib.parse import quote
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import json
import time
import logging


context = ssl.create_default_context()


logger = logging.getLogger(__name__)
logging.basicConfig(filename='mail-eagle.log', encoding='utf-8', level=logging.DEBUG)


def get_job_by_id(job_id):
    with open('config.json', 'r') as file:
        config = json.load(file)
    for job in config['jobs']:
        if job['id'] == job_id:
            return job
    return None


def update_config(job_id, successful_emails, failed_emails):
    with open('config.json', 'r') as file:
        config = json.load(file)

    for job in config['jobs']:
        if job['id'] == job_id:
            job['successful_emails'] = list(set(job.get('successful_emails', []) + successful_emails))
            job['failed_emails'] = list(set(failed_emails))
            break

    with open('config.json', 'w') as file:
        json.dump(config, file, indent=4)


def send_html_email(smtp_server, smtp_port, sender_email, sender_password, recipient_email, subject, content, delay):
    try:
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        encoded_email = quote(recipient_email)

        # Append the unsubscribe link to the content
        unsubscribe_link = f"<center><p>Drücke <a href=\"https://eu-submit.jotform.com/252227521165350\" style=\"color: red; text-decoration: none;\">hier</a> um den Newsletter abzubestellen.</p></center>"
        with open(content, 'r', encoding='utf-8') as file:
            html_content = file.read()
        html_content += unsubscribe_link

        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)

        # Establish SMTP connection
        with smtplib.SMTP(smtp_server, smtp_port) as server: #, context=context
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
            print(f"Email sent to {recipient_email}")
            logger.info(f"Email sent to {recipient_email}")
            return True  # Success
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        return False
    finally:
        time.sleep(delay)


def send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, content, job_id, batch_size=400, wait_time=3600, delay=0.125):
    total_emails = len(email_list)
    batches = [email_list[i:i + batch_size] for i in range(0, total_emails, batch_size)]
    all_successful_emails = []
    all_failed_emails = []

    for batch_number, batch in enumerate(batches):
        print(f"Sending batch {batch_number + 1}/{len(batches)} with {len(batch)} emails.")
        logger.info(f"Sending batch {batch_number + 1}/{len(batches)} with {len(batch)} emails.")

        successful_emails = []
        failed_emails = []

        for email_id, email in enumerate(batch):
            success = send_html_email(smtp_server, smtp_port, sender_email, sender_password, email, subject, content, delay)
            if success:
                successful_emails.append(email)
            else:
                failed_emails.append(email)

            # Update config after each email
            update_config(job_id, successful_emails, failed_emails)
            successful_emails.clear()
            failed_emails.clear()

        all_successful_emails.extend(successful_emails)
        all_failed_emails.extend(failed_emails)

        if batch_number < len(batches) - 1:
            print(f"Waiting for {wait_time / 3600} hour(s) before sending the next batch.")
            logger.info(f"Waiting for {wait_time / 3600} hour(s) before sending the next batch.")

            time.sleep(wait_time)

    retry_failed_emails(smtp_server, smtp_port, sender_email, sender_password, all_failed_emails, subject, content, job_id, wait_time, delay)


def retry_failed_emails(smtp_server, smtp_port, sender_email, sender_password, failed_emails, subject, content, job_id, wait_time, delay):
    retry_attempts = 0
    all_successful_emails = []

    while failed_emails:
        retry_attempts += 1
        print(f"Retrying failed emails, attempt {retry_attempts}.")
        logger.info(f"Retrying failed emails, attempt[{job_id}] {retry_attempts}.")

        successful_emails = []
        new_failed_emails = []

        for email_id, email in enumerate(failed_emails):
            success = send_html_email(smtp_server, smtp_port, sender_email, sender_password, email, subject, content, delay)
            if success:
                successful_emails.append(email)
            else:
                new_failed_emails.append(email)

        all_successful_emails.extend(successful_emails)
        failed_emails = new_failed_emails
        update_config(job_id, successful_emails, new_failed_emails)

        if failed_emails:
            print(f"Failed to send {len(failed_emails)} emails. Retrying after {wait_time / 3600} hour(s).")
            logger.error(f"[{job_id}]: Failed to send {len(failed_emails)} emails. Retrying after {wait_time / 3600} hour(s).")
            time.sleep(wait_time)
        else:
            print("All emails sent successfully after retry.")
            logger.info(f"[{job_id}]: All emails sent successfully after retry.")

if __name__ == "__main__":
    sender_email = "info@homa-bau.com"
    sender_password = f"8@B%eD>AGtd8LM:" #"QF5hPY$25Ly4W!!uUz^S6csu8s%EgAkz^#012d*tM%7c#1&^j#G*1#pcW&W!Cmxa"
    smtp_server = "78.46.226.32"
    smtp_port = 55587

    email_list = [
        "stevan0901@protonmail.com",
    ]

    subject = "Hallo Joni :)"

    send_emails(smtp_server, smtp_port, sender_email, sender_password, email_list, subject, 'msg.txt', 1)