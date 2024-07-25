import shortuuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from .constants import (MAX_LENGTH_EMAIL, MAX_LENGTH_FIRSTNAME,
                        MAX_LENGTH_LASTNAME, MAX_LENGTH_NAME_RECIPE,
                        MAX_LENGTH_NAME_TAG, MAX_LENGTH_SLUG,
                        MAX_LENGTH_UNIT, MAX_LENGTH_USERNAME,
                        MIN_VALUE_ING, MIN_VALUE_TIME, ORIGINAL_URL,
                        SHORT_URL, SHORT_URL_LIMIT)
from .validators import name_validator, unicode_validator


class User(AbstractUser):
    email = models.EmailField(max_length=MAX_LENGTH_EMAIL, unique=True)
    first_name = models.CharField(max_length=MAX_LENGTH_FIRSTNAME,
                                  validators=[name_validator])
    last_name = models.CharField(max_length=MAX_LENGTH_LASTNAME,
                                 validators=[name_validator])
    username = models.CharField(max_length=MAX_LENGTH_USERNAME, unique=True,
                                validators=[unicode_validator])
    avatar = models.ImageField(upload_to='users/', null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    def __str__(self):
        return self.email


class Subscription(models.Model):
    user = models.ForeignKey(User, related_name='follower',
                             on_delete=models.CASCADE)
    author = models.ForeignKey(User, related_name='following',
                               on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='not_self_follow'
            )
        ]


class BaseModel(models.Model):
    name = models.CharField(max_length=MAX_LENGTH_NAME_TAG, unique=True,
                            validators=[name_validator])

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Ingredient(BaseModel):
    measurement_unit = models.CharField(max_length=MAX_LENGTH_UNIT)

    class Meta:
        default_related_name = 'ingredients'


class Tag(BaseModel):
    slug = models.SlugField(max_length=MAX_LENGTH_SLUG, unique=True)

    class Meta:
        default_related_name = 'tags'


class Recipe(models.Model):
    tags = models.ManyToManyField(Tag, related_name='recipes')
    image = models.ImageField(upload_to='recipes/images/')
    name = models.CharField(max_length=MAX_LENGTH_NAME_RECIPE,
                            validators=[name_validator])
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='recipes')
    cooking_time = models.PositiveSmallIntegerField(
        validators=(
            MinValueValidator(
                MIN_VALUE_TIME,
                message='Время приготовления должно быть больше 0'),
        )
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               related_name='ingredientinrecipe')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField(
        validators=(
            MinValueValidator(
                MIN_VALUE_ING,
                message='Количество ингредиентов должно быть больше 0'),
        )
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'], name='ingredient_unique'
            ),
        ]


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Favorite(UserRecipeRelation):
    class Meta:
        default_related_name = 'favorited_by'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='favorite_unique'
            ),
        )


class ShoppingCart(UserRecipeRelation):

    class Meta:
        default_related_name = 'in_shoppingcart'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='cart_unique'
            ),
        )


class ShortLink(models.Model):
    original_url = models.URLField(max_length=ORIGINAL_URL)
    short_link = models.CharField(max_length=SHORT_URL, unique=True)

    def save(self, *args, **kwargs):
        if not self.short_link:
            link = f'/s/{shortuuid.uuid()[:SHORT_URL_LIMIT]}'
            self.short_link = link
        super().save(*args, **kwargs)

    def __str__(self):
        return self.short_link
