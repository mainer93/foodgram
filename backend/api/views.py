from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, ShortLink, Subscription, Tag)
from .filters import IngredientFilter, RecipeFilter
from .pagination import UserListPagination
from .permissions import IsOwnerOrReadOnly
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeSerializer, ShoppingCartRecipeSerializer,
                          ShortLinkSerializer, SubscriptionSerializer,
                          TagSerializer, UserSerializer)

User = get_user_model()


class UserViewSet(viewsets.GenericViewSet):
    pagination_class = UserListPagination

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = request.user.follower.all()
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = SubscriptionSerializer(page, many=True,
                                                context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(queryset, many=True,
                                            context={'request': request})
        return Response(serializer.data)

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscriptions = Subscription.objects.filter(
                user=request.user, author=author)
            if not subscriptions.exists():
                return Response({'error': 'Подписка не существует'},
                                status=status.HTTP_400_BAD_REQUEST)
            subscriptions.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['put', 'patch', 'delete'], detail=False,
            url_path='me/avatar', permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method in ['PUT', 'PATCH']:
            avatar_data = request.data.get('avatar')
            if avatar_data is None:
                return Response(
                    {'error': 'Данные аватара не были предоставлены'},
                    status=status.HTTP_400_BAD_REQUEST)
            serializer = UserSerializer(
                instance=user, data={'avatar': avatar_data},
                partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            avatar_serializer = AvatarSerializer(instance=user)
            return Response(avatar_serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response({'message': 'Аватар удален'},
                            status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, url_path='me',
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientFilter,)
    search_fields = ['^name']
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = UserListPagination
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def handle_action(self, request, recipe, user, action_model):
        if request.method == 'POST':
            try:
                serializer = self.get_serializer()
                if action_model == Favorite:
                    serializer.validate_favorite(recipe, user)
                elif action_model == ShoppingCart:
                    serializer.validate_shopping_cart(recipe, user)
                action_model.objects.create(user=user, recipe=recipe)
                response_serializer = ShoppingCartRecipeSerializer(
                    recipe, context={'request': request})
                return Response(response_serializer.data,
                                status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({'detail': str(e)},
                                status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            instance = action_model.objects.filter(
                user=user, recipe=recipe).first()
            if not instance:
                detail_msg = (
                    'Рецепт не был добавлен '
                    'в избранное' if action_model == Favorite
                    else 'Рецепт не был добавлен в корзину'
                )
                return Response({'detail': detail_msg},
                                status=status.HTTP_400_BAD_REQUEST)
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        return self.handle_action(request, recipe, user, Favorite)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        return self.handle_action(request, recipe, user, ShoppingCart)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        recipes_in_cart = ShoppingCart.objects.filter(
            user=user
        ).values_list('recipe_id', flat=True)
        shopping_list = IngredientInRecipe.objects.filter(
            recipe__id__in=recipes_in_cart
        ).values(
            name=F('ingredient__name'),
            unit=F('ingredient__measurement_unit')
        ).annotate(amount=Sum('amount'))
        shopping_cart_text = 'Список покупок:\n'
        for ingredient in shopping_list:
            shopping_cart_text += (
                f'{ingredient["name"]} - '
                f'{ingredient["amount"]} '
                f'{ingredient["unit"]}\n'
            )
        response = HttpResponse(shopping_cart_text, content_type='text/plain')
        filename = 'shopping_cart.txt'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        full_url = f'/recipes/{recipe.pk}/'
        link_obj, created = ShortLink.objects.get_or_create(
            original_url=full_url)
        serializer = ShortLinkSerializer(link_obj,
                                         context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Favorite.objects.filter(recipe=instance).exists():
            return Response({'detail': 'Нельзя удалить рецепт, '
                             'который находится в избранном у кого-то'},
                            status=status.HTTP_400_BAD_REQUEST)
        if ShoppingCart.objects.filter(recipe=instance).exists():
            return Response({'detail': 'Нельзя удалить рецепт, '
                             'который находится в корзине покупок у кого-то'},
                            status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


def redirect_to_full_link(request, short_id):
    short_link = f'/s/{short_id}'
    link_obj = get_object_or_404(ShortLink, short_link=short_link)
    full_link = link_obj.original_url
    return redirect(full_link)
