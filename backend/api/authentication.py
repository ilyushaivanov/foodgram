from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """Вы написали что это лишнее но без него падают тесты на аутентификацию,
    альтернативы я не вижу как реализовать это."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email=username).first()
        if user and user.check_password(password):
            return user
        return None