from models.friends import Friend
from models.messages import Message
from sqlalchemy import or_, and_
from models import db_session
from flask_login import current_user


# Формируем данные для левой панели (список чатов)
# Функция для получения текста последнего сообщения
def get_last_message_text(db_sess, sender_id, receiver_id):
    # Получаем последнее сообщение
    last_message_query = (
        db_sess.query(Message)
        .filter(or_(and_(Message.sender_id == sender_id, Message.receiver_id == receiver_id),
                    and_(Message.sender_id == receiver_id, Message.receiver_id == sender_id)))
        .order_by(Message.timestamp.desc())
        .first()
    )
    # Возвращаем текст или пустую строку
    return last_message_query.text[:10] if last_message_query else ""


# Получение статусов дружбы
def get_friend_status(user_id):
    db_sess = db_session.create_session()
    friend_record = db_sess.query(Friend).filter(and_(
        (Friend.user_id == current_user.id), (Friend.friend_id == user_id)
    )).first()

    if not friend_record:
        return "not_friends"  # Пользователи не друзья
    elif friend_record.stat == 1:
        return "friends"  # Уже друзья
    elif friend_record.stat == 0 and friend_record.user_id == current_user.id:
        return "request_sent"  # Заявка отправлена текущим пользователем
    elif friend_record.stat == 2:
        return "request_received"  # Заявка получена от другого пользователя
    else:
        return "not_friends"