# models/news.py
from datetime import datetime
from .db_session import SqlAlchemyBase
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import json


class News(SqlAlchemyBase):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(40), nullable=False)  # Заголовок новости
    content = Column(Text(512), nullable=False)  # Текст новости
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата создания
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Автор новости
    image = Column(Text)

    # Отношение к пользователю (используем back_populates)
    author = relationship("User", back_populates="news")

    def set_images(self, image_list):
        """Преобразует список изображений в JSON."""
        self.images = json.dumps(image_list)

    def get_images(self):
        """Возвращает список изображений из JSON."""
        return json.loads(self.images) if self.images else []

    def __repr__(self):
        return f'<News {self.title}>'
