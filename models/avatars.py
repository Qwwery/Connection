from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class Avatar(SqlAlchemyBase, UserMixin):
    __tablename__ = 'avatars'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    image_data = Column(String, nullable=False)  # Поле для хранения изображения в формате base64

    user = relationship("User", back_populates="avatar")
