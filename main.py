from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from flask_login import login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.secret_key = 'DOTA 2'
db_session.global_init('db/db.db')


def main():
    app.run(debug=True)


@app.route('/', methods=['GET', 'POST'])
def start():
    if request.method == 'GET':
        if not session.get('logged_in'):
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
        # db_sess = db_session.create_session()
        # form_name = request.form.get('name')
        # form_last_name = request.form.get('lastName')
        # form_login = request.form.get('login')
        # form_email = request.form.get('email')
        # form_password = request.form.get('password')

        # check = db_sess.query(User).filter(User.email == form_email).first()

        return redirect(url_for('authorization'))


@app.route('/check-email', methods=['POST'])
def check_email():
    db_sess = db_session.create_session()
    data = request.json
    email = data.get("email")
    exists = db_sess.query(User).filter(User.email == email).first()
    if exists:
        return jsonify({"exists": True})
    else:
        return redirect(url_for('registration'))


@app.route('/registration-new-user', methods=['POST'])
def register_new_user():
    db_sess = db_session.create_session()
    data = request.json
    name = data.get("name")
    email = data.get("email")
    last_name = data.get("lastName")
    password = data.get("password")
    login = data.get("login")
    print(name, email, last_name, password, login)
    user = User(name=name, email=email, last_name=last_name, special_login=login)
    user.set_password(password)
    db_sess.add(user)
    db_sess.commit()
    return 'ok'


@app.route('/authorization', methods=['GET', 'POST'])
def authorization():
    return render_template('authorization.html')


@app.route('/privacy', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html')


@app.route('/feed', methods=['GET', 'POST'])
def feed():
    return render_template('feed.html')


if __name__ == '__main__':
    main()
