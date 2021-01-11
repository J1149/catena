from urllib.parse import urlencode
from django.conf import settings
import random
import string
nonce_choices = string.ascii_letters + string.digits


def nonce(length):
    return ''.join([random.choice(nonce_choices) for i in range(length)])

def get_signup_url():
    body = {"client_id": settings.PAIPASS_SSO_CLIENT_ID,
            "redirect_uri": settings.OAUTH_CALLBACK_URL,
            "response_type": 'code',
            'from': 'catena',
            # TODO create nonce generator
            "state": nonce(length=8),
            "scope": settings.REQ_SCOPES
            }
    url_goto = ''.join(['oauth/authorize?', urlencode(body, doseq=True)])
    body2 = {'goTo': url_goto}
    url = ''.join([settings.PAIPASS_DOMAIN + 'signup?', urlencode(body2, doseq=True)])
    return url