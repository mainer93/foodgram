from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from .constants import SITE_ADDRESS
from .filters import RecipeFilter
from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, ShortLink, Tag)
from .permissions import IsOwnerOrReadOnly
from api.serializers import (IngredientSerializer, RecipeSerializer,
                             ShoppingCartRecipeSerializer, ShortLinkSerializer,
                             TagSerializer)
from recipes.pagination import UserListPagination


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer

    def get_queryset(self):
        name_starts_with = self.request.query_params.get('name', None)
        if name_starts_with:
            return Ingredient.objects.filter(
                name__istartswith=name_starts_with)
        return Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    serializer_class = RecipeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = UserListPagination
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response({'detail': 'Рецепт уже добавлен в избранное'},
                                status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            favorite = Favorite.objects.filter(user=user,
                                               recipe=recipe).first()
            if not favorite:
                return Response(
                    {'detail': 'Рецепт не был добавлен в избранное'},
                    status=status.HTTP_400_BAD_REQUEST)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response({'detail': 'Рецепт уже добавлен в корзину'},
                                status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShoppingCartRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            shopping_cart_item = ShoppingCart.objects.filter(
                user=user, recipe=recipe).first()
            if not shopping_cart_item:
                return Response({'detail': 'Рецепт не был добавлен в корзину'},
                                status=status.HTTP_400_BAD_REQUEST)
            shopping_cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        recipes_in_cart = ShoppingCart.objects.filter(
            user=request.user, is_in_shopping_cart=True).values_list(
                'recipe_id', flat=True)
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
        full_url = recipe.get_absolute_url()
        link_obj, created = ShortLink.objects.get_or_create(
            original_url=full_url)
        serializer = ShortLinkSerializer(link_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_favorited or instance.is_in_shopping_cart:
            return Response({'detail': 'Нельзя удалить рецепт, '
                             'который находится в избранном или корзине'},
                            status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


def redirect_to_full_link(request, short_id):
    short_link = f'{SITE_ADDRESS}/s/{short_id}'
    link_obj = get_object_or_404(ShortLink, short_link=short_link)
    full_link = link_obj.original_url
    return redirect(full_link)
