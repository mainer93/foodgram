from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import RegexValidator

unicode_validator = UnicodeUsernameValidator()

name_validator = RegexValidator(
    regex=r'^[a-zA-Zа-яА-Я]*$',
    message='Допустимы только буквы без пробелов'
)
