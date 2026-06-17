import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from foodgram.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV (оптимизированный)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-path', default='data', help='Путь к папке с CSV файлами'
        )
        parser.add_argument(
            '--verbose', action='store_true', help='Подробный вывод'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        data_path = options['data_path']
        verbose = options['verbose']
        filepath = os.path.join(data_path, 'ingredients.csv')

        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f'Файл {filepath} не найден'))
            return

        self.stdout.write('Чтение CSV...')
        ingredients_data = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    name = row[0].strip()
                    measurement_unit = row[1].strip()
                    if name and measurement_unit:
                        ingredients_data.append((name, measurement_unit))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка чтения файла: {e}'))
            return

        if not ingredients_data:
            self.stdout.write(self.style.WARNING('Нет данных для импорта'))
            return

        ingredients_to_create = [
            Ingredient(name=name, measurement_unit=unit)
            for name, unit in ingredients_data
        ]

        try:
            created_ingredients = Ingredient.objects.bulk_create(
                ingredients_to_create,
                ignore_conflicts=True
            )
            created_count = len(created_ingredients)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Импортировано ингредиентов: {created_count} '
                    f'(всего строк в CSV: {len(ingredients_data)})'
                )
            )
            if verbose:
                for ing in created_ingredients:
                    self.stdout.write(f'  Добавлен: {ing.name}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при bulk_create: {e}'))
            raise
