import csv
import random
import string


def generate_random_email():
    name = ''.join(random.choices(string.ascii_lowercase, k=10))
    domain = ''.join(random.choices(string.ascii_lowercase, k=5))
    return f"{name}@{domain}.com"


def append_random_emails_to_csv(file_path, num_emails=10000):
    with open(file_path, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=';')
        for _ in range(num_emails):
            email = generate_random_email()
            deleted = 'true'
            status = 'okssss'
            csvwriter.writerow([email, deleted, status])


# Use the function to append 10,000 random emails to test.csv
append_random_emails_to_csv('test.csv')