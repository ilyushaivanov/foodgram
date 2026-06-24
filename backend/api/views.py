from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from foodgram.models import (Favorite, Follow, Ingredient, Recipe,
                             RecipeIngredient, ShoppingCart, Tag, User)
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, FavoriteCreateSerializer,
                          FollowCreateSerializer, IngredientSerializer,
                          RecipeCreateUpdateSerializer, RecipeSerializer,
                          ShoppingCartCreateSerializer, SubscriptionSerializer,
                          TagSerializer, UserSerializer)


class UserViewSet(DjoserUserViewSet):
    permission_classes = [AllowAny]
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        if self.action == 'avatar':
            return AvatarSerializer
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        if self.action in ['list', 'retrieve']:
            return UserSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=[
        'get'
    ], permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=False, methods=[
        'put'
    ], permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        avatar_url = request.build_absolute_uri(user.avatar.url)
        return Response({'avatar': avatar_url}, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete()
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=[
        'get'
    ], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        queryset = User.objects.filter(
            following__user=request.user
        ).order_by('id')
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=[
        'post'
    ], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk=None, *args, **kwargs):
        author = self.get_object()
        serializer = FollowCreateSerializer(
            data={'author': author.id, 'user': request.user.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None, *args, **kwargs):
        author = self.get_object()
        deleted, _ = Follow.objects.filter(
            user=request.user, author=author
        ).delete()
        if not deleted:
            return Response(
                {'error': 'Не были подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name']


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('-id')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        base_url = request.build_absolute_uri('/')[:-1]
        short_url = f"{base_url}/s/{recipe.short_code}"
        return Response({'short-link': short_url})

    @action(detail=True, methods=[
        'post'
    ], permission_classes=[IsAuthenticated], url_path='favorite')
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        serializer = FavoriteCreateSerializer(
            data={'recipe': recipe.id, 'user': request.user.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'error': 'Не в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=[
        'post'
    ], permission_classes=[IsAuthenticated], url_path='shopping_cart')
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        serializer = ShoppingCartCreateSerializer(
            data={'recipe': recipe.id, 'user': request.user.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'error': 'Не в корзине'},
                status=status.HTTP_400_BAD_REQUEST
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
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')

        content = "Список покупок:\n\n"
        for item in ingredients:
            content += (
                f"{item['ingredient__name']} – {item['total_amount']} "
                f"{item['ingredient__measurement_unit']}\n"
            )

        response = HttpResponse(content, content_type='text/plain')
        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'
        return response


def redirect_to_recipe(request, code):
    recipe = get_object_or_404(Recipe, short_code=code)
    redirect_url = request.build_absolute_uri(f'/api/recipes/{recipe.id}/')
    return HttpResponseRedirect(redirect_url)
