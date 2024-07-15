import base64
import uuid

from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers

from recipes.constants import (AMOUNT_INGREDIENT, COOKING_TIME,
                               FORMAT_SPLIT, SITE_ADDRESS)
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, ShortLink, Subscription, Tag, User)


class Base64ImageField(serializers.ImageField):
    def __init__(self, *args, **kwargs):
        self.site_address = kwargs.pop('site_address', SITE_ADDRESS)
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if value:
            return f"{self.site_address}{value.url}"
        return None

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[FORMAT_SPLIT]
            id = uuid.uuid4()
            data = ContentFile(base64.b64decode(imgstr), name=f'{id}.{ext}')
        return super().to_internal_value(data)


class UserCreateSerializer(BaseUserCreateSerializer):

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'password')


class UserSerializer(BaseUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False)

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
        return False


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar')


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


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
        return Subscription.objects.filter(user=self.context['request'].user,
                                           author=obj.author).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = Recipe.objects.filter(author=obj.author)
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        return RecipeListSerializer(recipes, many=True,
                                    context={'request': request}).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


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
    image = Base64ImageField(site_address=SITE_ADDRESS)
    author = serializers.SerializerMethodField()
    ingredients = RecipeIngredientSerializer(source='ingredientinrecipe_set',
                                             many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return request.user.is_authenticated and Favorite.objects.filter(
            user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return request.user.is_authenticated and ShoppingCart.objects.filter(
            user=request.user, recipe=obj).exists()

    def validate(self, data):
        cooking_time = data.get('cooking_time')
        if cooking_time is None or cooking_time < COOKING_TIME:
            raise serializers.ValidationError({
                'cooking_time': 'Время приготовления должно быть больше 0'
            })
        ingredients = self.initial_data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError('Необходимо добавить '
                                              'хотя бы один ингредиент')
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
                raise serializers.ValidationError(f'Такого ингредиента не '
                                                  f'существует: '
                                                  f'id={ingredient_id}')
            if amount < AMOUNT_INGREDIENT:
                raise serializers.ValidationError(f'Количество ингредиента '
                                                  f'должно быть больше 0: '
                                                  f'id={ingredient_id}')
        data['ingredients'] = ingredients
        tags = self.initial_data.get('tags')
        if not tags:
            raise serializers.ValidationError('Необходимо добавить '
                                              'хотя бы один тег')
        tag_ids = set()
        for tag_id in tags:
            if tag_id in tag_ids:
                raise serializers.ValidationError('Повторяющиеся '
                                                  'теги недопустимы')
            tag_ids.add(tag_id)
            tag_instance = Tag.objects.filter(id=tag_id).first()
            if not tag_instance:
                raise serializers.ValidationError(f'Такого тега не '
                                                  f'существует: id={tag_id}')
        data['tags'] = tags
        return data

    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        image_data = validated_data.pop('image', None)
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author, image=image_data,
                                       **validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            IngredientInRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        return recipe

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_author(self, obj):
        user = obj.author
        request = self.context.get('request')
        is_subscribed = False
        if request and request.user.is_authenticated:
            is_subscribed = Subscription.objects.filter(user=request.user,
                                                        author=user).exists()
        return {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_subscribed": is_subscribed,
            "avatar": request.build_absolute_uri(
                user.avatar.url) if user.avatar else None
        }

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
            instance.ingredientinrecipe_set.all().delete()
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
        return {'short-link': instance.short_link}
