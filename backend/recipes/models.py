import shortuuid
from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import (MAX_LENGTH_EMAIL, MAX_LENGTH_FIRSTNAME,
                        MAX_LENGTH_LASTNAME, MAX_LENGTH_NAME_ING,
                        MAX_LENGTH_NAME_RECIPE, MAX_LENGTH_NAME_TAG,
                        MAX_LENGTH_PASSWORD, MAX_LENGTH_SLUG, MAX_LENGTH_UNIT,
                        MAX_LENGTH_USERNAME, ORIGINAL_URL, SHORT_URL,
                        SHORT_URL_LIMIT, SITE_ADDRESS)
from .validators import unicode_validator, validate_username


class User(AbstractUser):
    email = models.EmailField(max_length=MAX_LENGTH_EMAIL, unique=True)
    first_name = models.CharField(max_length=MAX_LENGTH_FIRSTNAME)
    last_name = models.CharField(max_length=MAX_LENGTH_LASTNAME)
    username = models.CharField(max_length=MAX_LENGTH_USERNAME, unique=True,
                                validators=[validate_username,
                                            unicode_validator])
    password = models.CharField(max_length=MAX_LENGTH_PASSWORD)
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
        unique_together = ['user', 'author']


class Tag(models.Model):
    name = models.CharField(max_length=MAX_LENGTH_NAME_TAG, unique=True)
    slug = models.SlugField(max_length=MAX_LENGTH_SLUG, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=MAX_LENGTH_NAME_ING)
    measurement_unit = models.CharField(max_length=MAX_LENGTH_UNIT)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    ingredients = models.ManyToManyField(Ingredient,
                                         through='IngredientInRecipe')
    tags = models.ManyToManyField(Tag, related_name='recipes')
    image = models.ImageField(upload_to='recipes/images/')
    name = models.CharField(max_length=MAX_LENGTH_NAME_RECIPE)
    text = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    cooking_time = models.IntegerField()
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'{SITE_ADDRESS}/recipes/{self.pk}/'


class IngredientInRecipe(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.IntegerField()


class Favorite(models.Model):
    user = models.ForeignKey(User, related_name='favorites',
                             on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, related_name='favorited_by',
                               on_delete=models.CASCADE)

    class Meta:
        unique_together = ['user', 'recipe']


class ShoppingCart(models.Model):
    user = models.ForeignKey(User, related_name='shoppingcart',
                             on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, related_name='in_shoppingcart',
                               on_delete=models.CASCADE)
    is_in_shopping_cart = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'recipe']


class ShortLink(models.Model):
    original_url = models.URLField(max_length=ORIGINAL_URL)
    short_link = models.CharField(max_length=SHORT_URL, unique=True)

    def save(self, *args, **kwargs):
        if not self.short_link:
            link = f'{SITE_ADDRESS}/s/{shortuuid.uuid()[:SHORT_URL_LIMIT]}'
            self.short_link = link
        super().save(*args, **kwargs)

    def __str__(self):
        return self.short_link
