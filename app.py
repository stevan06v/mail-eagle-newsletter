from flask_bootstrap import Bootstrap5
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.fields import *
from wtforms.validators import DataRequired, Length, Regexp
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from secrets import compare_digest

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


user = User('admin', 'password')

# Register the user with Flask-Login
login_manager.user_loader(load_user)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 150)])
    submit = SubmitField()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    form = LoginForm()

    if form.validate_on_submit():
        if user.username == form.username.data and compare_digest(user.password, form.password.data):
            # Login the user
            login_user(user)

            flash('Successfully logged in!')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', form=form, error='Invalid username or password')

    return render_template('login.html', form=form)


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


app.run(debug=True)

