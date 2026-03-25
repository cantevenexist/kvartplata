#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Применение миграций
python manage.py makemigrations
python manage.py migrate

# Миграции для APScheduler
python manage.py migrate django_apscheduler

# Очищение таблиц базы данных Postgre
# python manage.py flush --no-input

# Создание аккаунта суперпользователя
sh init_superadmin.sh

# Запуск планировщика в фоновом режиме
python /usr/src/app/scheduler_runner.py &

# Запуск основного приложения
exec "$@"