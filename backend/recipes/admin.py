from django.contrib import admin

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, ShortLink, Subscription, Tag, User)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'username')
    search_fields = ('email', 'username')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('original_url', 'short_link')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author',
                    'favorited_count', 'in_shopping_cart_count',
                    'favorited_users', 'in_shopping_cart_users')
    list_filter = ('tags', 'author')
    search_fields = ('name', 'author__email')
    raw_id_fields = ('author',)
    autocomplete_fields = ('author',)

    def favorited_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()
    favorited_count.short_description = 'Избрано'

    def in_shopping_cart_count(self, obj):
        return ShoppingCart.objects.filter(recipe=obj).count()
    in_shopping_cart_count.short_description = 'В корзине'

    def favorited_users(self, obj):
        users = obj.favorited_by.all()
        return ', '.join([favorite.user.username for favorite in users])

    def in_shopping_cart_users(self, obj):
        users = obj.in_shoppingcart.all()
        return ', '.join([cart.user.username for cart in users])

    favorited_users.short_description = 'Добавили в избранное'
    in_shopping_cart_users.short_description = 'Добавили в корзину'
