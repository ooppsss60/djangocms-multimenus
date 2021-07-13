from classytags.arguments import Argument, MultiKeywordArgument
from classytags.core import Options
from classytags.helpers import InclusionTag
from django import template
from django.db.models.signals import post_save
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.utils.translation import get_language
from django.core.cache import cache
from multimenus.models import MenuItem

register = template.Library()


def get_cache_key(menu_id, site_pk, lang):
    cache_key = 'multimenus-{}-{}-{}'.format(menu_id, site_pk, lang)
    return cache_key


@register.tag
class ShowMultiMenu(InclusionTag):
    DEFAULT_TEMPLATE_NAME = "multimenus/menu.html"
    name = 'show_multi_menu'
    push_context = True
    options = Options(
        Argument('menu_id', required=True),
        Argument('template', required=False),
        MultiKeywordArgument('params', required=False)
    )

    def get_template(self, context, **kwargs):
        template_name = kwargs.get('template')
        if not template_name:
            template_name = ShowMultiMenu.DEFAULT_TEMPLATE_NAME
        return template_name

    def get_context(self, context, menu_id, template=None, params={}):
        current_site = get_current_site(context['request'])
        cache_key = 'multimenus-{}-{}-{}'.format(menu_id, current_site.pk, get_language())
        menu_items = cache.get(cache_key)
        if menu_items is None:
            try:
                menu = MenuItem.objects.get(site=current_site, menu_id=menu_id)
                if 'include_self' in params and params['include_self']:
                    menu_items = [menu, ]
                else:
                    menu_items = menu.get_children()
            except MenuItem.DoesNotExist:
                menu_items = []
            cache.set(cache_key, menu_items, 60 * 60 * 24)
        return {
            'items': menu_items,
            'template': template or ShowMultiMenu.DEFAULT_TEMPLATE_NAME,
        }
    
 
def clear_cache(sender, instance, **kwargs):
    try:
        cache_key = get_cache_key(instance.menu_id, instance.site.pk, get_language())
        cache.delete(cache_key)
    except:
        pass
    try:
        if instance.get_root():
            cache_key = get_cache_key(instance.get_root().menu_id, instance.site.pk, get_language())
            cache.delete(cache_key)
    except:
        pass


post_save.connect(clear_cache, sender=MenuItem)
