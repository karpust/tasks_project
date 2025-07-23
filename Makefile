.PHONY: test cov cov-html lint format check-comments fix-comments clean check
# не файлы, а команды к выполнению

# Что проверять
SRC = .github authapp integration_tests tasks scripts tasks_project

test:  ## Запуск django тестов
	python manage.py test

cov:  ## Запуск тестов с замером покрытия
	coverage run manage.py test
	coverage report --fail-under=80
	coverage xml  # for codecov

cov-html:  ## Генерация HTML-отчёта покрытия и автоматическое открытие в браузере
	coverage html & disown && start htmlcov/index.html

lint:  ## Проверка стиля кода с ruff
	ruff check $(SRC)

format:  ## Форматирование кода с black (отступы, кавычки, переносы строк)
	black $(SRC)
	ruff check --fix $(SRC)

check-comments:  ## Проверка docstring и комментариев
	docformatter --check --wrap-summaries 88 --wrap-descriptions 88 --recursive $(SRC)  # suitable for black

fix-comments:  ## Форматирование docstring и комментариев
	@echo "Fixing comments and docstrings with docformatter..."
	docformatter --in-place --wrap-summaries 88 --wrap-descriptions 88 --recursive $(SRC)

clean:  ## Очистка отчёта покрытия
	@echo "Cleaning coverage and temp files..."
	@python -c "import shutil; shutil.rmtree('htmlcov', ignore_errors=True)"
	@python -c "import os; import os; os.path.exists('.coverage') and os.remove('.coverage')"

check: lint check-comments  ## Проверка линтерами ruff and docformatter

format-all: format fix-comments  ## Форматирование black и docformatter

up:
	docker compose -f docker-compose.yml up -d --build
down:
	docker compose -f docker-compose.yml down -v

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'



# Очистка отчёта покрытия и временных файлов
# clean:
# 	-@rm -rf htmlcov .coverage __pycache__ .pytest_cache
# # -@ предотвращает вывод ошибок при отсутствии файлов
