import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from foodgram.models import (Favorite, Follow, Ingredient, Profile, Recipe,
                             RecipeIngredient, ShoppingCart, Tag, Unit)

User = get_user_model()


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'title', 'slug']


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class IngredientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    measurement_unit = serializers.CharField(
        source='measurement_unit.title', read_only=True
    )

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.title', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit.title', read_only=True
    )
    amount = serializers.FloatField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='profile.avatar', read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar'
        ]

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, max_length=254)
    username = serializers.CharField(required=True, max_length=150)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(
        required=True, write_only=True, min_length=1
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким username уже существует."
            )
        return value

    def validate_first_name(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        return value

    def validate_last_name(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.get_or_create(user=user)
        return user


class UserCreateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name']


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверен')
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField()

    class Meta:
        model = Profile
        fields = ['avatar']


class RecipeShortSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='title', read_only=True)
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class FavoriteShoppingCartSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'image', 'cooking_time']


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['recipes', 'recipes_count']

    def get_recipes(self, obj):
        request = self.context.get('request')
        if request:
            limit = request.query_params.get('recipes_limit')
            recipes = obj.recipes.all().order_by('-id')
            if limit:
                try:
                    limit = int(limit)
                    recipes = recipes[:limit]
                except ValueError:
                    pass
            return RecipeShortSerializer(
                recipes, many=True, context=self.context
            ).data
        return []


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
    image = serializers.ImageField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time'
        ]

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        write_only=True, required=True, source='title'
    )
    text = serializers.CharField(
        write_only=True, required=True
    )
    image = serializers.CharField(write_only=True, required=True)
    ingredients = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=True
    )
    cooking_time = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        model = Recipe
        fields = [
            'name', 'text', 'image', 'ingredients', 'tags', 'cooking_time'
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.method in ['PUT', 'PATCH']:
            if 'ingredients' not in self.initial_data:
                raise serializers.ValidationError(
                    {'ingredients': 'Обязательное поле.'}
                )
            if 'tags' not in self.initial_data:
                raise serializers.ValidationError(
                    {'tags': 'Обязательное поле.'}
                )
        return attrs

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        ingredient_ids = []
        for item in value:
            if 'id' not in item or 'amount' not in item:
                raise serializers.ValidationError(
                    "Каждый ингредиент должен содержать id и amount."
                )
            try:
                amount = float(item['amount'])
                if amount <= 0:
                    raise serializers.ValidationError(
                        "Количество должно быть положительным."
                    )
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    "Количество должно быть числом."
                )
            ing_id = item['id']
            if not Ingredient.objects.filter(id=ing_id).exists():
                raise serializers.ValidationError(
                    f"Ингредиент с id {ing_id} не существует."
                )
            if ing_id in ingredient_ids:
                raise serializers.ValidationError(
                    "Ингредиенты не должны повторяться."
                )
            ingredient_ids.append(ing_id)
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError("Теги не должны повторяться.")
        return value

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        if len(value) > 256:
            raise serializers.ValidationError(
                "Название не должно превышать 256 символов."
            )
        return value

    def validate_text(self, value):
        if not value:
            raise serializers.ValidationError("Обязательное поле.")
        return value

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Время приготовления должно быть не менее 1 минуты."
            )
        return value

    def _decode_image(self, base64_string):
        if not base64_string:
            raise serializers.ValidationError("Изображение обязательно.")
        try:
            if ';base64,' not in base64_string:
                raise ValueError()
            format, imgstr = base64_string.split(';base64,')
            ext = format.split('/')[-1]
            return ContentFile(
                base64.b64decode(imgstr), name=f'{uuid.uuid4()}.{ext}'
            )
        except Exception:
            raise serializers.ValidationError(
                "Неверный формат изображения. Ожидается base64."
            )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        image_data = validated_data.pop('image')
        title = validated_data.pop('title')
        text = validated_data.pop('text')
        cooking_time = validated_data.pop('cooking_time')
        author = self.context['request'].user

        image = self._decode_image(image_data)
        recipe = Recipe.objects.create(
            title=title,
            text=text,
            image=image,
            cooking_time=cooking_time,
            author=author
        )
        recipe.tags.set(tags)

        for item in ingredients_data:
            ingredient = Ingredient.objects.get(id=item['id'])
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=item['amount'],
                unit=ingredient.measurement_unit
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        image_data = validated_data.pop('image', None)
        title = validated_data.pop('title', None)
        text = validated_data.pop('text', None)
        cooking_time = validated_data.pop('cooking_time', None)

        if title is not None:
            instance.title = title
        if text is not None:
            instance.description = text
        if cooking_time is not None:
            instance.cooking_time = cooking_time
        if image_data is not None:
            instance.image = self._decode_image(image_data)

        instance.save()

        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.ingredient_amounts.all().delete()
            for item in ingredients_data:
                ingredient = Ingredient.objects.get(id=item['id'])
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=item['amount'],
                    unit=ingredient.measurement_unit
                )
        return instance
