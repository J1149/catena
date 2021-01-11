from django.urls import path

from .views import (LoginView, LoginTokenView, LogoutView, ProfileView, RefreshProfileView, RegisterView)

app_name = 'users'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login-token/', LoginTokenView.as_view(), name='login_token'),

    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/<str:pub_key_addr>/', ProfileView.as_view(), name='profile'),
    path('refresh-profile/', RefreshProfileView.as_view(),  name='refresh-profile'),
    path('register/', RegisterView.as_view(), name='register'),

]