from datetime import datetime

def format_date_russian(date):
    # Список русских названий месяцев
    months = [
        "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
        "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
    ]

    # Форматируем дату
    day = date.day
    month = months[date.month - 1]  # Названия месяцев начинаются с индекса 0
    year = date.year

    return f"{day} {month} {year}"
