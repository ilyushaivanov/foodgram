import csv
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from foodgram.models import Ingredient, Unit


class Command(BaseCommand):
    help = 'Импорт ингредиентов из CSV'

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

        self.stdout.write('Импорт ингредиентов...')
        try:
            count = 0
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    title = row[0].strip()
                    unit_name = row[1].strip()
                    if not title or not unit_name:
                        continue

                    unit, unit_created = Unit.objects.get_or_create(
                        title=unit_name,
                        defaults={'slug': unit_name.lower().replace(' ', '_')}
                    )
                    if unit_created and verbose:
                        self.stdout.write(
                            f'  Создана единица: {
                                unit_name
                            } (slug: {unit.slug})'
                        )

                    obj, created = Ingredient.objects.get_or_create(
                        title=title,
                        measurement_unit=unit
                    )
                    if created:
                        count += 1
                        if verbose:
                            self.stdout.write(
                                f'  Добавлен ингредиент: {title} ({unit_name})'
                            )
            self.stdout.write(
                self.style.SUCCESS(f'Импортировано ингредиентов: {count}')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка импорта: {e}'))
            raise
