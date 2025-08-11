import csv
import os
from flask_bootstrap import Bootstrap5
from flask import send_file
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileAllowed, FileRequired
from jsonstore import JsonStore
import time
import logging
import uuid
from werkzeug.utils import secure_filename
from wtforms.fields import *
import sched
from dotenv import load_dotenv
import threading
from threading import Thread, Event
from datetime import datetime, timedelta
import uuid
from wtforms.validators import DataRequired, Length, Regexp
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from secrets import compare_digest
from mail_sender import send_emails
from wtforms import EmailField, SubmitField
from wtforms.validators import DataRequired
from urllib.parse import unquote
from flask import make_response
from functools import wraps, update_wrapper
from datetime import datetime

load_dotenv()

store = JsonStore('config.json')

app = Flask(__name__)

app.secret_key = 'dev'

login_manager = LoginManager(app)

bootstrap = Bootstrap5(app)

csrf = CSRFProtect(app)
logging.getLogger('werkzeug').disabled = True

logger = logging.getLogger(__name__)
logging.basicConfig(filename='mail-eagle.log', encoding='utf-8', level=logging.DEBUG)


class TaskManager:
    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.tasks = {}
        self.lock = threading.Lock()

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while True:
            self.lock.acquire()
            self.scheduler.run(blocking=False)
            self.lock.release()
            time.sleep(0.1)

    def add_task(self, name, delay, priority, action, argument=()):
        self.lock.acquire()
        event = self.scheduler.enter(delay, priority, self.run_task, (name, action, argument))
        self.tasks[name] = {'event': event, 'action': action, 'argument': argument}
        self.lock.release()
        logger.info(f"Task '{name}' added with delay {delay}s and priority {priority}.")

    def remove_task(self, name):
        self.lock.acquire()
        if name in self.tasks:
            event = self.tasks[name]['event']
            self.scheduler.cancel(event)
            del self.tasks[name]
            logger.info(f"Task '{name}' removed.")
        else:
            logger.info(f"Task '{name}' removed.")
        self.lock.release()

    def list_tasks(self):
        self.lock.acquire()
        for name, task_info in self.tasks.items():
            print(f" - {name}: Action={task_info['action'].__name__}, Argument={task_info['argument']}")
        self.lock.release()

    def run_task(self, name, action, argument):
        def task_wrapper():
            logger.info(f"Task '{name}' started.")
            action(*argument)
            logger.info(f"Task '{name}' finished.")
            job = get_job_by_uuid(name)
            job['is_finished'] = True

            store['jobs'] = [job for job in store['jobs'] if job['job_uuid'] != name]
            store['jobs'] += [job]

            self.lock.acquire()
            if name in self.tasks:
                del self.tasks[name]
            self.lock.release()

        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()


# init task-manager
manager = TaskManager()
manager.start()


def get_blacklist(file_path='blacklist.txt'):
    try:
        with open(file_path, 'r') as file:
            blacklist = file.readlines()
        # Strip newline characters from each email address
        blacklist = [email.strip() for email in blacklist]
    except FileNotFoundError:
        # Return an empty list if the file does not exist
        blacklist = []
    return blacklist


def subtract_lists(list1, list2):
    return [item for item in list1 if item not in list2]


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


class BlacklistEntryForm(FlaskForm):
    entry = StringField('Blacklist Entry', validators=[DataRequired()])
    submit = SubmitField('Submit')


class BlacklistCSVForm(FlaskForm):
    column = StringField('CSV Column', validators=[DataRequired()])
    file = FileField('CSV File', validators=[DataRequired()])
    submit = SubmitField('Upload')


class UnsubscribeForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    submit = SubmitField('Unsubscribe')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    login_form = LoginForm()

    if login_form.validate_on_submit():
        if user.username == login_form.username.data and compare_digest(user.password, login_form.password.data):
            login_user(user)

            logger.info(f"Login attempt successful.")
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


def read_blacklist():
    blacklist_path = 'blacklist.txt'
    if os.path.exists(blacklist_path):
        with open(blacklist_path, 'r') as file:
            lines = file.readlines()
        return [{'id': idx + 1, 'entry': line.strip()} for idx, line in enumerate(lines)]
    return []


@app.route('/blacklist', methods=['GET'])
def blacklist():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        blacklist_data = read_blacklist()

        titles = [
            ('id', 'ID'),
            ('entry', 'Blacklist Entry')
        ]

        blacklist_table_data = TableData(blacklist_data, titles)

        entry_form = BlacklistEntryForm()
        csv_form = BlacklistCSVForm()

        return render_template('blacklist.html', blacklist_data=blacklist_table_data, entry_form=entry_form,
                               csv_form=csv_form)


def update_blacklist(entry):
    if entry not in get_blacklist():
        with open('blacklist.txt', 'a') as file:
            file.write(entry + '\n')


@app.route('/blacklist/text-entry', methods=['POST'])
def blacklist_text_entry():
    form = BlacklistEntryForm()
    if form.validate_on_submit():
        entry = form.entry.data

        update_blacklist(entry)

        logger.info(f'Received blacklist entry: {entry}')
        flash("Successfully added blacklist entry!", 'success')
    return redirect(url_for('blacklist'))


@app.route('/blacklist/csv-upload', methods=['POST'])
def blacklist_csv_upload():
    form = BlacklistCSVForm()
    if form.validate_on_submit():
        column = form.column.data
        file = form.file.data

        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join('uploads', filename)
            file.save(filepath)

            with open(filepath, newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    update_blacklist(row[column])

            logger.info(f'Successfully processed blacklist-CSV file!')
            flash("Successfully processed CSV file!", 'success')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')
            logger.error(f'An error occurred: {str(e)}')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    else:
        logger.error(f'Failed to upload CSV file. Please ensure the form is filled out correctly.')
        flash("Failed to upload CSV file. Please ensure the form is filled out correctly.", 'danger')

    return redirect(url_for('blacklist'))


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
        logger.info(f'Email sender configuration saved successfully!')

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
            csv_reader = csv.reader(csv_file, delimiter=',')
            header = next(csv_reader)
            if column_name in header:
                column_index = header.index(column_name)
                for row in csv_reader:
                    if 0 <= column_index < len(row):
                        column_data.append(row[column_index])
                    else:
                        raise IndexError(f"Column index {column_index} out of range.")
            else:
                logger.error(f"Column '{column_name}' not found in CSV file header.")
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


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


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

            if csv_file:
                csv_file.save(csv_file_path)
            if content_file:
                content_file.save(content_file_path)

            job = {
                "id": len(store['jobs']) + 1,
                "job_uuid": str(uuid.uuid4()),
                "name": form.name.data,
                "subject": form.subject.data,
                "is_scheduled": False,
                "is_finished": False,
                "csv_path": csv_file_path,
                "schedule_date": form.date.data.strftime('%m/%d/%Y %H:%M:%S'),
                "content_file_path": content_file_path,
                "list": remove_duplicates(subtract_lists(parse_csv_column(csv_file_path, form.column.data), get_blacklist())),
                "successful_emails": [],
                "failed_emails": []
            }

            store['jobs'] += [job]

            print(store['jobs'])

            flash("Successfully created job!", 'success')
            logger.info(f"Successfully created job[{form.name.data}]!")
            return redirect(url_for('jobs'))
        except Exception as e:
            flash(f"An error occurred: {e}", 'error')
            logger.error(f"An error occurred: {e} while creating job!")

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


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return update_wrapper(no_cache, view)


@app.route('/open/<int:job_id>', methods=['GET'])
@login_required
@nocache
def open_job(job_id):
    job = get_job_by_id(job_id)

    if job:

        successful_emails = [{'id': idx + 1, 'email': email} for idx, email in enumerate(job['successful_emails'])]
        failed_emails = [{'id': idx + 1, 'email': email} for idx, email in enumerate(job['failed_emails'])]
        emails = [{'id': idx + 1, 'email': email} for idx, email in enumerate(job['list'])]

        titles = [
            ('id', 'ID'),
            ('email', 'Email')
        ]

        successful_emails_data = TableData(successful_emails[:50], titles)
        failed_emails_data = TableData(failed_emails[:50], titles)
        emails_data = TableData(emails[:50], titles)

        return render_template('open-job.html', job=job,
                               successful_emails_data=successful_emails_data,
                               failed_emails_data=failed_emails_data,
                               emails_data=emails_data,
                               failed_count=len(failed_emails) if failed_emails else 0,
                               success_count=len(successful_emails) if successful_emails else 0,
                               total_count=len(job['list']) if job['list'] else 0
                               )
    else:
        flash(f"Job[{job_id}] not found!", 'error')
        logger.error(f"Job[{job_id}] not found!")
        return redirect(url_for('jobs'))


def unsubscribe_email(email_dict, email_id):
    if email_id in email_dict:
        logger.info(f"{email_dict[email_id]} successfully unsubscribed!")
        del email_dict[email_id]
    else:
        print(f"Email ID {email_id} not found.")
        logger.error(f"Email ID {email_id} not found.")


def reload_store():
    # disallow caching --> some fucked up shit code but works wonders :=)
    global store
    store = JsonStore('config.json')


def get_job_by_uuid(_uuid):
    reload_store()
    for job in store['jobs']:
        if job['job_uuid'] == _uuid:
            return job
    return None


def get_job_by_id(job_id):
    reload_store()
    for job in store['jobs']:
        if job['id'] == job_id:
            return job
    return None


def delete_job_files(job):
    if os.path.exists(job['csv_path']):
        os.remove(job['csv_path'])
    if os.path.exists(job['content_file_path']):
        os.remove(job['content_file_path'])


@app.route('/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = get_job_by_id(job_id)
    if job:
        delete_job_files(job)
        store['jobs'] = [job for job in store['jobs'] if job['id'] != job_id]

        manager.remove_task(job['job_uuid'])

        flash(f"Job[{job_id}] successfully deleted!", 'success')
        logger.info(f"Job[{job_id}] successfully deleted!")
    else:
        flash(f"Job[{job_id}] not found!", 'error')
        logger.error(f"Job[{job_id}] not found")

    return redirect(url_for('jobs'))


@app.route('/schedule/<int:job_id>', methods=['GET'])
@login_required
def schedule_job(job_id):
    jobs_temp = store['jobs']
    for job in jobs_temp:
        if job['id'] == job_id:
            if job['is_scheduled']:
                flash(f"Job[{job_id}] is already scheduled!", 'warning')
                logger.warning(f"Job[{job_id}] is already scheduled!")
            else:
                try:
                    delay = ((datetime
                              .strptime(job["schedule_date"], "%m/%d/%Y %H:%M:%S") - datetime.now())
                             .total_seconds())
                    print(f"Delay: {delay}s...")

                    if delay <= 0:
                        flash(f"Job[{job_id}] cannot be scheduled in the past!", 'danger')
                        logger.warning(f"Job[{job_id}] cannot be scheduled in the past!")
                    else:
                        email_args = {
                            'smtp_server': store['email_sender.smtp_server'],
                            'smtp_port': store['email_sender.smtp_port'],
                            'sender_email': store['email_sender.sender_email'],
                            'sender_password': store['email_sender.sender_password'],
                            'email_list': job['list'],
                            'subject': job['subject'],
                            'content': job['content_file_path'],
                            'job_id': job['id']
                        }

                        manager.add_task(job['job_uuid'], int(delay), 1, lambda: send_emails(**email_args))

                        job['is_scheduled'] = True
                        store['jobs'] = jobs_temp
                        flash(f"Job[{job_id}] successfully scheduled!", 'success')
                        logger.info(f"Job[{job_id}] successfully scheduled!")
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
                logger.warning(f"Job[{job_id}] is not scheduled!")
            else:
                manager.remove_task(job['job_uuid'])

                job['is_scheduled'] = False
                store['jobs'] = jobs_temp
                flash(f"Successfully stopped scheduling of Job[{job['id']}].", 'success')
                logger.info(f"Successfully stopped scheduling of Job[{job['id']}].")
            break

    return redirect(url_for('jobs'))


@app.route('/abbestellen', methods=['GET', 'POST'])
def abbestellen():
    form = UnsubscribeForm()
    if form.validate_on_submit():
        email_address = form.email.data
        email = unquote(email_address)
        email = email.strip()
        email = email.lower()
        unsubscribed = True

        update_blacklist(email)

        for job in store['jobs']:
            if email_address in job['list']:
                job['list'].remove(email_address)
                store['jobs'] = [j if j['id'] != job['id'] else job for j in store['jobs']]

                unsubscribed = True

        if unsubscribed:
            return render_template('unsubscribe.html',
                                   message=f"You have successfully unsubscribed {email_address} from the newsletter.")
        else:
            return render_template('unsubscribe.html', message="Email address not found.")

    return render_template('unsubscribe_form.html', form=form)


@app.route('/abbestellen/<email>', methods=['GET'])
def unsubscribe(email):
    email = unquote(email)
    email = email.strip()
    email = email.lower()
    unsubscribed = True
    update_blacklist(email)

    for job in store['jobs']:
        if email in job['list']:
            job['list'].remove(email)
            store['jobs'] = [j if j['id'] != job['id'] else job for j in store['jobs']]
            unsubscribed = True

    if unsubscribed:
        return render_template('unsubscribe.html',
                               message=f"You have successfully unsubscribed {email} from the newsletter.")
    else:
        return render_template('unsubscribe.html', message="Email address not found.")


def parse_log_file(log_file):
    logs = []

    with open(log_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line:
                parts = line.split(':', 2)
                if len(parts) == 3:
                    log_level_str = parts[0].strip()
                    log_level = get_log_level(log_level_str)
                    message = parts[2].strip()

                    log_entry = {
                        'log_level': log_level,
                        'message': message
                    }

                    logs.append(log_entry)
                else:
                    logs.append({
                        'log_level': 'UNKNOWN',
                        'message': line
                    })
    return logs


def get_log_level(log_level_str):
    if log_level_str == 'ERROR' or log_level_str == 'ERR':
        return 'ERROR'
    elif log_level_str == 'DEBUG':
        return 'DEBUG'
    elif log_level_str == 'INFO':
        return 'INFO'
    elif log_level_str == 'WARNING' or log_level_str == 'WARN':
        return 'WARNING'
    else:
        return 'UNKNOWN'


@app.route('/logging')
@login_required
def logging():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        logs = parse_log_file('mail-eagle.log')
        print(logs)
        return render_template('logging.html', logs=logs[-10:][::-1])
    

@app.route('/download_logs')
def download_logs():
    log_file_path = 'mail-eagle.log'

    # Send the log file as an attachment
    return send_file(log_file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)