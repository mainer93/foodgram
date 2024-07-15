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
            self.stdout.write(self.style.ERROR(
                'Файл не найден: ' + csv_file_path))
            return

        with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            for row in reader:
                name, measurement_unit = row
                name = name.strip()
                measurement_unit = measurement_unit.strip()
                Ingredient.objects.create(
                    name=name,
                    measurement_unit=measurement_unit
                )
        self.stdout.write(self.style.SUCCESS('Данные успешно импортированы'))
