import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импортирует данные из CSV файла в модель Ingredient'

    def handle(self, *args, **kwargs):
        csv_file_path = os.path.join(settings.BASE_DIR, 'data',
                                     'ingredients.csv')
        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл не найден: {csv_file_path}'))
            return
        ingredients = []
        try:
            with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.reader(file)
                for row in reader:
                    try:
                        name, measurement_unit = row
                        name = name.strip()
                        measurement_unit = measurement_unit.strip()
                        ingredients.append(Ingredient(
                            name=name,
                            measurement_unit=measurement_unit
                        ))
                    except ValueError as e:
                        self.stdout.write(self.style.WARNING(
                            f'Ошибка при обработке строки {row}: {e}'))
                        continue
            Ingredient.objects.bulk_create(ingredients)
            self.stdout.write(self.style.SUCCESS(
                'Данные успешно импортированы'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f'Файл не найден: {csv_file_path}'))
        except csv.Error as e:
            self.stdout.write(self.style.ERROR(
                f'Ошибка при чтении CSV файла: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Произошла ошибка: {str(e)}'))
