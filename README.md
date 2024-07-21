# Описание проекта foodgram

Проект представляет собой веб-приложение на Django для управления рецептами. В проекте реализованы функции для создания, редактирования и удаления рецептов, а также управления избранными рецептами и корзиной покупок. Дополнительно, проект поддерживает создание и использование сокращённых ссылок для рецептов.

Проект включает в себя:
- Административный интерфейс для управления рецептами и их связанными данными.
- Возможность добавления рецептов в избранное и корзину покупок.
- Импорт данных из CSV файлов в модель ингредиентов.
- Генерацию коротких ссылок на рецепты.

## Установка и запуск

1. Клонировать репозиторий:

``` 
git clone git@github.com:mainer93/foodgram.git 
```

2. Перейти в папку проекта:

```
cd foodgram
```

3. Создать и активировать виртуальное окружение:

```
python -m venv venv
```

```
source venv/scripts/activate
```
4. Обновить pip:

```
python -m pip install --upgrade pip
```

5. Установить зависимости из файла requirements.txt:

```
cd backend
pip install -r requirements.txt
```

6. Создать файл .env с полями:
```
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
POSTGRES_DB=foodgram
DB_HOST=db
DB_PORT=5432
DB_NAME=foodgram
SECRET_KEY='ВАШ КЛЮЧ'
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://localhost,https://127.0.0.1
SITE_ADDRESS=http://localhost
```

7. Перейти в папку infra и запустить проект
```
sudo docker compose -f docker-compose.yml up -d --build
```

8. Выполнить миграции
```
sudo docker compose -f docker-compose.yml exec backend python manage.py makemigrations
```
```
sudo docker compose -f docker-compose.yml exec backend python manage.py migrate
```

9. Собрать статику
```
sudo docker compose -f docker-compose.yml exec backend python manage.py collectstatic
```

10. Создадим суперпользователя
```
sudo docker compose -f docker-compose.yml exec backend python manage.py createsuperuser
```

11. Импортируем данные из CSV файла в модель Ingredient
```
sudo docker compose -f docker-compose.yml exec backend python manage.py import_csv
```

# Технологии

* Python 3.9
* Django 3.2.16
* Django REST Framework 3.12.4
* PostgreSQL
* Docker

## Автор проекта

[Александр Заваленов](https://github.com/mainer93)
https://mainer93foodgram.ddns.net - Адрес сервера