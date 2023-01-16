rm db.sqlite3
rm -rf accounts/migrations/*
rm -rf mercari/migrations/*
rm -rf settings_amazon/migrations/*
rm -rf yahoo/migrations/*

python manage.py makemigrations yahoo
python manage.py makemigrations mercari
python manage.py makemigrations accounts
python manage.py makemigrations settings_amazon
python manage.py migrate
python manage.py createsuperuser --email admin@example.com --username admin
