from django_filters.rest_framework import FilterSet, filters

from foodgram.models import Recipe, Tag


class RecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    author = filters.NumberFilter(field_name='author__id')
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('is_favorited', 'is_in_shopping_cart', 'author', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 'yes')
        if self.request and self.request.user.is_authenticated:
            if value:
                return queryset.filter(favorites__user=self.request.user)
            else:
                return queryset.exclude(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if isinstance(value, str):
            value = value.lower() in ('true', '1', 'yes')
        if self.request and self.request.user.is_authenticated:
            if value:
                return queryset.filter(shopping_cart__user=self.request.user)
            else:
                return queryset.exclude(shopping_cart__user=self.request.user)
        return queryset
