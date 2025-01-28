from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from flask_login import UserMixin


class AboutUser(SqlAlchemyBase, UserMixin):
    __tablename__ = 'about_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    interests = Column(String, nullable=False)
    birthday = Column(String, nullable=False)
    city = Column(String, nullable=False)

    hide_interests = Column(Boolean, nullable=False, default=False)
    hide_birthday = Column(Boolean, nullable=False, default=False)
    hide_city = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="about")
