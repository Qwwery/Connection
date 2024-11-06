from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from check_email import is_valid_email as check_email_to_correct

app = Flask(__name__)
app.secret_key = 'DOTA 2'
db_session.global_init('db/db.db')
login_manager = LoginManager()
login_manager.init_app(app)


def main():
    app.run(debug=True)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/', methods=['GET', 'POST'])
def start():
    if request.method == 'GET':
        if not current_user.is_authenticated:
            return render_template('hello.html')
        else:
            return redirect(url_for('feed'))
    elif request.method == 'POST':
        db_sess = db_session.create_session()

        if request.form.get('button') == 'registration':
            form_email = request.form.get('email')
            form_password = request.form.get('password')
            session['email'] = form_email
            session['password'] = form_password

            if db_sess.query(User).filter(User.email == form_email).first():
                return redirect(url_for('authorization'))

            return redirect(url_for('registration'))
        else:
            form_login = request.form.get('login')
            form_password = request.form.get('password')
            session['login'] = form_login
            session['password'] = form_password
            return redirect(url_for('authorization'))


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if session.get('logged_in'):
        return redirect(url_for('feed'))
    if request.method == 'GET':
        info = {
            'email': session.get('email'),
            'password': session.get('password')
        }
        return render_template('registration.html', info=info)
    else:
        return redirect(url_for('authorization'))


@app.route('/check-email', methods=['POST'])
def check_email():
    db_sess = db_session.create_session()
    data = request.json
    email = data.get("email")
    is_check_email_to_correct = False
    if not check_email_to_correct(email):
        is_check_email_to_correct = True
    exists = db_sess.query(User).filter(User.email == email).first()
    if exists:
        return jsonify({"error_exists": True, 'errror_check_email_to_correct': is_check_email_to_correct})
    else:
        return jsonify({"error_exists": False, 'error_check_email_to_correct': is_check_email_to_correct})


@app.route('/registration-new-user', methods=['POST'])
def register_new_user():
    db_sess = db_session.create_session()
    data = request.json
    name = data.get("name")
    email = data.get("email")
    last_name = data.get("lastName")
    password = data.get("password")
    login = data.get("login")
    user = User(name=name, email=email, last_name=last_name, special_login=login)
    user.set_password(password)
    db_sess.add(user)
    db_sess.commit()

    user_info = db_sess.query(User).filter(User.email == email).first()
    db_sess.commit()

    login_user(user_info, remember=True)
    print(current_user)
    return 'ok'


@app.route('/authorization', methods=['GET', 'POST'])
def authorization():
    return render_template('authorization.html')


@app.route('/privacy', methods=['GET'])
def privacy():
    with open('static/text/privacy.txt', 'r', encoding='utf-8') as f:
        privacy_text = f.read()
    info = {
        'privacy_text': privacy_text
    }
    return render_template('privacy.html', **info)


@app.route('/user_agreement', methods=['GET'])
def user_agreement():
    with open('static/text/user_agreement.txt', 'r', encoding='utf-8') as f:
        user_agreement_text = f.read()
    info = {
        "user_agreement_text": user_agreement_text
    }
    return render_template('user_agreement.html', **info)


@app.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    return render_template('feed.html')


if __name__ == '__main__':
    main()
