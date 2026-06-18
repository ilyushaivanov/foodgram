from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from rest_framework import serializers
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer
)

from foodgram.models import (Favorite, Follow, Ingredient, Profile, Recipe,
                             RecipeIngredient, ShoppingCart, Tag)

from drf_extra_fields.fields import Base64ImageField

User = get_user_model()
"""Ваши замечания полностью ломают спецификацию Api и я"""
"""уже отчаялся чтобы привести все обратно в рабочее состояние"""
"""У меня осталось 3 дня до 21 числа чтобы это сдать"""
"""Что мне делать я не знаю, пишу так потому что нет возможности связаться"""


class CustomUserCreateSerializer(DjoserUserCreateSerializer):
    """Также вы сказали использовать стандартный сериализатор djoser"""
    """для пользователя но также из за него не"""
    """получается привести к спецификации."""
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return value

    class Meta(DjoserUserCreateSerializer.Meta):
        fields = (
            'id', 'username', 'email', 'password', 'first_name', 'last_name'
        )


username_validator = RegexValidator(
    regex=r'^[\w.@+-]+\Z',
    message='Введите корректное имя пользователя.',
    code='invalid_username'
)


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.title', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar'
        ]

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile.avatar.url)
        return None

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, author=obj).exists()
        )


class FollowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['user', 'author']
        read_only_fields = ['user']

    def validate(self, attrs):
        user = self.context['request'].user
        author = attrs.get('author')
        if user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя')
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError('Уже подписаны')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = Profile
        fields = ('avatar')


class RecipeShortSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteShoppingCartSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'title', 'image', 'cooking_time')


class FavoriteAddResponseSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['recipes', 'recipes_count']

    def get_recipes(self, obj):
        request = self.context['request']
        limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all().order_by('-id')
        if limit:
            try:
                limit = int(limit)
                if limit > 0:
                    recipes = recipes[:limit]
            except ValueError:
                pass
        return RecipeShortSerializer(
            recipes, many=True, context=self.context
        ).data


class FavoriteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['user', 'recipe']
        read_only_fields = ['user']

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs.get('recipe')
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Уже в избранном')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ShoppingCartCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']
        read_only_fields = ['user']

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Уже в корзине')
        return attrs

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='ingredient_amounts', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    name = serializers.CharField(source='title', read_only=True)
    text = serializers.CharField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        )


class IngredientCreateSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        required=True
    )
    amount = serializers.IntegerField(min_value=1, required=True)


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        write_only=True, required=True, source='title'
    )
    text = serializers.CharField(write_only=True, required=True)
    image = Base64ImageField(write_only=True, required=True)
    ingredients = serializers.ListField(
        child=IngredientCreateSerializer(),
        write_only=True,
        required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        required=True
    )
    cooking_time = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'name', 'text', 'image', 'ingredients', 'tags', 'cooking_time'
        )

    def validate(self, attrs):
        ingredients = attrs.get('ingredients')
        if ingredients is not None:
            if not ingredients:
                raise serializers.ValidationError(
                    {'ingredients': 'Обязательное поле.'}
                )
            ingredient_ids = [item['id'].id for item in ingredients]
            if len(ingredient_ids) != len(set(ingredient_ids)):
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться.'}
                )
        tags = attrs.get('tags')
        if tags is not None and not tags:
            raise serializers.ValidationError(
                {'tags': 'Обязательное поле.'}
            )
        return attrs

    def _create_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def _update_ingredients(self, instance, ingredients_data):
        instance.ingredient_amounts.all().delete()
        self._create_ingredients(instance, ingredients_data)

    def create(self, validated_data, **kwargs):
        author = kwargs.get('author')
        if author is None:
            author = self.context['request'].user

        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(
            **validated_data,
            author=author
        )
        recipe.tags.set(tags)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        if ingredients_data is not None:
            self._update_ingredients(instance, ingredients_data)
        if tags is not None:
            instance.tags.set(tags)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
