from io import BytesIO

from django.core.files.base import ContentFile
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View, TemplateView
from django.conf import settings
from django.urls import reverse
import requests
from uuid import uuid4
import json
from urllib.parse import urlencode
from django.http import FileResponse, StreamingHttpResponse, HttpResponse
from dataclasses import dataclass, field
from PIL import Image
from users.users import get_signup_url
from users.models import CatenaUser

ASSETS_PER_PAGE = 10


def append_field(d, name, value, type_, value_actual=None, ):
    d['name'] = name
    d['value'] = value
    d['fieldType'] = type_
    if value_actual is not None:
        d['value_actual'] = value_actual


def append_fields(tree, post, field_names):
    type_ = 'TEXT'
    for count, field_name in enumerate(field_names, start=tree['count'] + 1):
        field_internal_name = f'field{count}'
        tree[field_internal_name] = {}

        append_field(tree[field_internal_name], field_name, post[field_name], type_)
        tree['count'] += 1


def get_out_filename(tree, uid, dataset_uuid):
    '''
    from the Paipass frontend:

    // r* and the chars thereafter allow the django backend to uniquely
    // identify this file upload set and will allow us
    // to make a GET request with the corresponding r* id
    const uid = 'file_' + Object.keys(fylesStruct).length + '_' + field['value'] + 'r*' + dataset['uuid'];
    fylesStruct[uid] = fyle;
    fileSizes[uid] = fyle.size;
    '''
    return f"file_{tree['count']}_{uid}r*{dataset_uuid}"


def append_image(tree, file, out_files, dataset_uuid, name, count=0):
    type_ = 'IMAGE'
    field_internal_name = f'field{count}'
    tree[field_internal_name] = {}
    uid = str(uuid4())
    field_name = file.name + uid
    # no idea why value_actual[0]['path'] isn't here instead;
    # keeping with the og spec found in paipass' frontend;
    # I think it has to do with how this field is named in the schema...
    d = tree[field_internal_name]
    value_actual = [{'path': file.name}]
    append_field(d, name, uid, type_, value_actual)
    tree['count'] += 1
    out_filename = get_out_filename(tree, uid, dataset_uuid)
    out_files[out_filename] = file


def append_images(tree, files, dataset_uuid):
    out_files = {}
    for count, file in enumerate(files.getlist('Images'), tree['count'] + 1):
        append_image(tree, file, out_files, dataset_uuid, name='Image', count=count)
    tree['count'] += 1
    return out_files


def login():
    """
    Login so we can register the app.
    """
    session = requests.Session()
    username = settings.PAIPASS_DEV_EMAIL
    password = settings.PAIPASS_DEV_PASS
    session.headers = {'content-type': 'application/x-www-form-urlencoded',
                       # Apparently some mechanism is stripping out parts
                       # of the header if it is prefixed with HTTP.
                       # I found that the login was crashing because it was
                       # missing an HTTP_REFERER. Initially, I appended a
                       # k-v pair of HTTP_REFERER: localhost to the headers
                       # but it was missing when I printed out the values
                       # inside request.META. I decided to check if it was
                       # being stripped out somehow and added a k-v pair
                       # of PEANUT-BUTTER: JELLY TIME to the headers. On
                       # the django side it was represent as:
                       # HTTP_PEANUT_BUTTER: Jelly Time.
                       # Upon removing the prefix HTTP from HTTP_REFERER,
                       # the login started working with the headers being
                       # represented in request.META as:
                       # HTTP_REFERER: localhost
                       'REFERER': settings.BACKEND_DOMAIN,
                       # HTTP_REFERER seems to be getting stripped; let's
                       # see if this makes it through. This worked...
                       }
    params = {'email': username, 'password': password}
    response = session.post(settings.PAIPASS_API_DOMAIN + r'api/v1/rest-auth/login/',
                            headers=session.headers,
                            data=params,
                            allow_redirects=False)
    response.raise_for_status()
    print('login succeeded!')
    return session


MAX_WIDTH = 256
MAX_HEIGHT = 256
MAX_SIZE = MAX_WIDTH, MAX_HEIGHT


def to_thumbnail(img):
    thumbnail = Image.open(img)
    og_width = thumbnail.size[0]
    og_height = thumbnail.size[1]
    if og_width > MAX_WIDTH or og_height > MAX_HEIGHT:
        thumbnail.thumbnail(MAX_SIZE, Image.BICUBIC)
    b = BytesIO()
    thumbnail.save(fp=b, format='PNG')
    return ContentFile(b.getvalue(), name=img.name)


def construct_tree(request, substitute_ids_from=None, has_images=False):
    schema_uuid = settings.CATENA_SCHEMA_ASSET_UUID
    tree = {}
    tree['id'] = schema_uuid
    tree['uuid'] = str(uuid4())
    tree['count'] = 0
    tree['name'] = 'Catena Assets'
    derived_tree = {'Asset Poster': request.user.email,
                    'Asset Owner': request.user.email}
    derived_tree.update(request.POST.dict())

    if derived_tree['Public'].lower() == 'on':
        tree['shared_with'] = 'everyone'
    else:
        tree['shared_with'] = 'self'

    append_fields(tree, derived_tree,
                  ['Name', 'Asset Owner', 'Asset Poster', 'Price', 'Description', 'Artist'])

    out_files = None
    if has_images:
        subtree = {}
        tree['count'] += 1
        tree[f"field{tree['count']}"] = subtree
        subtree['fieldType'] = 'LIST'
        subtree['name'] = 'Images'
        subtree['count'] = 0

        out_files = append_images(subtree, request.FILES, dataset_uuid=tree['uuid'])
        thumbnail = to_thumbnail(request.FILES['thumbnail'])
        append_image(tree, thumbnail, out_files,
                     dataset_uuid=tree['uuid'], name='Main Thumbnail',
                     count=tree['count'] + 1)

        tree['count'] += 1
    if substitute_ids_from is not None:
        for key, obj in iter_obj(tree, None):
            if key in substitute_ids_from:
                obj['data_id'] = substitute_ids_from.get_field(key).data_id
    return tree, out_files


class AddAssetView(TemplateView):
    template_name = 'assets/add_asset.html'
    http_method_names = ('get', 'post')

    def post(self, request, *args, **kwargs):
        tree, out_files = construct_tree(request, has_images=True)

        session = login()
        session.headers.update({'X-CSRFToken': session.cookies['csrftoken']})
        # The content-type found in the session headers disrupts what
        # requests would otherwise put in their if it wasn't there.
        del session.headers['content-type']

        # requests.post() strips out nested json so we need to put it into a string and then json.loads() the
        # string at the destination
        data = {'tree': json.dumps(tree)}

        response = session.post(settings.PAIPASS_API_DOMAIN + 'api/v1/yggdrasil/dataset/',
                                data=data,
                                files=out_files)

        response.raise_for_status()

        return HttpResponseRedirect('/')


@dataclass
class DatasetsAbbreviated:
    ids: list = field(default_factory=list)
    next: int = None
    previous: int = None


def get_page_num(url):
    # api/v1/yggdrasil/datasets/?Asset+Poster=ryanh%2Bdev%40j1149.com&orderBy=-created_on&orderDir=DESC&page=2&perPage=1
    if url is None:
        return None
    # when we are on page 2, django will send back a url that does not include the page query param
    if 'page' not in url:
        return 1
    s = url.split('&page=')[-1]
    if '&' in s:
        return int(s.split('&')[0])
    return int(s)


def get_datasets(session, num_datasets, page, query_params=None):
    url = settings.PAIPASS_API_DOMAIN + 'api/v1/yggdrasil/datasets/?'
    body = {'orderDir': 'DESC',
            'perPage': num_datasets,
            'orderBy': '-created_on',
            'page': page,
            }

    if query_params is not None:
        body.update(query_params)

    url_token = ''.join([url, urlencode(body)])

    response = session.get(url_token)
    response.raise_for_status()
    j = response.json()
    da = DatasetsAbbreviated()
    da.ids = list(map(lambda d: d['id'], j['results']))
    next = get_page_num(j['next'])
    prev = get_page_num(j['previous'])
    da.next = '?page=' + str(next) if next else next
    da.prev = '?page=' + str(prev) if prev else prev
    return da


@dataclass
class TimelineEvent:
    event_name: str
    timestamp: str
    blockchain_address: str


@dataclass
class CatenaAsset:
    asset_id: str = None
    name: str = None
    asset_owner: str = None
    asset_poster: str = None
    artist: str = None
    description: str = None
    price: str = None
    price_units: str = None
    dm_url: str = None
    profile_url: str = None
    shared_with: str = None
    timeline_events: list = field(default_factory=list)
    images: list = field(default_factory=list)


class CatenaAssetRawishField:

    def __init__(self, name, value, data_id):
        self.name = normalize_name(name)
        self.value = normalize_value(self.name, value)
        self.data_id = data_id


class CatenaAssetRawish:

    def __init__(self, asset_id, d):
        self.asset_id = asset_id
        self._d = d
        self._fields = []
        self._names_to_assets = {}
        self.generate_fields(d)

    def generate_fields(self, d):
        for key, obj in iter_obj(d, None):
            if obj['fieldType'].upper() == 'LIST' or obj['fieldType'].upper() == 'OBJECT':
                continue
            if obj['data_id'] is None:
                continue
            print('name', obj['name'])
            print(obj, flush=True)
            car = CatenaAssetRawishField(name=obj['name'], value=obj['value'], data_id=obj['data_id'])
            self.append_field(car)

    def append_field(self, car):
        self._fields.append(car)
        self._names_to_assets[car.name] = car

    def __contains__(self, item):
        return item in self._names_to_assets

    def __getitem__(self, item):
        return self._names_to_assets[item].value

    def get_field(self, item):
        return self._names_to_assets[item]

def normalize_name(name):
    return name.strip().replace(' ', '_').lower()

def normalize_value(name, value):
    # if it's an email address, change it to the public key address
    if name == 'asset_owner' and '@' in value:
        users = CatenaUser.objects.all().filter(email=value)
        if users.count() > 0:
            value = users.first().public_key
    return value


def iter_obj(assets_obj, key_name, image_key_name=None):
    if image_key_name is None:
        image_key_name = key_name
    for key, obj in assets_obj.items():
        if 'field' in key and key != 'fieldType':
            #field_type = assets_obj['fieldType']
            name = normalize_name(obj['name'])
            if key_name in obj:
                if name.lower() == 'main_thumbnail':
                    yield name, obj[image_key_name]
                else:
                    yield name, obj[key_name]
            else:
                yield name, obj


def transform(data):
    catena_assets = []
    for asset_id, catena_assets_set in data.items():
        catena_asset = CatenaAsset()
        catena_asset.asset_id = asset_id
        for name, value in iter_obj(catena_assets_set, key_name='value', image_key_name='data_id'):

            value = normalize_value(name,value)
            if name == 'images':
                for _, image_id in iter_obj(value, key_name='data_id'):
                    catena_asset.images.append(image_id)
            else:
                setattr(catena_asset, normalize_name(name), value)
        setattr(catena_asset, 'shared_with', catena_assets_set['shared_with'])
        catena_assets.append(catena_asset)
    return catena_assets


def data_ids_to_query_params(ids):
    out = ''
    for i in range(len(ids)):
        out += f'id={ids[i]}&'
    return out


def get_data_bundle(ids, session=None, transform_to=None):
    if transform_to is None:
        transform_to = 'CatenaAsset'
    if session is None:
        session = login()
    try:
        suffix = '?'
        suffix += data_ids_to_query_params(ids)
        url = settings.PAIPASS_API_DOMAIN + 'api/v1/yggdrasil/data-bundle/' + suffix
        response = session.get(url)
        response.raise_for_status()
        data = response.json()
        if transform_to == 'CatenaAsset':
            data = transform(data)
        elif transform_to == 'CatenaAssetRawish':
            catena_assets = []
            for asset_id, catena_assets_set in data.items():
                car = CatenaAssetRawish(asset_id, catena_assets_set)
                catena_assets.append(car)
            data = catena_assets
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return []
    # suffix = '?'
    # for i in range(len(ids)):
    #     suffix += f'id={ids[i]}&'
    # url = settings.PAIPASS_API_DOMAIN + 'api/v1/yggdrasil/data-bundle/' + suffix
    # response = session.get(url)
    # response.raise_for_status()
    # transformation = transform(response.json())
    return data


def add_gallery_context_data(context, request, query_params=None):
    def add_images_to_ds(ds):
        new_images = []

        for image in ds.images:
            if image is None:
                continue
            image_url = reverse('assets:image', kwargs=dict(image_id=image))
            new_images.append(image_url)
        ds.images = new_images

    if query_params is None:
        query_params = {}
    session = login()
    page = request.GET.get('page', 1)

    ds_abbr = get_datasets(session,
                           num_datasets=ASSETS_PER_PAGE,
                           page=page,
                           query_params=query_params)

    data_bundle = get_data_bundle(ds_abbr.ids, session)
    is_anon_user = getattr(request.user, 'email', None) is None
    signup_url = get_signup_url()
    for dataset in data_bundle:

        add_images_to_ds(dataset)
        if is_anon_user:
            dataset.dm_url = signup_url
        elif request.user.public_key == dataset.asset_owner:
            dataset.asset_owner = 'self'
        else:
            dataset.dm_url = reverse('messages_compose_to', kwargs={'recipient': dataset.asset_owner})

        dataset.profile_url = reverse('users:profile', kwargs={'pub_key_addr': dataset.asset_owner})

    context['catena_assets'] = data_bundle
    context['PAIPASS_API_DOMAIN'] = settings.PAIPASS_API_DOMAIN
    context['next'] = ds_abbr.next if ds_abbr.next else "#"
    context['prev'] = ds_abbr.prev if ds_abbr.prev else "#"
    context['prev_disabled'] = "disabled" if ds_abbr.prev is None else ""
    context['next_disabled'] = "disabled" if ds_abbr.next is None else ""
    return context


class AssetView(View):

    def get(self, request, *args, **kwargs):
        pass

    def delete(self, request, asset_id, *args, **kwargs):
        session = login()
        catena_asset = get_data_bundle((asset_id,), session=session)[0]
        if catena_asset.asset_owner != request.user.public_key:
            return HttpResponse({'detail': 'user does not own the asset'}, status=403)

        session.headers.update({'X-CSRFToken': session.cookies['csrftoken']})
        url = settings.PAIPASS_API_DOMAIN + f'api/v1/yggdrasil/dataset/{asset_id}/'
        response = session.delete(url)
        response.raise_for_status()

        return HttpResponse({'detail': 'success'})


class EditAssetView(TemplateView):
    template_name = 'assets/edit_asset.html'
    http_method_names = ('get', 'post')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = kwargs['asset_id']
        catena_asset = get_data_bundle((asset_id,))[0]
        context['catena_asset'] = catena_asset
        if catena_asset.shared_with == 'everyone':
            context['checked'] = 'checked'
        else:
            context['checked'] = ''
        return context

    def post(self, request, asset_id, *args, **kwargs):
        session = login()
        catena_asset = get_data_bundle((asset_id,), session=session, transform_to='CatenaAssetRawish')[0]
        if catena_asset['asset_owner'] != request.user.public_key:
            return HttpResponse({'detail': 'user does not own the asset'}, status=403)

        tree, _ = construct_tree(request, substitute_ids_from=catena_asset, has_images=False)

        session.headers.update({'X-CSRFToken': session.cookies['csrftoken']})
        data = {'tree': json.dumps(tree)}

        url = settings.PAIPASS_API_DOMAIN + f'api/v1/yggdrasil/dataset/{asset_id}/'
        response = session.put(url, data=data)
        response.raise_for_status()
        return HttpResponseRedirect(reverse('assets:index'))


class AssetsView(TemplateView):
    template_name = 'assets/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = {'Asset Poster': self.request.user.email}
        context = add_gallery_context_data(context, self.request, query_params)
        context['is_home_page'] = False
        return context


class ImageView(View):

    def get(self, request, image_id, *args, **kwargs):
        session = login()
        response = session.get(settings.PAIPASS_API_DOMAIN + f'api/v1/yggdrasil/data/{image_id}/')
        # out_response = FileResponse(response.content)
        # out_response = StreamingHttpResponse(streaming_content=response.content, content_type="image/jpeg")
        out_response = HttpResponse(response.content, content_type="image/jpeg")
        out_response['Cache-Control'] = 'max-age=86400'
        return out_response