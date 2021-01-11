from django.views.generic import TemplateView
from assets.views import add_gallery_context_data


class IndexPageView(TemplateView):
    template_name = 'main/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = add_gallery_context_data(context,
                                           request=self.request,
                                           query_params={'shared_with': 'everyone',
                                                         'distinct': 'Artist'})
        context['is_home_page'] = True
        return context
