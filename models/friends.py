import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, ForeignKey


class Friend(SqlAlchemyBase, UserMixin):
    __tablename__ = 'friends'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name_friends = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Переименовано из user
    friend_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Добавлен внешний ключ
    stat = Column(Integer, nullable=False)  #    -1      \     0      \   1   \       2
                                           #  не друзья \ в ожидании \ друзья \ заявка в друзья
    # Отношение к пользователю (основной пользователь)
    user = relationship(
        "User",
        back_populates="friends",
        foreign_keys=[user_id]  # Указываем, что связь происходит через user_id
    )

    # Отношение к другу (пользователь-друг)
    friend = relationship(
        "User",
        foreign_keys=[friend_id]  # Указываем, что связь происходит через friend_id
    )

    def __repr__(self):
        return f'<Friend> userid:{self.user_id} friendid:{self.friend_id}'