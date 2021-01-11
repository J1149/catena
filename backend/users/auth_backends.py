from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model


class OAuthBackend(BaseBackend):

    def authenticate(self, request, token=None):
        pass

    def get_user(self, pk):
        user = get_user_model().object.all().get(id=pk)
        return user
