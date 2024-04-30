# Import the Flask and Flask-Login libraries
from flask import Flask, render_template, request, session, redirect
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required


# Create a Flask app
app = Flask(__name__)
app.secret_key = '89798789jhvjhjg' 

# Configure Flask-Login
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
user = User('office@sana-bau.com', 'password')

# Register the user with Flask-Login
login_manager.user_loader(load_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        # Get the username and password from the request
        username = request.form['username']
        password = request.form['password']

        # Check if the username and password are valid
        if user.username == username and user.password == password:
            # Login the user
            login_user(user)
            return redirect('/')

        return render_template('login.html', error='Invalid username or password.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route('/')
def admin():
    if not current_user.is_authenticated:
        return redirect('/login')
    else:
        return render_template('admin.html')


# Run the app
if __name__ == '__main__':
    app.run(debug=True)