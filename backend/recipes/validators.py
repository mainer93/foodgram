from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

unicode_validator = UnicodeUsernameValidator()


def validate_username(value):
    if value == 'me':
        raise ValidationError(
            'Значение поля "username" не должно быть указано как "me"')
