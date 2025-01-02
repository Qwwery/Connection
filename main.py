from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from check_email import is_valid_email as check_email_to_correct
from sqlalchemy import or_

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


@app.route('/', methods=["GET"])
def start():
    if request.method == 'GET':
        if not current_user.is_authenticated:
            return render_template('hello.html')
        else:
            return redirect(url_for('feed'))


@app.route('/check-registration', methods=["POST"])
def check_registration():
    db_sess = db_session.create_session()
    data = request.json

    email = data.get('email')
    password = data.get('password')

    if db_sess.query(User).filter(User.email == email).first():
        return jsonify({'error': 'Данная почта уже используется'})
    if email == '' or password == '':
        return jsonify({'error': "Проверьте правильность заполнения данных"})
    if not check_email_to_correct(email):
        return jsonify({'error': "Почта введена в неправильном формате"})
    session['email'] = email
    session['password'] = password
    return jsonify({'ok': True})


@app.route('/check-authorization', methods=['POST'])
def check_authorization():
    db_sess = db_session.create_session()
    data = request.json
    login = data.get('email')
    password = data.get('password')

    th_user = db_sess.query(User).filter(
        or_(User.email == login, User.special_login == login)).first()

    if th_user:
        if th_user.check_password(password):
            login_user(th_user, remember=True)
            return jsonify({'ok': True})
    return jsonify({'error': "Неверная почта или пароль"})


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.is_authenticated:
        return redirect(url_for('feed'))
    if request.method == 'GET':
        try:
            info = {
                'login': session.get("login") if session.get("login") else '',
                'email': session.get('email') if session.get('email') else '',
                'password': session.get('password') if session.get('password') else ''
            }
        except KeyError:
            info = {}
        return render_template('registration.html', info=info)


@app.route('/check-all-reg', methods=['POST'])  # Проверка перед регистрацией нового пользователя
def check_email():
    db_sess = db_session.create_session()
    data = request.json
    email = data.get("email")
    is_check_email_to_correct = not check_email_to_correct(email)

    exists = db_sess.query(User).filter(User.email == email).first()
    exists = True if exists else False

    special_login = data.get("special_login")
    error_login = True if db_sess.query(User).filter(User.special_login == special_login).first() else False

    return jsonify(
        {"error_exists": exists, 'error_check_email_to_correct': is_check_email_to_correct, 'error_login': error_login})


@app.route('/registration-new-user', methods=['POST'])  # Если проверка выше прошли, то регистрировать нового пользователя
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
    return 'ok'


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
