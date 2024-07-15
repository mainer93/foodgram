from django.contrib.auth import get_user_model, update_session_auth_hash
from recipes.models import Subscription
from recipes.pagination import UserListPagination
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (SetPasswordSerializer, SubscriptionSerializer,
                          UserAvatarSerializer, UserCreateSerializer,
                          UserSerializer)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserListPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['set_avatar', 'delete_avatar']:
            return UserAvatarSerializer
        elif self.action == 'set_password':
            return SetPasswordSerializer
        elif self.action in ['subscriptions', 'subscribe', 'unsubscribe']:
            return SubscriptionSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve',
                           'subscriptions', 'subscribe', 'unsubscribe']:
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        if self.action in ['me', 'set_avatar', 'delete_avatar',
                           'set_password']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @action(detail=False, methods=['get', 'put', 'delete'],
            permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'PUT':
            avatar = request.data.get('avatar')
            if not avatar:
                return Response({'avatar': ['Это поле обязательное']},
                                status=status.HTTP_400_BAD_REQUEST)
            user = request.user
            serializer = self.get_serializer(user, data=request.data,
                                             partial=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                updated_user = User.objects.get(id=user.id)
                return Response({'avatar': updated_user.avatar.url},
                                status=status.HTTP_200_OK)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            user = request.user
            user.avatar.delete()
            user.save()
            return Response({'avatar': None},
                            status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'],
            permission_classes=[IsAuthenticated])
    def set_password(self, request):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current_password = serializer.validated_data['current_password']
        if not user.check_password(current_password):
            errors = {'current_password': ['Текущий пароль введен неверно']}
            raise ValidationError(errors)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = Subscription.objects.filter(user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubscriptionSerializer(page, many=True,
                                                context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(queryset, many=True,
                                            context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if not request.user.is_authenticated:
            return Response({'detail': 'Для выполнения этого действия '
                             'требуется аутентификация'},
                            status=status.HTTP_401_UNAUTHORIZED)
        if request.method == 'POST':
            if request.user == author:
                return Response({'detail': 'Невозможно '
                                 'подписаться на себя'},
                                status=status.HTTP_400_BAD_REQUEST)
            if Subscription.objects.filter(user=request.user,
                                           author=author).exists():
                return Response({'detail': 'Вы уже подписаны '
                                 'на этого пользователя'},
                                status=status.HTTP_400_BAD_REQUEST)
            subscription = Subscription(user=request.user, author=author)
            subscription.save()
            serializer = SubscriptionSerializer(subscription,
                                                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=request.user,
                                                       author=author).first()
            if not subscription:
                return Response({'detail': 'Подписка не существует'},
                                status=status.HTTP_400_BAD_REQUEST)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if pk == 'me':
            if request.user.is_authenticated:
                instance = request.user
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
            else:
                return Response(
                    {'detail':
                        'Для выполнения этого действия '
                        'требуется аутентификация'},
                    status=status.HTTP_401_UNAUTHORIZED)
        else:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
