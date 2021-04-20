from django.urls import path

from .views import (AssetView, AssetsView, AddAssetView, ImageView, EditAssetView, TransferAssetView,
                    AssetProvenanceView)

app_name = 'assets'

urlpatterns = [
    path('', AssetsView.as_view(), name='index'),
    path('add-asset/', AddAssetView.as_view(), name='add_asset'),
    path('image/<str:image_id>/',  ImageView.as_view(), name='image'),
    path('edit/<str:asset_id>/', EditAssetView.as_view(), name='edit'),
    path('transfer/<str:asset_id>/', TransferAssetView.as_view(), name='transfer'),
    path('provenance/<str:asset_id>/', AssetProvenanceView.as_view(), name='provenance'),
    # NOTE: This should probably always be last
    path('<str:asset_id>/', AssetView.as_view(), name='asset'),

]
