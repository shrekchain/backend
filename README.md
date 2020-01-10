### Build and run

`docker-compose up`

### Rebuild

`docker-compose build`

### Clear db

`docker-compose down && rm -rf <PROJECT_ROOT>/shared/postgresql/pgdata/*`

### Run tests

`docker-compose run --rm app python manage.py test --settings config.settings.test`
