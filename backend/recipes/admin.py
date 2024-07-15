from django.contrib import admin

from .models import (User, Subscription, Tag, Ingredient,
                     Recipe, IngredientInRecipe, Favorite,
                     ShoppingCart, ShortLink)


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


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    list_filter = ('tags', 'author')
    search_fields = ('name', 'author__username')

    def is_favorited(self, obj):
        return obj.favorited_by.count()

    def is_in_shopping_cart(self, obj):
        return obj.in_shoppingcart.count()

    is_favorited.short_description = 'Избрано'
    is_in_shopping_cart.short_description = 'В корзине'


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'is_in_shopping_cart')


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('original_url', 'short_link')
