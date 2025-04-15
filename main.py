from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from models.avatars import Avatar
from models.friends import Friend
from models.about_users import AboutUser
from models.news import News
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# from flask_cors import CORS
from check_email import is_valid_email as check_email_to_correct
from sqlalchemy import or_, and_
from base64 import b64decode, b64encode
from datetime import datetime
from translate import format_date_russian
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
# CORS(app)
app.secret_key = 'DOTA 2'
db_session.global_init('db/db.db')
login_manager = LoginManager()
login_manager.init_app(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Базовая директория проекта
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')  # Папка для загрузки изображений

# Создаем папку для загрузок, если она не существует
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Настройка Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def main():
    app.run(debug=True)


@app.errorhandler(404)
def error404(error):
    return render_template("404.html"), 404


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
        news_list = db_sess.query(News).filter(News.user_id == current_user.id).order_by(News.created_at.desc()).all()

        for news in news_list:
            news.created_at = format_date_russian(news.created_at)

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
            "news_list": news_list,
        }
        return render_template("home.html", **info)

    except Exception as e:
        print(f"Error: {e}")
        return redirect("/")


@app.route('/add-news', methods=['POST'])
def add_news():
    db_sess = db_session.create_session()
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    image_base64 = data.get('image')

    if not title or not content:
        return jsonify({"error": "Заполните все поля"}), 400

    # Сохраняем новость в базе данных
    news = News(title=title, content=content, image=image_base64, user_id=current_user.id)
    db_sess.add(news)
    db_sess.commit()

    return jsonify({
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "image": news.image,  # Возвращаем Base64-строку
        "created_at": format_date_russian(news.created_at),
    })


@app.route('/delete-news/<int:news_id>', methods=['DELETE'])
@login_required
def delete_news(news_id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).get(news_id)

    if not news or news.user_id != current_user.id:
        return jsonify({"error": "Новость не найдена или недоступна"}), 404

    db_sess.delete(news)
    db_sess.commit()

    return jsonify({"success": "Новость удалена"}), 200


@app.route('/edit-news/<int:news_id>', methods=['PUT'])
@login_required
def edit_news(news_id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).get(news_id)
    if not news or news.user_id != current_user.id:
        return jsonify({"error": "Новость не найдена или недоступна"}), 404

    data = request.get_json()
    news.title = data.get('title')
    news.content = data.get('content')
    db_sess.commit()

    return jsonify({
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "created_at": news.created_at.strftime('%d %B %Y')
    }), 200


@app.route('/prof/<login>', methods=["GET", "POST"])  # Профиль другого пользователя
def user(login):
    if not current_user.is_authenticated:
        return redirect('/')
    db_sess = db_session.create_session()
    person = db_sess.query(User).filter(or_(User.special_login == login, User.email == login)).first()
    if person is None:
        return redirect('/')
    if person.special_login == current_user.special_login:
        return redirect('/home')
    try:
        avatar_bytes = db_sess.query(Avatar).filter(Avatar.user_id == person.id).first().image_data
        avatar_bytes = str(avatar_bytes).replace("b'", "").replace("'", "")
        about_user = db_sess.query(AboutUser).filter(AboutUser.user_id == person.id).first()
        hide_interests = about_user.hide_interests
        hide_birthday = about_user.hide_birthday
        hide_city = about_user.hide_city

        in_f = db_sess.query(Friend).filter(Friend.user_id == current_user.id, Friend.friend_id == person.id).first()
        out_f = db_sess.query(Friend).filter(Friend.friend_id == current_user.id, Friend.user_id == person.id).first()
        check = -1
        if in_f:
            if out_f:
                check = 1
            else:
                check = 0
        else:
            if out_f:
                check = 2


    except Exception as e:
        print(f"Error: {e}")
        return redirect('/')
    info = {
        'name': person.name,
        "last_name": person.last_name,
        "ava": avatar_bytes,
        "user_id": person.id,
        "check": check,
        "hide_interests": hide_interests,
        "hide_birthday": hide_birthday,
        "hide_city": hide_city,
    }
    return render_template('viewprof.html', **info)


@app.route("/privacy-settings",
           methods=["POST"])  # Это каждый отдельный пользователь могут поставить отображение своих данных
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


@app.route('/check-registration',
           methods=["POST"])  # Проверка регистрации (для того, чтобы страница не обновлялась при запросе на регистрацию
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


@app.route('/check-authorization',
           methods=['POST'])  # Проверка для авторизации (сделал для того, чтобы не делать еще 1 страницу
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

    about = AboutUser(user_id=user.id, city='Тут пока пусто', birthday="Тут пока пусто", interests='Тут пока пусто')

    db_sess.add(avatar)
    db_sess.add(about)
    db_sess.commit()

    user_info = db_sess.query(User).filter(User.email == email).first()
    db_sess.close()
    login_user(user_info, remember=True)
    return 'ok'


@app.route('/privacy', methods=['GET'])  # Политика конфиденциальности (хз как это пишется)
def privacy():
    with open('static/text/privacy.txt', 'r', encoding='utf-8') as f:
        privacy_text = f.read()
    info = {
        'privacy_text': privacy_text
    }
    return render_template('privacy.html', **info)


@app.route('/user_agreement', methods=['GET'])  # Пользовательское соглашение
def user_agreement():
    with open('static/text/user_agreement.txt', 'r', encoding='utf-8') as f:
        user_agreement_text = f.read()
    info = {
        "user_agreement_text": user_agreement_text
    }
    return render_template('user_agreement.html', **info)


@app.route('/feed', methods=['GET'])
def feed():
    db_sess = db_session.create_session()
    news_list = db_sess.query(News).order_by(News.created_at.desc()).all()

    for news in news_list:
        news.created_at = format_date_russian(news.created_at)

    if current_user.is_authenticated:
        return render_template('feed.html', show_friend_requests=True, show_search_people=True, news_list=news_list)
    else:
        return render_template('feed.html', show_friend_requests=False, show_search_people=False, news_list=news_list)


@app.route("/friends", methods=["GET"])
@login_required
def friends():  # Все твои друзья
    db_sess = db_session.create_session()
    try:
        user = current_user.id
        friends = db_sess.query(Friend).filter(Friend.user_id == user).all()
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
        return render_template("friends.html", **info)


@app.route('/send-friend-request', methods=['POST'])
@login_required
def send_friend_request():
    print(1)
    try:
        # Получаем данные из запроса
        data = request.get_json()
        friend_id = data.get('friend_id')

        if not friend_id:
            return jsonify({'success': False, 'message': 'ID друга не указан.'}), 400

        # Проверяем, что пользователь не отправляет заявку самому себе
        if current_user.id == friend_id:
            return jsonify({'success': False, 'message': 'Нельзя отправить заявку самому себе.'}), 400

        # Проверяем, что заявка еще не отправлена
        db_sess = db_session.create_session()
        existing_request = db_sess.query(Friend).filter(
            Friend.user_id == current_user.id,
            Friend.friend_id == friend_id
        ).first()

        if existing_request:
            return jsonify({'success': False, 'message': 'Заявка уже отправлена.'}), 400
        friend = db_sess.query(User).filter(or_(User.id == friend_id, User.special_login == friend_id)).first()
        # Создаем новую запись о дружбе
        new_friend_request = Friend(
            user_id=current_user.id,
            friend_id=friend_id,
            name_friends=friend.name,  # Например, статус "в ожидании"
            stat=0,
        )
        print(2)
        db_sess.add(new_friend_request)
        db_sess.commit()

        return jsonify({'success': True, 'message': 'Заявка успешно отправлена.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/cancel-friend-request', methods=['POST'])
@login_required
def cancel_friend_request():
    try:
        # Получаем данные из запроса
        data = request.get_json()
        friend_id = data.get('friend_id')

        if not friend_id:
            return jsonify({'success': False, 'message': 'ID друга не указан.'}), 400

        # Проверяем, что заявка существует
        db_sess = db_session.create_session()
        existing_request = db_sess.query(Friend).filter(
            Friend.user_id == current_user.id,
            Friend.friend_id == friend_id,
            stat=-1,
        ).first()

        if not existing_request:
            return jsonify({'success': False, 'message': 'Заявка не найдена.'}), 400

        # Удаляем заявку
        db_sess.delete(existing_request)
        db_sess.commit()

        return jsonify({'success': True, 'message': 'Заявка успешно отменена.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/accept-friend-request', methods=['POST'])
@login_required
def accept_friend_request():
    try:
        # Получаем данные из запроса
        data = request.get_json()
        friend_id = data.get('friend_id')

        if not friend_id:
            return jsonify({'success': False, 'message': 'ID друга не указан.'}), 400

        # Проверяем, что заявка существует
        db_sess = db_session.create_session()
        out_f = db_sess.query(Friend).filter(
            Friend.friend_id == current_user.id,
            Friend.user_id == friend_id
        ).first()

        if not out_f:
            return jsonify({'success': False, 'message': 'Заявка не найдена.'}), 400

        friend = db_sess.query(User).filter(User.id == friend_id).first()
        if not friend:
            return jsonify({'success': False, 'message': 'Пользователь не найден.'}), 400

        # Создаем запись о дружбе для текущего пользователя
        in_f = Friend(
            user_id=current_user.id,
            friend_id=friend_id,
            name_friends=friend.name,
            stat=1,
        )
        db_sess.add(in_f)
        db_sess.commit()

        return jsonify({'success': True, 'message': 'Заявка успешно принята.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/friend-requests')
@login_required
def friend_requests():
    db_sess = db_session.create_session()

    incoming_requests = db_sess.query(Friend).filter(and_(
        Friend.friend_id == current_user.id,
        Friend.stat == 0
    )).all()

    requests_data = [
        {
            "id": req.id,
            "sender_name": f"{req.user.name} {req.user.last_name}",
            "special_login": req.user.special_login,
        }
        for req in incoming_requests
    ]

    return render_template("friend_requests.html", incoming_requests=requests_data)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_people():
    if request.method == 'GET':
        # Отображаем страницу поиска
        return render_template("search.html")

    elif request.method == 'POST':
        try:
            data = request.get_json()
            query = data.get('query')

            if not query:
                return jsonify({'success': False, 'message': 'Запрос пуст.'}), 400

            db_sess = db_session.create_session()
            users = db_sess.query(User).filter(
                (User.name.ilike(f"%{query}%")) | (User.last_name.ilike(f"%{query}%") |
                                                   (User.special_login.ilike(f"%{query}%")))).all()

            users_data = [
                {
                    "id": user.id,
                    "name": user.name,
                    "last_name": user.last_name,
                    "special_login": user.special_login,
                }
                for user in users
            ]

            return jsonify({'success': True, 'users': users_data}), 200

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    main()
