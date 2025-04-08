from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from models.avatars import Avatar
from models.friends import Friend
from models.about_users import AboutUser
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# from flask_cors import CORS
from check_email import is_valid_email as check_email_to_correct
from sqlalchemy import or_
from base64 import b64decode, b64encode

app = Flask(__name__)
# CORS(app)
app.secret_key = 'DOTA 2'
db_session.global_init('db/db.db')
login_manager = LoginManager()
login_manager.init_app(app)


def main():
    app.run(debug=True)


@login_manager.user_loader
def load_user(user_id):  # ХЗ, какая-то инициализация бд, видимо
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/', methods=["GET"])  # Если авторизован, то переносить на страницу новостей, иначе - нет.
def start():
    if request.method == 'GET':
        if not current_user.is_authenticated:
            return render_template('hello.html')
        else:
            return redirect(url_for('feed'))


@app.route('/home', methods=["GET"])  # Твой профиль
def home():
    if not current_user.is_authenticated:
        return redirect("/")

    db_sess = db_session.create_session()
    try:
        ava = db_sess.query(Avatar).filter_by(user_id=current_user.id).first().image_data
        ava = str(ava).replace("b'", "").replace("'", "")
        name = current_user.name
        last_name = current_user.last_name
        about = db_sess.query(AboutUser).filter_by(user_id=current_user.id).first()
        interests = about.interests if about.interests != '-' else ''
        birthday = about.birthday if about.birthday != '-' else ''
        city = about.city if about.city != '-' else ''
        email = current_user.email
        hide_interests = about.hide_interests
        hide_birthday = about.hide_birthday
        hide_city = about.hide_city
        info = {
            'name': name,
            'last_name': last_name,
            'ava': ava,
            'birthday': birthday,
            'city': city,
            'interests': interests,
            "email": email,
            "hide_interests": hide_interests,
            "hide_birthday": hide_birthday,
            "hide_city": hide_city,
        }
        return render_template("home.html", **info)
    except Exception as e:
        print(f"Error: {e}")
        return redirect("/")


@app.route('/prof/<login>', methods=["GET"])  # Профиль другого пользователя
def user(login):
    if not current_user.is_authenticated:
        return redirect('/')
    db_sess = db_session.create_session()
    person = db_sess.query(User).filter(or_(User.special_login == login, User.id == login)).first()
    if person.special_login == current_user.special_login:
        return redirect('/home')
    if person is None:
        return redirect('/')
    try:
        avatar_bytes = db_sess.query(Avatar).filter(Avatar.user_id == person.id).first().image_data
        avatar_bytes = str(avatar_bytes).replace("b'", "").replace("'", "")
        info = {
            'name': person.name,
            "last_name": person.last_name,
            "ava": avatar_bytes
        }
        return render_template('viewprof.html', **info)
    except Exception as e:
        print(f"Error: {e}")
        return redirect('/')


@app.route("/privacy-settings", methods=["POST"])  # Это каждый отдельный пользователь можут поставить отображение своих данных
def privacy_settings():
    data = request.json
    db_sess = db_session.create_session()
    try:
        about_user = db_sess.query(AboutUser).filter_by(user_id=current_user.id).first()
        about_user.interests = data.get('interests', '')
        about_user.birthday = data.get('birthday', '')
        about_user.city = data.get('city', '')
        about_user.hide_interests = data.get('hide_interests', False)
        about_user.hide_birthday = data.get('hide_birthday', False)
        about_user.hide_city = data.get('hide_city', False)
        db_sess.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error: {e}")
        db_sess.rollback()
        return jsonify({"status": "error"}), 500
    finally:
        db_sess.close()


@app.route('/check-registration', methods=["POST"])  # Проверка регистрации (для того, чтобы страница не обновлялась при запросе на регистрацию
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
    db_sess.close()
    return jsonify({'ok': True})


@app.route('/check-authorization', methods=['POST'])  # Проверка для авторизации (сделал для того, чтобы не делать еще 1 страницу
def check_authorization():
    db_sess = db_session.create_session()
    data = request.json
    login = data.get('email')
    password = data.get('password')

    th_user = db_sess.query(User).filter(
        or_(User.email == login, User.special_login == login)).first()

    db_sess.close()
    if th_user:
        if th_user.check_password(password):
            login_user(th_user, remember=True)
            return jsonify({'ok': True})
    return jsonify({'error': "Неверная почта или пароль"})


@app.route('/registration', methods=['GET'])  # хз, какая-то регистрация
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
    db_sess.close()
    return jsonify(
        {"error_exists": exists, 'error_check_email_to_correct': is_check_email_to_correct, 'error_login': error_login})


@app.route('/registration-new-user',
           methods=['POST'])  # Если проверки выше прошли, то регистрировать нового пользователя
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

    with open('static/image/unnamed.jpg', 'rb') as avatar:
        ava64 = b64encode(avatar.read())

    avatar = Avatar(image_data=ava64, user_id=user.id)

    about = AboutUser(user_id=user.id, city='-', birthday="-", interests='-')

    db_sess.add(avatar)
    db_sess.add(about)
    db_sess.commit()

    user_info = db_sess.query(User).filter(User.email == email).first()
    db_sess.close()
    login_user(user_info, remember=True)
    return 'ok'


@app.route('/privacy', methods=['GET']) #  Политика конфеденциальности (хз как это пишется)
def privacy():
    with open('static/text/privacy.txt', 'r', encoding='utf-8') as f:
        privacy_text = f.read()
    info = {
        'privacy_text': privacy_text
    }
    return render_template('privacy.html', **info)


@app.route('/user_agreement', methods=['GET']) # Пользовательское соглашение
def user_agreement():
    with open('static/text/user_agreement.txt', 'r', encoding='utf-8') as f:
        user_agreement_text = f.read()
    info = {
        "user_agreement_text": user_agreement_text
    }
    return render_template('user_agreement.html', **info)


@app.route('/feed', methods=['GET', 'POST']) #  Главная (после регистрации)
@login_required
def feed():
    return render_template('feed.html')

@app.route("/friends", methods=["GET"])
@login_required
def friends():  # Все твои друзья
    db_sess = db_session.create_session()
    try:
        user = current_user.id
        friends = db_sess.query(Friend).filter(Friend.user_id == user)
        for i in friends:
            print(i)
        info = {
            "friends": friends,
            "error": False
        }
        return render_template("friends.html", **info)
    except Exception:
        info = {
            "friends": [],
            "error": True
        }
        return render_template("friends.html", )


if __name__ == '__main__':
    main()
