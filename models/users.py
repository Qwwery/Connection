# models/user.py
import sqlalchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    special_login = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    last_name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=False)

    # Отношения с другими моделями
    avatar = relationship("Avatar", back_populates="user", uselist=False)
    about = relationship("AboutUser", back_populates="user", uselist=False)

    # Отношение к новостям (используем back_populates)
    news = relationship("News", back_populates="author")

    friends = relationship(
        "Friend",
        back_populates="user",
        foreign_keys="[Friend.user_id]"
    )

    def __repr__(self):
        return f'<User> id:{self.id} name:{self.name} login:{self.special_login} email:{self.email}'

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)