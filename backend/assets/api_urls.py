from django.urls import path

from .api_views import (AssetView,)

urlpatterns = [
    path('', AssetView.as_view()),
]