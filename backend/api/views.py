import base64
import uuid

from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination

from foodgram.models import (Favorite, Follow, Ingredient, Recipe,
                             RecipeIngredient, ShoppingCart, ShortLink, Tag,
                             User)

from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, ChangePasswordSerializer,
                          IngredientSerializer,
                          RecipeCreateUpdateSerializer, RecipeSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserCreateSerializer, UserSerializer,
                          UserCreateResponseSerializer,
                          FavoriteAddResponseSerializer)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = [AllowAny]
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['list', 'retrieve']:
            return UserSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        elif self.action == 'avatar':
            return AvatarSerializer
        elif self.action == 'subscriptions':
            return SubscriptionSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        output_serializer = UserCreateResponseSerializer(user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=[
        'get'
    ], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=[
        'post'
    ], permission_classes=[IsAuthenticated], url_path='set_password')
    def set_password(self, request):
        serializer = self.get_serializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            methods=['put', 'delete'],
            permission_classes=[IsAuthenticated],
            url_path='me/avatar')
    def avatar(self, request):
        profile = request.user.profile
        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                return Response(
                    {'avatar': ['Обязательное поле.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                if ';base64,' in avatar_data:
                    format, imgstr = avatar_data.split(';base64,')
                    ext = format.split('/')[-1]
                    avatar_file = ContentFile(
                        base64.b64decode(imgstr),
                        name=f'avatar_{uuid.uuid4()}.{ext}'
                    )
                else:
                    return Response(
                        {'avatar': ['Неверный формат. Ожидается base64.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception:
                return Response(
                    {'avatar': ['Неверный формат base64.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if profile.avatar:
                profile.avatar.delete()
            profile.avatar = avatar_file
            profile.save()
            avatar_url = request.build_absolute_uri(profile.avatar.url)
            return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            if profile.avatar:
                profile.avatar.delete()
                profile.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=[
        'get'
    ], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        queryset = User.objects.filter(
            following__user=request.user
        ).order_by('id')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=[
        'post', 'delete'
    ], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk=None):
        author = self.get_object()
        user = request.user
        if request.method == 'POST':
            if user == author:
                return Response(
                    {
                        'error': 'Нельзя подписаться на себя'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            _, created = Follow.objects.get_or_create(user=user, author=author)
            if not created:
                return Response(
                    {
                        'error': 'Уже подписаны'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            serializer = SubscriptionSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted, _ = Follow.objects.filter(
                user=user, author=author
            ).delete()
            if not deleted:
                return Response(
                    {
                        'error': 'Не были подписаны'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TagViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['^title']


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=request.user)
        output_serializer = RecipeSerializer(
            recipe, context={'request': request}
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link, _ = ShortLink.objects.get_or_create(recipe=recipe)
        base_url = request.build_absolute_uri('/')[:-1]
        short_url = f"{base_url}/s/{short_link.code}"
        return Response({'short-link': short_url})

    @action(detail=True, methods=[
        'post', 'delete'
    ], permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            _, created = Favorite.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response(
                    {
                        'error': 'Уже в избранном'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FavoriteAddResponseSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted, _ = Favorite.objects.filter(
                user=user, recipe=recipe
            ).delete()
            if not deleted:
                return Response(
                    {
                        'error': 'Не в избранном'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=[
        'post', 'delete'
    ], permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            _, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response(
                    {
                        'error': 'Уже в корзине'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FavoriteAddResponseSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            deleted, _ = ShoppingCart.objects.filter(
                user=user, recipe=recipe
            ).delete()
            if not deleted:
                return Response(
                    {
                        'error': 'Не в корзине'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=[
        'get'
    ], permission_classes=[IsAuthenticated], url_path='download_shopping_cart')
    def download_shopping_cart(self, request):
        user = request.user
        cart_recipes = ShoppingCart.objects.filter(
            user=user
        ).values_list('recipe', flat=True)
        ingredients = RecipeIngredient.objects.filter(
            recipe_id__in=cart_recipes
        ).values(
            'ingredient__title',
            'ingredient__measurement_unit__title'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__title')

        content = "Список покупок:\n\n"
        for item in ingredients:
            content += (
                f"{item['ingredient__title']} – {item['total_amount']} "
                f"{item['ingredient__measurement_unit__title']}\n"
            )

        response = HttpResponse(content, content_type='text/plain')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'
        return response

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        output_serializer = RecipeSerializer(
            instance, context={'request': request}
        )
        return Response(output_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
