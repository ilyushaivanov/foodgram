Находясь в папке infra, выполните команду docker-compose up. При выполнении этой команды контейнер frontend, описанный в docker-compose.yml, подготовит файлы, необходимые для работы фронтенд-приложения, а затем прекратит свою работу.

По адресу http://localhost изучите фронтенд веб-приложения, а по адресу http://localhost/api/docs/ — спецификацию API.


# Foodgram — продуктовый помощник

**Foodgram** — это веб-приложение, где пользователи могут публиковать рецепты, добавлять их в избранное и список покупок, а также скачивать список покупок в текстовом формате. Проект реализован на Django + DRF, фронтенд на React, развернут с использованием Docker и GitHub Actions.

## 🚀 Деплой проекта

Проект развернут по адресу:  
[https://foodgram0891.duckdns.org/]

---

## 📖 Инструкция по развертыванию в Docker

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/ваш_username/foodgram.git
cd foodgram

2. Настройка секретов GitHub
В репозитории перейдите в Settings → Secrets and variables → Actions и добавьте следующие секреты:


DOCKER_USERNAME: Ваш логин на Docker Hub
DOCKER_PASSWORD: Пароль или токен доступа к Docker Hub
HOST: Публичный IP-адрес вашего сервера
USER: Имя пользователя для SSH
SSH_KEY: SSH-ключ


3. Подготовка сервера
На сервере выполните:

Установите Docker и Docker Compose:

sudo apt update
sudo apt install docker
sudo apt install docker-compose

Создайте папку переменных окружения:

Создайте файл .env в папке ~/foodgram/infra/:

cd ~/foodgram/infra
nano .env
Пример содержимого:

SECRET_KEY=ваш_секретный_ключ
DEBUG=False
ALLOWED_HOSTS=ваш_домен_or_ip
CSRF_TRUSTED_ORIGINS=http://ваш_домен_or_ip,https://ваш_домен_or_ip
DB_ENGINE=django.db.backends.postgresql
DB_NAME=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=ваш_пароль_бд
DB_HOST=db
DB_PORT=5432


4. Запуск деплоя
Внесите изменения в код и сделайте push в ветку main:

git add .
git commit -m "Deploy"
git push
GitHub Actions автоматически соберёт образы, загрузит их на Docker Hub и выполнит деплой на сервер.

5. Проверка
После завершения workflow сайт будет доступен по вашему домену или IP-адресу.
Админка: https://ваш_домен/admin/

Стек технологий
Бэкенд:

Python 3.12

Django 5.2

Django REST Framework 3.15

Djoser (аутентификация)

SimpleJWT (токены)

PostgreSQL 14

Gunicorn

Pillow (обработка изображений)

Фронтенд:

React

Инфраструктура:

Docker & Docker Compose

Nginx (веб-сервер)

GitHub Actions (CI/CD)

Let's Encrypt (SSL-сертификаты)


Как наполнить БД данными

Через админку:

Зайдите в админку: https://ваш_домен/admin/

Добавьте теги, ингредиенты и рецепты вручную.

Через фикстуры:

python manage.py import_csv --data-path data --verbose


Документация API

Документация доступна по адресу:

/api/docs/


Примеры запросов и ответов:

Регистрация пользователя
Запрос:

POST /api/users/
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "user1",
  "first_name": "Иван",
  "last_name": "Иванов",
  "password": "Qwerty123"
}
Ответ (201 Created):

{
  "id": 1,
  "email": "user@example.com",
  "username": "user1",
  "first_name": "Иван",
  "last_name": "Иванов"
}
Создание рецепта
Запрос (с токеном):

POST /api/recipes/
Authorization: Token your_token_here
Content-Type: application/json

{
  "name": "Омлет",
  "text": "Взбить яйца, обжарить на сковороде.",
  "image": "data:image/png;base64,...",
  "cooking_time": 5,
  "tags": [1, 2],
  "ingredients": [
    {"id": 10, "amount": 2},
    {"id": 15, "amount": 100}
  ]
}
Ответ (201 Created):


{
  "id": 42,
  "name": "Омлет",
  "image": "http://foodgram0891.duckdns.org/media/recipes/omlet.png",
  "cooking_time": 5,
  "author": { ... },
  "tags": [...],
  "ingredients": [
    {
      "id": 10,
      "name": "Яйцо",
      "measurement_unit": "шт.",
      "amount": 2
    },
    {
      "id": 15,
      "name": "Молоко",
      "measurement_unit": "мл",
      "amount": 100
    }
  ]
}


Скачать список покупок

GET /api/recipes/download_shopping_cart/
Authorization: Token your_token_here
Ответ: текстовый файл:

Список покупок:

Яйцо – 2 шт.
Молоко – 100 мл.


Авторство
Разработчик: Иванов Илья
GitHub: ilyushaivanov
Проект выполнен в рамках финального этапа курса «Python-разработчик» в Яндекс.Практикуме.
Дата: июнь 2026 г.