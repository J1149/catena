from django.contrib.auth import get_user_model
from django.urls import reverse
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import login, logout
from dataclasses import dataclass, field

import requests
from urllib.parse import urlencode

from users.models import CatenaUser
from users.users import (get_signup_url, nonce)


# Create your views here.
class LoginView(View):
    http_method_names = ('get',)

    def get(self, *args, **kwargs):
        body = {"client_id": settings.PAIPASS_SSO_CLIENT_ID,
                "redirect_uri": settings.OAUTH_CALLBACK_URL,
                "response_type": 'code',
                'from': 'catena',
                # TODO create nonce generator
                "state": nonce(length=8),
                "scope": settings.REQ_SCOPES
                }
        url = ''.join([settings.PAIPASS_API_DOMAIN + 'oauth/authorize?', urlencode(body, doseq=True)])
        return HttpResponseRedirect(url)


class RegisterView(View):

    def get(self, *args, **kwargs):
        return HttpResponseRedirect(get_signup_url())


def reduce_to_value(d, keys):
    if len(keys) > 0:
        key = keys.pop(0)
        return reduce_to_value(d[key], keys)
    # it's not a dictionary anymore
    else:
        return d


def translate_for_internal_usage(user_data):
    translation = {}
    keys = [(['email', 'value'], 'email'),
            (['phone', 'value'], 'phone_number'),
            (['name', 'value'], 'full_name'),
            (['paicoin_address', 'value'], 'public_key'),
            (['email', 'user_id'], 'paipass_user_id'),
            (['accounttype', 'value'], 'account_type')]
    for key_tuple in keys:
        if key_tuple[0][0] in user_data:
            value = reduce_to_value(user_data, key_tuple[0])
            translation[key_tuple[1]] = value
    translation['refresh_token'] = user_data['refresh_token']
    return translation


def create_account(user_data):
    # user = get_user_model().objects.create(email=user_data['email']['value'],
    #                                        phone_number=user_data['phone']['value'],
    #                                        full_name=user_data['name']['value'],
    #                                        public_key=user_data['paicoin_address']['value'],
    #                                        paipass_user_id=user_data['email']['user_id'],
    #                                        account_type=user_data['accounttype']['value'])
    user = get_user_model().objects.create(**user_data)
    return user


def update_account(user, user_data):
    if user.paipass_user_id != user_data['paipass_user_id']:
        raise Exception("User ids do not match")
    # user.email = user_data['email']['value']
    # user.phone_number = user_data['phone']['value']
    # user.full_name = user_data['name']['value']
    # user.public_key = user_data['paicoin_address']['value']
    # user.paipass_user_id = user_data['email']['user_id']
    # user.account_type = user_data['accounttype']['value']
    for key in user_data:
        setattr(user, key, user_data[key])


def get_access_token(user, auth_code, grant_type):
    url = settings.PAIPASS_API_DOMAIN + "oauth/token/?"

    data = {'grant_type': grant_type,
            'redirect_uri': settings.OAUTH_CALLBACK_URL,
            'client_id': settings.PAIPASS_SSO_CLIENT_ID,
            }
    if grant_type == 'refresh_token':
        data['refresh_token'] = auth_code
    else:
        data['code'] = auth_code

    auth = (settings.PAIPASS_SSO_CLIENT_ID, settings.PAIPASS_SSO_CLIENT_SECRET)

    response = requests.post(url,
                             auth=auth,
                             data=data, )
    j = response.json()
    access_token = j["access_token"]
    refresh_token = None
    if 'refresh_token' in j:
        refresh_token = j['refresh_token']
    return access_token, refresh_token


def get_user_data(user, auth_code, state=None, grant_type='authorization_code'):
    access_token, refresh_token = get_access_token(user, auth_code, grant_type=grant_type)
    auth_header = 'Bearer {0}'.format(access_token)
    headers = {"Authorization": auth_header,
               "Accept": 'application/json',
               "Content-type": 'application/json;charset=utf-8'}

    user_data = {'refresh_token': refresh_token}
    for url in settings.REQ_DATA_URLS:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            continue
        else:
            user_data.update(response.json())

    if 'email' not in user_data:
        return None, 'Email was not found in the user\'s data'

    return translate_for_internal_usage(user_data), None


def get_user(user_data):
    qs = get_user_model().objects.all().filter(paipass_user_id=user_data['paipass_user_id'])
    if qs.count() < 1:
        return None
    else:
        user = qs.first()
    return user


def error_out(reason=None):
    return HttpResponseRedirect('/?error=True')


class LoginTokenView(View):
    http_method_names = ('get',)

    def login(self):
        pass

    def get(self, request, *args, **kwargs):
        auth_code = request.GET.get('code', None)
        state = request.GET.get('state', None)
        user_data, reason = get_user_data(request.user, auth_code, state)

        if reason is not None:
            return error_out(reason)

        user = get_user(user_data)
        if user is None:
            user = create_account(user_data)

        user.refresh_token = user_data['refresh_token']
        user.save()

        login(request, user)

        return HttpResponseRedirect('/')


class LogoutView(View):
    http_method_names = ('get',)

    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect('/')


@dataclass
class UserProfile:
    account_type: str = None
    email: str = None
    full_name: str = None
    phone_number: str = None
    public_key: str = None
    description: str = None
    is_user_requesting_themself: bool = False




class ProfileView(TemplateView):
    template_name = 'profile/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        up = UserProfile()
        context['user_profile'] = up
        if 'pub_key_addr' in kwargs:
            user = CatenaUser.objects.all().get(public_key=kwargs['pub_key_addr'])
        elif not user.is_authenticated:
            return context
        else:
            up.email = user.email
            up.full_name = user.full_name
            up.phone_number = user.phone_number
            up.is_user_requesting_themself = True

        up.account_type = user.account_type
        up.public_key = user.public_key
        up.description = user.description
        up.dm_url = reverse('messages_compose_to', kwargs={'recipient': up.public_key})

        return context


    def post(self, request, *args, **kwargs):
        user = request.user
        user.description = request.POST.get('description')
        user.save()
        return HttpResponseRedirect('/users/profile/')


class RefreshProfileView(View):

    def post(self, request, *args, **kwargs):
        user_data, reason = get_user_data(request.user, request.user.refresh_token, grant_type='refresh_token')
        if reason is not None:
            return error_out(reason)

        update_account(request.user, user_data)
        request.user.refresh_token = user_data['refresh_token']
        request.user.save()
        return HttpResponseRedirect('/users/profile/?')
