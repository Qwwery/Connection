from flask import Flask, session, render_template, request, redirect, url_for, sessions, make_response, jsonify
from models import db_session
from models.users import User
from models.avatars import Avatar
from models.friends import Friend
from models.about_users import AboutUser
from models.news import News
from models.messages import Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
# from flask_cors import CORS
from check_email import is_valid_email as check_email_to_correct
from sqlalchemy import or_, and_
from base64 import b64decode, b64encode
from datetime import datetime
from translate import format_date_russian
import os
from werkzeug.utils import secure_filename
from get_info import get_last_message_text, get_friend_status

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
    person = db_sess.query(User).filter(or_(User.special_login == login, User.id == login)).first()
    print(person)
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
        if in_f and out_f:
            check = in_f.stat
        else:
            check = -1


    except Exception as e:
        print(f"Error: {e}")
        return redirect('/')

    news_person = db_sess.query(News).filter(
        or_(News.user_id == person.id, News.user_id == person.special_login)).order_by(News.created_at.desc()).all()

    for news in news_person:
        news.created_at = format_date_russian(news.created_at)

    info = {
        'name': person.name,
        "last_name": person.last_name,
        "ava": avatar_bytes,
        "user_id": person.id,
        "check": check,
        "hide_interests": hide_interests,
        "hide_birthday": hide_birthday,
        "hide_city": hide_city,
        "news_list": news_person,
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
        friends = db_sess.query(Friend).filter(and_(Friend.user_id == user, Friend.stat == 1)).all()
        for friend in friends:
            friend.user.avatar.image_data = str(friend.user.avatar.image_data).replace("b'", "").replace("'", "")

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
    finally:
        db_sess.close()


@app.route('/send-friend-request', methods=['POST'])
@login_required
def send_friend_request():
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

        new_friend_request_2 = Friend(
            user_id=friend_id,
            friend_id=current_user.id,
            name_friends=current_user.name,  # Например, статус "в ожидании"
            stat=2,
        )

        db_sess.add(new_friend_request)
        db_sess.add(new_friend_request_2)

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
            Friend.friend_id == friend_id
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
        print(friend_id)
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
        db_sess.query(Friend).filter(and_(Friend.friend_id == current_user.id, Friend.user_id == friend_id)).update({
            "stat": 1
        })
        db_sess.query(Friend).filter(and_(Friend.user_id == current_user.id, Friend.friend_id == friend_id)).update({
            "stat": 1
        })
        db_sess.commit()

        return jsonify({'success': True, 'message': 'Заявка успешно принята.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/reject-friend-request', methods=['POST'])
@login_required
def reject_friend_request():
    try:
        data = request.get_json()
        friend_id = data.get('friend_id')
        if not friend_id:
            return jsonify({'success': False, 'message': 'ID друга не указан.'}), 400

        db_sess = db_session.create_session()
        # Находим заявку в друзья
        friend_request = db_sess.query(Friend).filter(
            Friend.friend_id == current_user.id,
            Friend.user_id == friend_id,
            Friend.stat == 0
        ).first()

        friend_request_2 = db_sess.query(Friend).filter(
            Friend.friend_id == friend_id,
            Friend.user_id == current_user.id,
            Friend.stat == 2
        ).first()

        if not friend_request:
            return jsonify({'success': False, 'message': 'Заявка не найдена.'}), 404

        # Удаляем заявку
        db_sess.delete(friend_request)
        db_sess.delete(friend_request_2)
        db_sess.commit()

        return jsonify({'success': True, 'message': 'Заявка отклонена.'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db_sess.close()


@app.route('/friend-requests')
@login_required
def friend_requests():
    db_sess = db_session.create_session()
    try:
        incoming_requests = db_sess.query(Friend).filter(and_(
            Friend.friend_id == current_user.id,
            Friend.stat == 0
        )).all()

        requests_data = [
            {
                "id": req.id,
                "sender_name": f"{req.user.name} {req.user.last_name}",
                "special_login": req.user.special_login,
                "friend_id": req.user.id,
                "ava": str(req.user.avatar.image_data).replace("b'", "").replace("'", ""),
            }
            for req in incoming_requests
        ]
    except Exception as e:
        print(str(e))
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db_sess.close()

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

            # Поиск пользователей
            users = db_sess.query(User).filter(
                (User.name.ilike(f"%{query}%")) |
                (User.last_name.ilike(f"%{query}%")) |
                (User.special_login.ilike(f"%{query}%"))
            ).all()

            # Формируем данные для ответа
            users_data = [
                {
                    "id": user.id,
                    "name": user.name,
                    "last_name": user.last_name,
                    "special_login": user.special_login,
                    "ava": str(user.avatar.image_data).replace("b'", "").replace("'", ""),
                    "friend_status": get_friend_status(user.id),
                }
                for user in users
                if user.id != current_user.id
            ]

            return jsonify({'success': True, 'users': users_data}), 200

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/remove-friend', methods=['POST'])
@login_required
def remove_friend():
    try:
        data = request.get_json()
        friend_id = data.get('friend_id')

        if not friend_id:
            return jsonify({'success': False, 'message': 'ID друга не указан.'}), 400

        db_sess = db_session.create_session()

        # Удаляем записи о дружбе
        db_sess.query(Friend).filter(
            ((Friend.user_id == current_user.id) & (Friend.friend_id == friend_id)) |
            ((Friend.user_id == friend_id) & (Friend.friend_id == current_user.id))
        ).delete(synchronize_session=False)

        db_sess.commit()

        return jsonify({'success': True, 'message': 'Друг успешно удален.'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/pending-friend", methods=["POST"])
@login_required
def pending_friend():
    data = request.get_json()
    friend_id = data.get('friend_id')
    print(friend_id)
    if not friend_id:
        return jsonify({"success": False, "message": "Нет id пользователя."}), 400

    try:
        db_sess = db_session.create_session()

        db_sess.query(Friend).filter(and_(Friend.user_id == current_user.id, Friend.friend_id == friend_id)).update({
            "stat": -1
        })
        db_sess.query(Friend).filter(and_(Friend.user_id == friend_id, Friend.friend_id == current_user.id)).update({
            "stat": -1
        })
        db_sess.commit()
    except Exception as e:
        print("Ошибка с изменением данных в БД")
        return jsonify({"success": False, "message": str(e)}), 500
    return jsonify({"success": True, "message": "Заявка отменена"}), 200


# @app.route("/send-message", methods=["POST"])
# @login_required
# def send_message():
#     try:
#         print(1)
#         data = request.get_json()
#         friend_id = data.get("friend_id")
#         text = data.get("text")  # Используем "text" вместо "message"
#         print(2)
#         if not friend_id or not text:
#             return jsonify({"success": False, "message": "Недостаточно данных."}), 400
#         print(3)
#         db_sess = db_session.create_session()
#
#         # Создаем новое сообщение
#         new_message = Message(
#             sender_id=current_user.id,
#             receiver_id=friend_id,
#             text=text,
#             timestamp=datetime.now()
#         )
#         db_sess.add(new_message)
#         db_sess.commit()
#         print(4)
#         return jsonify({"success": True, "message": "Сообщение отправлено."}), 200
#
#     except Exception as e:
#         print("Error", e)
#         return jsonify({"success": False, "message": str(e)}), 500


@app.route("/messages/<int:friend_id>", methods=["GET"])
@login_required
def messages(friend_id):
    db_sess = db_session.create_session()
    try:
        # Получаем список всех друзей текущего пользователя
        friends = db_sess.query(Friend).filter(
            Friend.user_id == current_user.id,
            Friend.stat == 1  # Только друзья
        ).all()

        # Генерация списка chat_data
        chat_data = [
            {
                "friend_id": friend.friend_id,
                "name": friend.friend.name,
                "avatar": str(friend.friend.avatar.image_data).replace("b'", "").replace("'", ""),
                "last_message": get_last_message_text(db_sess, friend.friend_id, friend.id),
            }
            for friend in friends
        ]

        # Если friend_id == 0, не показываем чат
        if friend_id == 0:
            return render_template("messages.html", chats=chat_data, selected_chat=None)

        # Иначе получаем выбранный чат
        selected_chat = next((chat for chat in chat_data if chat["friend_id"] == friend_id), None)
        if not selected_chat:
            return render_template("messages.html", chats=chat_data, selected_chat=None)

        # Получаем сообщения для выбранного чата
        messages = db_sess.query(Message).filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
            ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.timestamp.asc()).all()

        message_data = [
            {
                "text": msg.text,
                "is_sent": msg.sender_id == current_user.id,
                "time": msg.timestamp.strftime("%H:%M"),
                "sent": current_user.id,
            }
            for msg in messages
        ]

        return render_template("messages.html", chats=chat_data, selected_chat=selected_chat, messages=message_data,
                               friend_id=friend_id)

    except Exception as e:
        print(f"Ошибка: {e}")
        return render_template("messages.html", chats=[], selected_chat=None, messages=[])
    finally:
        db_sess.close()


@app.route("/get_new_messages/<int:friend_id>", methods=["GET"])
@login_required
def get_new_messages(friend_id):
    db_sess = db_session.create_session()
    try:
        last_message_id = int(request.args.get("last_message_id", 0))

        # Получаем новые сообщения для выбранного чата
        new_messages = db_sess.query(Message).filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == friend_id)) |
            ((Message.sender_id == friend_id) & (Message.receiver_id == current_user.id)),
            Message.id > last_message_id
        ).order_by(Message.timestamp.asc()).all()

        # Формируем JSON-ответ
        message_data = [
            {
                "id": msg.id,
                "text": msg.text,
                "is_sent": msg.sender_id == current_user.id,
                "time": msg.timestamp.strftime("%H:%M"),
            }
            for msg in new_messages
        ]

        return jsonify(message_data)

    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify([]), 500
    finally:
        db_sess.close()


@app.route("/send_message", methods=["POST"])
@login_required
def send_message():
    db_sess = db_session.create_session()
    try:
        data = request.json
        text = data.get("text")
        receiver_id = data.get("receiver_id")

        if not text or not receiver_id:
            return jsonify({"status": "error", "message": "Недостаточно данных"}), 400

        # Создаем новое сообщение
        new_message = Message(
            text=text,
            sender_id=current_user.id,
            receiver_id=receiver_id,
            timestamp=datetime.utcnow()
        )
        db_sess.add(new_message)
        db_sess.commit()

        return jsonify({"status": "success", "message": "Сообщение отправлено"})

    except Exception as e:
        print(f"Ошибка: {e}")
        return jsonify({"status": "error", "message": "Ошибка сервера"}), 500
    finally:
        db_sess.close()


if __name__ == '__main__':
    main()
