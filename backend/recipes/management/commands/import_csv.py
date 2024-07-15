import csv

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импортирует данные из CSV файла в модель Ingredient'

    def handle(self, *args, **kwargs):
        csv_file = 'data/ingredients.csv'
        with open(csv_file, 'r', encoding='utf-8-sig') as file:
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
