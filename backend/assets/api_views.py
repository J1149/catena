from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class AssetView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)


    def post(self, request, *args, **kwargs):

        return Response({'detail': 'hello world'}, status=status.HTTP_200_OK)
