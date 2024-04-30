from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import os

app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

login_manager = LoginManager()
login_manager.init_app(app)

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

# Create a user
user = User('admin', 'password')

@login_manager.user_loader
def load_user(user_id):
    return user if user.get_id() == user_id else None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if user.username == username and user.password == password:
            login_user(user)
            return redirect('/admin')
        return render_template('login.html', error='Invalid username or password.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'POST':
        smtp_server = request.form['smtp_server']
        smtp_port = request.form['smtp_port']
        sender_email = request.form['sender_email']
        sender_password = request.form['sender_password']
        recipient_emails = request.form['recipient_emails']
        message_subject = request.form['message_subject']
        message_content = request.form['message_content']

        # Save SMTP and email data to account.txt
        with open('account.txt', 'w') as f:
            f.write(f"{smtp_server}\n{smtp_port}\n{sender_email}\n{sender_password}")

        # Save recipient emails to emaillist.txt
        with open('emaillist.txt', 'w') as f:
            f.write(recipient_emails)

        # Save message content to msg.txt
        with open('msg.txt', 'w', encoding='utf-8') as f:
            f.write(message_content)

        # Save message subject to subject.txt
        with open('subject.txt', 'w') as f:
            f.write(message_subject)

        return redirect('/send_emails')

    return render_template('admin.html')

@app.route('/send_emails')
@login_required
def send_emails():
    # Logic to send emails based on saved data
    # You can implement this part here

    return "Emails sent successfully."


@app.route('/')
def maintest():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        return render_template('admin.html')


if __name__ == '__main__':
    app.run(debug=True)
