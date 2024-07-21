from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
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
from .serializers import (IngredientSerializer, RecipeSerializer,
                          ShoppingCartRecipeSerializer, ShortLinkSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserSerializer)

User = get_user_model()


class UserViewSet(UserViewSet):
    pagination_class = UserListPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['registry'] = (self.action == 'create')
        return context

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = request.user.follower.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubscriptionSerializer(page, many=True,
                                                context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(queryset, many=True,
                                            context={'request': request})
        return Response(serializer.data)

    @action(methods=['post', 'delete'], detail=True,
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, pk=id)
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request})
            if serializer.is_valid():
                serializer.save(user=request.user, author=author)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
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
            serializer = UserSerializer(instance=user,
                                        data={'avatar': avatar_data},
                                        partial=True,
                                        context={'request': request,
                                                 'avatar_set': True})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response({'message': 'Аватар удален'},
                            status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (IngredientFilter,)
    search_fields = ['^name']


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
                if action_model == Favorite:
                    self.get_serializer().validate_favorite(recipe, user)
                    Favorite.objects.create(user=user, recipe=recipe)
                elif action_model == ShoppingCart:
                    self.get_serializer().validate_shopping_cart(recipe, user)
                    ShoppingCart.objects.create(user=user, recipe=recipe)
            except ValidationError as e:
                return Response({'detail': str(e)},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = ShoppingCartRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if action_model == Favorite:
                instance = recipe.favorited_by.filter(user=user).first()
            elif action_model == ShoppingCart:
                instance = recipe.in_shoppingcart.filter(user=user).first()
            if not instance:
                detail_msg = (
                    'Рецепт не был добавлен в избранное'
                    if action_model == Favorite
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
