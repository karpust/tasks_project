# Task Management API

[![basic CI](https://github.com/karpust/tasks_project/actions/workflows/ci.yml/badge.svg)](https://github.com/karpust/tasks_project/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/karpust/tasks_project/branch/improvements/graph/badge.svg?token=CHI6PFCJTO)](https://codecov.io/github/karpust/tasks_project)


API управления задачами с поддержкой ролей, подтверждением email, уведомлениями и асинхронными задачами.

## Запуск проекта:
### 1. Клонировать репозиторий:
```shell
git clone https://github.com/karpust/tasks_project.git
```
### 2. Создать .env по образцу .env.examlpe в корне проекта или использовать .env.examlpe с изменениями:
```shell
mv .env.example .env
```
### 3. Выполнить команду запуска проекта в корневой директории:
```shell
make up
```

## Функциональность

### Аутентификация и авторизация

- Регистрация пользователя
- Подтверждение email по ссылке из письма
- Повторное подтверждение email при неудаче
- Вход с JWT (httpOnly cookies)
- Обновление токена
- Смена пароля
- Выход

### Работа с задачами

- Создание задач с возможностью одновременного создания категории и тэгов
- Ролевой доступ:
  - **Юзер**
  - **Менеджер**
  - **Админ**
- Разграничение прав на:
  - Задачи
  - Комментарии
- Поддержка фильтрации и пагинации

### Асинхронные задачи (Celery + Redis + Flower)

- Отправка email при регистрации, повторном подтверждении, смене пароля.
- Удаление неподтверждённых пользователей по расписанию.
- Уведомление о приближающемся дедлайне для автора и исполнителей задачи.

### Тестирование

- Django Unit Test
- Проверка покрытия с помощью `coverage`


## Документация API

- OpenAPI schema (YAML): `/schema/`
- Swagger UI: `/swagger/`
- Redoc: `/redoc/`

##  Используемые технологии

- Python / Django / DRF
- PostgreSQL
- Redis
- Celery
- Flower
- drf-spectacular
- Docker
- Unittests (Django Unit Test)
- pre-commit хуки
- CI (github actions)
- Swagger / Redoc
- Faker, Factory Boy
