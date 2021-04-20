from urllib.parse import urlparse
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

EXEMPT_URLS = {'/', '/gallery', '/users/login/', '/users/login-token/', '/users/register/', '/assets/image/'}

class RequireLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            if not any([exempt_url not in request.path_info for exempt_url in EXEMPT_URLS]):
                return redirect('/gallery')
        response = self.get_response(request)
        return response