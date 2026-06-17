from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet, RecipeViewSet,
    TagViewSet, UserViewSet, redirect_to_recipe
)

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('tags', TagViewSet)
router.register('ingredients', IngredientViewSet)
router.register('recipes', RecipeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('s/<str:code>/', redirect_to_recipe, name='short-link-redirect'),
    path('auth/', include('djoser.urls.authtoken')),
]
