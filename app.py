import csv
import os
from flask_bootstrap import Bootstrap5
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileAllowed, FileRequired
from jsonstore import JsonStore
import time
from wtforms.fields import *
from dotenv import load_dotenv
import threading
from datetime import datetime
import uuid
from wtforms.validators import DataRequired, Length, Regexp
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from secrets import compare_digest

from mail_sender import send_emails

load_dotenv()

store = JsonStore('config.json')

app = Flask(__name__)

app.secret_key = 'dev'

login_manager = LoginManager(app)

bootstrap = Bootstrap5(app)

csrf = CSRFProtect(app)

# Define a User model
class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_id(self):
        return self.username


@login_manager.user_loader
def load_user(user_id):
    return user if user.get_id() == user_id else None


user = User(os.getenv('LOGIN'), os.getenv('PASSWORD'))

# Register the user with Flask-Login
login_manager.user_loader(load_user)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 150)])
    submit = SubmitField()


class SenderEmailCredentials(FlaskForm):
    smtp_server = StringField('SMTP-Server', validators=[DataRequired()])
    smtp_port = IntegerField('SMTP-Port', validators=[DataRequired()])
    sender_email = EmailField('Sender-Email', validators=[DataRequired()])
    sender_password = PasswordField('Sender-Password', validators=[DataRequired()])

    submit = SubmitField()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    login_form = LoginForm()

    if login_form.validate_on_submit():
        if user.username == login_form.username.data and compare_digest(user.password, login_form.password.data):
            # Login the user
            login_user(user)

            flash('Successfully logged in!')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', form=login_form, error='Invalid username or password')

    return render_template('login.html', form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        return render_template('index.html')


@app.route('/configure', methods=['GET', 'POST'])
@login_required
def configure():
    form = SenderEmailCredentials()
    if request.method == 'POST' and form.validate_on_submit():
        # Process form data
        smtp_server = form.smtp_server.data
        smtp_port = form.smtp_port.data
        sender_email = form.sender_email.data
        sender_password = form.sender_password.data

        store['email_sender.smtp_server'] = smtp_server
        store['email_sender.smtp_port'] = smtp_port
        store['email_sender.sender_email'] = sender_email
        store['email_sender.sender_password'] = sender_password

        flash('Email sender configuration saved successfully!', 'success')

        return redirect(url_for('configure'))

    # Load existing data if available
    form.smtp_server.data = store['email_sender.smtp_server']
    form.smtp_port.data = store['email_sender.smtp_port']
    form.sender_email.data = store['email_sender.sender_email']
    form.sender_password.data = store['email_sender.sender_password']

    return render_template('configure.html', form=form, email_sender=store['email_sender'])


class JobForm(FlaskForm):
    name = StringField('Job Name', description="Define a name to identify the job later on.",
                       validators=[DataRequired()])
    csv = FileField(label="Email List as CSV", description="Input the HTML Newsletter Content File.",
                    validators=[FileAllowed(['csv']), FileRequired()])
    column = StringField('Email Column Name', description="Use the exact name of your CSV Email Column.",
                         validators=[DataRequired()])
    subject = StringField(description="Set a subject for the email.",
                          validators=[DataRequired()])
    content = FileField(description="Input the HTML Newsletter Content File.",
                        validators=[FileAllowed(['html'], FileRequired())])
    date = DateTimeLocalField(description="This field indicates the date when the newsletter should be sent.",
                              validators=[DataRequired()])
    submit = SubmitField('Add')


def parse_csv_column(csv_file_path, column_name):
    try:
        column_data = []
        with open(csv_file_path, 'r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')  # Specify the delimiter
            header = next(csv_reader)  # Get the header row
            if column_name in header:
                column_index = header.index(column_name)
                for row in csv_reader:
                    if 0 <= column_index < len(row):
                        column_data.append(row[column_index])
                    else:
                        raise IndexError(f"Column index {column_index} out of range.")
            else:
                raise ValueError(f"Column '{column_name}' not found in CSV file header.")

        return column_data
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


class TableData:
    def __init__(self, data, titles):
        self.data = data
        self.titles = titles

    def __iter__(self):
        for item in self.data:
            yield item


@app.route('/jobs', methods=['GET', 'POST'])
@login_required
def jobs():
    form = JobForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            csv_file = form.csv.data
            content_file = form.content.data

            csv_filename = str(uuid.uuid4()) + '.csv'
            content_filename = str(uuid.uuid4()) + '.html'

            uploads_folder = os.path.join(app.root_path, 'uploads')
            csv_file_path = os.path.join(uploads_folder, csv_filename)
            content_file_path = os.path.join(uploads_folder, content_filename)

            # Save files
            if csv_file:
                csv_file.save(csv_file_path)
            if content_file:
                content_file.save(content_file_path)

            job = {
                "id": len(store['jobs']) + 1,
                "name": form.name.data,
                "subject": form.subject.data,
                "is_scheduled": False,
                "is_finished": False,
                "csv_path": csv_file_path,
                "schedule_date": form.date.data.strftime('%m/%d/%Y %H:%M:%S'),
                "content_file_path": content_file_path,
                "list": parse_csv_column(csv_file_path, form.column.data)
            }

            store['jobs'] += [job]

            print(store['jobs'])

            flash("Successfully created job!", 'success')
            return redirect(url_for('jobs'))
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')

    jobs_data = [
        {
            'id': job['id'],
            'name': job['name'],
            'subject': job['subject'],
            'schedule_date': job['schedule_date'],
            'is_scheduled': job['is_scheduled'],
            'is_finished': job['is_finished']
        }
        for job in store['jobs']
    ]

    titles = [
        ('id', 'ID'),
        ('name', 'Name'),
        ('subject', 'Subject'),
        ('schedule_date', 'Schedule Date'),
        ('is_scheduled', 'Is Scheduled'),
        ('is_finished', 'Is Finished'),
    ]

    table_data = TableData(jobs_data, titles)

    return render_template('jobs.html', form=form, table_data=table_data)


def send_delayed_mails(delay, job):
    print(f"Starting job[{job['name']}] with delay: {delay}s")
    time.sleep(delay)

    send_emails(
                smtp_server=store['email_sender.smtp_server'],
                smtp_port=store['email_sender.smtp_port'],
                sender_email=store['email_sender.sender_email'],
                sender_password=store['email_sender.sender_password'],
                email_list=job['list'],
                subject=job['subject'],
                content=job['content_file_path'],
                job_id=job['id']
    )

    # Update job status
    job['is_finished'] = True
    job['is_scheduled'] = False

    # Update the job in the list
    jobs = store.jobs
    for i, existing_job in enumerate(jobs):
        if existing_job['id'] == job['id']:
            jobs[i] = job
            break

    store.jobs = jobs


class MailJob(threading.Thread):
    def __init__(self, job, *args, **kwargs):
        super(MailJob, self).__init__(*args, **kwargs)
        self._stop = threading.Event()
        self.job = job

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while True:
            if self.stopped():
                return
            print("Hello, world!")
            time.sleep(1)


class MailsJobScheduler:
    def __init__(self):
        self.mail_jobs = []

    def schedule_job(self, job):
        now = datetime.now()
        schedule_date = datetime.strptime(job["schedule_date"], "%m/%d/%Y %H:%M:%S")
        delay = (schedule_date - now).total_seconds()

        if delay < 0:
            raise AttributeError('The target datetime is below the start time!')

        job_thread = threading.Thread(target=send_delayed_mails, args=(delay, job), daemon=True)
        job_thread.start()

        mail_job = MailJob(job)

        self.mail_jobs.append(mail_job)

    def stop_job_thread(self, job_id):
        for iterator in self.mail_jobs:
            if iterator.job["id"] == job_id:
                self.mail_jobs = [mj for mj in self.mail_jobs if mj.job["id"] != job_id]
                iterator.stop()
                return True
        return False


mails_job_scheduler = MailsJobScheduler()


def unsubscribe_email(email_dict, email_id):
    if email_id in email_dict:
        del email_dict[email_id]
    else:
        print(f"Email ID {email_id} not found.")


@app.route('/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    # wipe junk leftover files
    for job in store['jobs']:
        if job['id'] == job_id:
            os.remove(job['csv_path'])
            os.remove(job['content_file_path'])
            break

    store['jobs'] = [job for job in store['jobs'] if job['id'] != job_id]
    mails_job_scheduler.stop_job_thread(job_id)

    flash(f"Job[{job_id}] successfully deleted!", 'success')
    return redirect(url_for('jobs'))


@app.route('/schedule/<int:job_id>', methods=['GET'])
@login_required
def schedule_job(job_id):
    jobs_temp = store['jobs']
    for job in jobs_temp:
        if job['id'] == job_id:
            if job['is_scheduled']:
                flash(f"Job[{job_id}] is already scheduled!", 'warning')
            else:
                try:
                    # schedule job
                    mails_job_scheduler.schedule_job(job)
                    job['is_scheduled'] = True
                    store['jobs'] = jobs_temp
                    flash(f"Job[{job_id}] successfully scheduled!", 'success')
                except Exception as e:
                    flash(message=str(e), category='danger')
            break

    return redirect(url_for('jobs'))


@app.route('/stop-scheduled-job/<int:job_id>', methods=['GET'])
@login_required
def stop_scheduled_job(job_id):
    jobs_temp = store['jobs']
    for job in jobs_temp:
        if job['id'] == job_id:
            if job['is_scheduled'] is False:
                flash(f"Job[{job_id}] is not scheduled!", 'warning')
            else:
                mails_job_scheduler.stop_job_thread(job)
                job['is_scheduled'] = False
                store['jobs'] = jobs_temp
                flash(f"Successfully stopped scheduling of Job[{job['id']}].", 'success')
            break

    return redirect(url_for('jobs'))


@app.route('/abbestellen/<int:job_id>/<int:email_id>', methods=['GET'])
def unsubscribe(job_id, email_id):
    # Find the job
    job = next((job for job in store['jobs'] if job['id'] == job_id), None)
    if job:
        # Unsubscribe the email
        email_dict = job['list']
        if email_id in email_dict:
            del email_dict[email_id]
            job['list'] = email_dict
            store['jobs'] = [job if j['id'] == job_id else j for j in store['jobs']]
            return render_template('unsubscribe.html', message="You have successfully unsubscribed from the newsletter.")
        else:
            return render_template('unsubscribe.html', message="Invalid email ID.")
    else:
        return render_template('unsubscribe.html', message="Invalid job ID.")


app.run(debug=True)
