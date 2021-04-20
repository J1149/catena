import requests

SITE_URL = 'http://localhost:7000/'
# SITE_URL = 'https://catenaart.com/'
def get_session(session_id):
    cd = {
        'sessionid': session_id,
        'csrftoken': 'cpUHacGzIaubrbYAvPG58zSWS2BD9d3LkOCszm5Ya244Gboco6ah2sNch3xaOrve',
    }
    cj = requests.utils.cookiejar_from_dict(cd)
    s = requests.Session()
    s.cookies = cj
    # response = s.get(SITE_URL + 'gallery/')
    return s


if __name__ == '__main__':
    s = get_session('m0aaj7yx00ifcqwy40jjjelv5mzvjjhq')
    headers = {'content-type': 'application/json', 'csrftoken': s.cookies['csrftoken'],
               'REFERER': 'http://localhost:7000'}
    data = {'txn_id': '123'}

    response = s.post(SITE_URL + 'api/v1/assets/',
                      headers=headers,
                      cookies=s.cookies,
                      json=data
                      )
    print(response)
