from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.constants import (AMOUNT_INGREDIENT, COOKING_TIME,
                               MAX_LENGTH_USERNAME)
from recipes.models import (Ingredient, IngredientInRecipe, Recipe, ShortLink,
                            Subscription, Tag, User)
from recipes.validators import unicode_validator


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False)
    email = serializers.EmailField()
    username = serializers.CharField(
        max_length=MAX_LENGTH_USERNAME,
        validators=[unicode_validator]
    )

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if not user.is_authenticated:
            return False
        return obj.following.filter(user=user, author=obj).exists()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = ('avatar',)


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.ImageField(source='author.avatar', read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'avatar', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context['request']
        return request.user.following.filter(author=obj.author).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.author.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            try:
                limit = int(recipes_limit)
                recipes = recipes[:limit]
            except ValueError:
                recipes = recipes.none()
        return RecipeListSerializer(recipes, many=True,
                                    context={'request': request}).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def validate(self, data):
        request = self.context['request']
        user = request.user
        author = User.objects.get(pk=self.initial_data.get('author'))
        if user == author:
            raise serializers.ValidationError(
                {'detail': 'Невозможно подписаться на самого себя'})
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                {'detail': 'Вы уже подписаны на этого пользователя'})
        data['author'] = author
        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientInRecipe
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(read_only=True, many=True)
    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return request.user.is_authenticated and obj.favorited_by.filter(
            user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return request.user.is_authenticated and obj.in_shoppingcart.filter(
            user=request.user).exists()

    def validate_favorite(self, obj, user):
        if obj.favorited_by.filter(user=user).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное')

    def validate_shopping_cart(self, obj, user):
        if obj.in_shoppingcart.filter(user=user).exists():
            raise serializers.ValidationError('Рецепт уже добавлен в корзину')

    def validate(self, data):
        cooking_time = data.get('cooking_time')
        if cooking_time is None or cooking_time < COOKING_TIME:
            raise serializers.ValidationError({
                'cooking_time': 'Время приготовления должно быть больше 0'
            })
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один ингредиент')
        ingredient_ids = []
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            try:
                amount = int(amount)
            except ValueError:
                raise serializers.ValidationError(f'Количество ингредиента '
                                                  f'должно быть числом: '
                                                  f'id={ingredient_id}')
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(f'Ингредиент с '
                                                  f'id={ingredient_id} '
                                                  f'уже добавлен')
            ingredient_ids.append(ingredient_id)
            ingredient_instance = Ingredient.objects.filter(
                id=ingredient_id).first()
            if not ingredient_instance:
                raise serializers.ValidationError(
                    f'Такого ингредиента с id={ingredient_id} не существует')
            if amount < AMOUNT_INGREDIENT:
                raise serializers.ValidationError(
                    f'Количество ингредиента должно быть больше 0: '
                    f'id={ingredient_id}')
        data['ingredients'] = ingredients
        tags = self.initial_data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один тег')
        tag_ids = set()
        for tag_id in tags:
            if tag_id in tag_ids:
                raise serializers.ValidationError(
                    'Повторяющиеся теги недопустимы')
            tag_ids.add(tag_id)
            tag_instance = Tag.objects.filter(id=tag_id).first()
            if not tag_instance:
                raise serializers.ValidationError(
                    f'Такого тега с id={tag_id} не существует')
        data['tags'] = tags
        return data

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        image_data = validated_data.pop('image', None)
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author,
                                       image=image_data, **validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        image_data = validated_data.get('image')
        if image_data:
            instance.image = image_data
        tags_data = validated_data.get('tags')
        if tags_data:
            instance.tags.clear()
            instance.tags.set(tags_data)
        ingredients_data = self.initial_data.get('ingredients')
        if ingredients_data:
            instance.ingredients.all().delete()
            for ingredient_data in ingredients_data:
                IngredientInRecipe.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data['id'],
                    amount=ingredient_data['amount']
                )
        instance.save()
        return instance


class ShoppingCartRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShortLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortLink
        fields = ('short_link',)

    def to_representation(self, instance):
        request = self.context.get('request')
        short_link = instance.short_link
        full_short_link = request.build_absolute_uri(short_link)
        return {'short-link': full_short_link}
