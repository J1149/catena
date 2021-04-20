from io import BytesIO

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

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
from datetime import datetime
from PIL import Image
from users.users import get_signup_url
from users.models import CatenaUser


ASSETS_PER_PAGE = 10


def transform_timeline_events(timeline_events, convert_iso_format=True):
    out = []
    for (name, obj) in iter_obj(timeline_events, key_name=None, is_recursive=False):
        te = TimelineEvent()
        for (name_inner, inner_obj) in iter_obj(obj, key_name=None):
            value = inner_obj['value']
            if convert_iso_format and name_inner == 'timestamp':
                value = datetime.fromisoformat(value)
            setattr(getattr(te, name_inner), 'value', value)
            if 'data_id' in inner_obj:
                setattr(getattr(te, name_inner), 'data_id', inner_obj['data_id'])

        out.append(te)
    return out


def append_field(d, name, value, type_, value_actual=None, ):
    d['name'] = name
    d['value'] = value
    d['fieldType'] = type_
    if value_actual is not None:
        d['value_actual'] = value_actual


def append_fields(tree, post, field_names, field_type=None):
    if field_type is None:
        field_type = 'TEXT'
    for count, field_name in enumerate(field_names, start=tree['count'] + 1):
        field_internal_name = f'field{count}'
        tree[field_internal_name] = {}

        append_field(tree[field_internal_name], field_name, post[field_name], field_type)
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


# if the user does not input a public key address,
# paipass will generate one internally from its own wallet
DEFAULT_PUB_KEY_ADDR = 'via_paipass'


def append_timeline_field(tree, name, value, type_, data_id=None, ):
    tree['count'] += 1
    field_internal_name = f'field{tree["count"]}'
    d = {}
    tree[field_internal_name] = d
    d['name'] = name
    d['value'] = value
    d['fieldType'] = type_
    if data_id is not None:
        d['data_id'] = data_id


def append_timeline_event_to_tree(timeline_events, timeline_event):
    subsubtree = {}
    timeline_events['count'] += 1
    timeline_events[f"field{timeline_events['count']}"] = subsubtree
    subsubtree['fieldType'] = 'OBJECT'
    subsubtree['name'] = 'Timeline Event'
    subsubtree['count'] = 0

    if timeline_event.timestamp.value is None:
        timeline_event.timestamp.value = datetime.utcnow().isoformat()

    append_timeline_field(subsubtree, 'Event Name', timeline_event.event_name.value, 'TEXT',
                          timeline_event.event_name.data_id)
    append_timeline_field(subsubtree, 'Blockchain Address', timeline_event.blockchain_address.value, 'TEXT',
                          timeline_event.blockchain_address.data_id)
    append_timeline_field(subsubtree, 'Timestamp', timeline_event.timestamp.value, 'DATE',
                          timeline_event.timestamp.data_id)


def construct_tree(request, substitute_ids_from=None, has_images=False, is_new_submission=False):
    schema_uuid = settings.CATENA_SCHEMA_ASSET_UUID
    tree = {}
    tree['id'] = schema_uuid
    tree['uuid'] = str(uuid4())
    tree['count'] = 0
    tree['name'] = 'Catena Assets'

    derived_tree = {}

    asset_owner = derived_tree.get('Asset Owner', request.user.email)
    derived_tree = {'Asset Owner': asset_owner,
                    'Asset Poster': asset_owner,
                    }
    derived_tree.update(request.POST.dict())

    asset_pub_key_addr = derived_tree.get('Asset Public Key Address', request.user.public_key)
    asset_pub_key = derived_tree.get('Asset Public Key', None)
    if asset_pub_key is None:
        encryption_value = 'unencrypted'
    else:
        encryption_value = 'encrypted'

    # this part of the config is built to imitate Pdp2Cfg in pdp2.py in paipass
    tree['cfg'] = {'name': 'paipass',
                   # the possible ops are found with the definition
                   # of Pdp2Op in pdp2.py in paipass
                   # 'op': 'OP_STORE',
                   'op': 'OP_SEND',
                   'pub_key_addr': asset_pub_key_addr,
                   'pub_key': asset_pub_key,
                   'amount': 0.00013,
                   'is_pub_key_ours': asset_pub_key_addr == DEFAULT_PUB_KEY_ADDR or asset_pub_key_addr == request.user.public_key,
                   'encryption_value': encryption_value,
                   # maybe this should depend on whether there are files
                   # attached
                   'is_compressed': False,
                   'watched_by': {
                       'name': 'PDP2'
                   }}

    # apparently if the box is not checked, a key named Public will not be in the
    # tree
    if 'Public' in derived_tree and derived_tree['Public'].lower() == 'on':
        tree['cfg']['shared_with'] = 'everyone'
    else:
        tree['cfg']['shared_with'] = 'self'

    # TODO This wasn't in the forms initially; delete this once it's added to the forms
    if 'Price Units' not in derived_tree:
        derived_tree['Price Units'] = 'USD'

    append_fields(tree, derived_tree,
                  ['Name', 'Asset Owner', 'Asset Poster', 'Price', 'Price Units',
                   'Description', 'Artist'])
    tes_subtree = {}
    tree['count'] += 1
    tree[f"field{tree['count']}"] = tes_subtree
    tes_subtree['fieldType'] = 'LIST'
    tes_subtree['name'] = 'Timeline Events'
    tes_subtree['count'] = 0
    if is_new_submission:
        subsubtree = {}
        tes_subtree['count'] += 1
        tes_subtree[f"field{tes_subtree['count']}"] = subsubtree
        subsubtree['fieldType'] = 'OBJECT'
        subsubtree['name'] = 'Timeline Event'
        subsubtree['count'] = 0

        derived_tree['Blockchain Address'] = asset_pub_key_addr
        derived_tree['Timestamp'] = datetime.utcnow().isoformat()
        derived_tree['Event Name'] = derived_tree.get('Change Description', 'Initial Submission')
        append_fields(subsubtree, derived_tree,
                      ['Event Name', 'Blockchain Address', ])
        append_fields(subsubtree, derived_tree, ('Timestamp',), field_type='DATE')
    # subtree['count'] += 1
    # subsubtree['count'] += 1
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
        for (key, obj) in iter_obj(tree, None, is_recursive=False):
            if key in substitute_ids_from:
                obj['data_id'] = substitute_ids_from.get_field(key).data_id
        for timeline_event in substitute_ids_from.timeline_events:
            # append_change(tes_subtree, timeline_event.blockchain_address, timeline_event.event_name, timeline_event.timestamp, data_id=timeline_event.data_id)
            append_timeline_event_to_tree(tes_subtree, timeline_event)
    return tree, out_files


class AddAssetView(TemplateView):
    template_name = 'assets/add_asset.html'
    http_method_names = ('get', 'post')

    def post(self, request, *args, **kwargs):
        tree, out_files = construct_tree(request, has_images=True, is_new_submission=True)

        session = login()
        session.headers.update({'X-CSRFToken': session.cookies['csrftoken']})
        # The content-type found in the session headers disrupts what
        # requests would have otherwise put in there if it wasn't there.
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


TXID_NOT_FOUND = 'Transaction Id Not Found'


@dataclass
class CatenaAsset:
    asset_id: str = None

    name: str = None
    asset_owner: str = None
    asset_poster: str = None
    artist: str = None
    description: str = None
    price: str = None
    price_units: str = "USD"
    dm_url: str = None
    profile_url: str = None
    shared_with: str = None
    txid: str = TXID_NOT_FOUND
    txid_url: str = None
    blockchain_address: str = None
    timeline_events: list = field(default_factory=list)
    images: list = field(default_factory=list)


@dataclass
class TimelineValue:
    value: 'typing.Any' = None
    data_id: str = None


@dataclass
class TimelineEvent:
    event_name: TimelineValue = field(default_factory=TimelineValue)
    blockchain_address: TimelineValue = field(default_factory=TimelineValue)
    timestamp: TimelineValue = field(default_factory=TimelineValue)


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
        self.timeline_events = tuple()
        self.generate_fields(d)

    def generate_fields(self, d):
        for (key, obj) in iter_obj(d, None, is_recursive=False):

            if key == 'timeline_events':
                self.timeline_events = transform_timeline_events(obj, convert_iso_format=False)
            else:
                fieldType = obj['fieldType'].upper()
                if fieldType == 'LIST' or fieldType == 'OBJECT':
                    continue
                if obj['data_id'] is None:
                    continue
                car = CatenaAssetRawishField(name=obj['name'], value=obj['value'], data_id=obj['data_id'])
                self.append_field(car)

    def append_field(self, car):
        self._fields.append(car)
        if car.name not in self._names_to_assets:
            self._names_to_assets[car.name] = car
        else:
            if isinstance(self._names_to_assets[car.name], list):
                self._names_to_assets[car.name].append(car)
            else:
                old_car = self._names_to_assets[car.name]
                self._names_to_assets[car.name] = [old_car, car]

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


def yield_pair(name, obj, key_name, image_key_name):
    if key_name in obj:
        if name.lower() == 'main_thumbnail':
            return name, obj[image_key_name]
        else:
            return name, obj[key_name]
    else:
        return name, obj


def iter_obj(assets_obj, key_name, image_key_name=None, is_recursive=True):
    if image_key_name is None:
        image_key_name = key_name
    for key, obj in assets_obj.items():
        if 'field' in key and key != 'fieldType':
            # field_type = assets_obj['fieldType']
            name = normalize_name(obj['name'])

            if is_recursive and (obj['fieldType'].upper() == 'OBJECT' or obj['fieldType'].upper() == 'LIST'):
                yield yield_pair(name, obj, key_name, image_key_name)
                for (subkey, subobj) in iter_obj(obj, key_name, image_key_name):
                    yield (subkey, subobj)
            else:
                name, obj = yield_pair(name, obj, key_name, image_key_name)
                yield name, obj


def get_obj_from_obj(from_obj, key_name):
    for (name, obj) in iter_obj(from_obj, key_name='value'):
        if normalize_name(key_name) == name:
            return obj
    return None


def get_most_recent_blockchain_addr(timeline_events):
    count = timeline_events['count']
    latest_timeline_event = timeline_events['field' + str(count - 1)]
    for (name, value) in iter_obj(latest_timeline_event, key_name='value'):
        if name.lower() == 'blockchain_address'.lower():
            return value

    return None


def transform(data):
    catena_assets = []
    # just a number that fits the txid into the modal
    txid_truncation_len = 31
    for asset_id, catena_assets_set in data.items():
        catena_asset = CatenaAsset()
        catena_asset.asset_id = asset_id
        for (name, value) in iter_obj(catena_assets_set, key_name='value', image_key_name='data_id'):

            value = normalize_value(name, value)
            if name == 'images':
                for (_, image_id) in iter_obj(value, key_name='data_id'):
                    catena_asset.images.append(image_id)
            else:
                setattr(catena_asset, normalize_name(name), value)
        setattr(catena_asset, 'shared_with', catena_assets_set['shared_with'])

        blockchain_address = get_most_recent_blockchain_addr(catena_asset.timeline_events)
        if blockchain_address is None:
            settings.LOGGER.critical(f'Asset blockchain address was none for asset_id {catena_asset.asset_id}')
        setattr(catena_asset, 'blockchain_address', blockchain_address)

        if catena_assets_set['txid'] is not None:
            setattr(catena_asset, 'txid', catena_assets_set['txid'][:txid_truncation_len] + '...')
            setattr(catena_asset, 'txid_url', f"https://paichain.info/ui/tx/{catena_assets_set['txid']}")

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
            dataset.dm_url = reverse('pai_messages', kwargs={'recipients': dataset.asset_owner}) +\
                             '?name=' + dataset.name + '&about=' + dataset.blockchain_address
        if dataset.asset_owner == 'self':
            dataset.profile_url = reverse('users:profile')
        else:
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


def append_change(catena_asset, asset_pub_key_addr, change_reason, timestamp=None, data_id=None):
    subtree = get_obj_from_obj(catena_asset, 'timeline events')
    if subtree is None:
        raise ValueError(f'obj is none for {catena_asset} when searching for timeline events')

    subsubtree = {}
    subtree['count'] += 1
    subtree[f"field{subtree['count']}"] = subsubtree
    subsubtree['fieldType'] = 'OBJECT'
    subsubtree['name'] = 'Timeline Event'
    subsubtree['count'] = 0

    fake_catena_asset = {}
    fake_catena_asset['Blockchain Address'] = asset_pub_key_addr
    if timestamp is None:
        fake_catena_asset['Timestamp'] = datetime.utcnow().isoformat()
    else:
        fake_catena_asset['Timestamp'] = timestamp
    fake_catena_asset['Event Name'] = fake_catena_asset.get('Change Description', change_reason)
    append_fields(subsubtree, fake_catena_asset,
                  ['Event Name', 'Blockchain Address', ])
    append_fields(subsubtree, fake_catena_asset, ('Timestamp',), field_type='DATE')
    return catena_asset


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
        asset_pub_key_addr = request.POST.get('Asset Public Key Address', request.user.public_key)
        append_change(tree, asset_pub_key_addr, 'Edit')
        session.headers.update({'X-CSRFToken': session.cookies['csrftoken']})
        data = {'tree': json.dumps(tree)}

        url = settings.PAIPASS_API_DOMAIN + f'api/v1/yggdrasil/dataset/{asset_id}/'
        response = session.put(url, data=data)
        response.raise_for_status()
        return HttpResponseRedirect(reverse('assets:index'))


class TransferAssetView(TemplateView):
    template_name = 'assets/transfer_asset.html'
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
        # this makes the request.POST mutable
        request.POST = request.POST.copy()
        new_owner = get_user_model().objects.all().get(public_key=request.POST['Asset Owner']).email
        request.POST['Asset Owner'] = new_owner
        request.POST['Asset Poster'] = new_owner
        tree, _ = construct_tree(request, substitute_ids_from=catena_asset, has_images=False)

        asset_pub_key_addr = request.POST.get('Asset Public Key Address', request.user.public_key)
        append_change(tree, asset_pub_key_addr, 'Transfer')

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


def get_provenance(data_id):
    url = settings.PAIPASS_API_DOMAIN + 'api/v1/yggdrasil/data-bundle/' + '?id=' + data_id
    session = login()
    response = session.get(url)
    response.raise_for_status()
    data = response.json()
    catena_asset = transform(data)[0]

    timeline_events = transform_timeline_events(catena_asset.timeline_events)

    return timeline_events


class AssetProvenanceView(TemplateView):
    template_name = 'assets/asset_provenance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['provenance_list'] = get_provenance(kwargs['asset_id'])
        context['is_home_page'] = False
        return context


