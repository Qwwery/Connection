from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from datetime import datetime


class Message(SqlAlchemyBase):
    __tablename__ = 'messages'

    # Поля таблицы
    id = Column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID сообщения
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # ID отправителя
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # ID получателя
    text = Column(String, nullable=False)  # Текст сообщения
    timestamp = Column(DateTime, default=datetime.now)  # Время отправки сообщения

    # Отношения с таблицей пользователей
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")

    def __repr__(self):
        return f"<Message> from {self.sender_id} to {self.receiver_id}: {self.text[:20]}..."
