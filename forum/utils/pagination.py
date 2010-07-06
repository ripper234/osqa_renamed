import math
from django.utils.datastructures import SortedDict
from django import template
from django.core.paginator import Paginator, EmptyPage
from django.utils.translation import ugettext as _
from django.http import Http404
from django.utils.safestring import mark_safe
from django.utils.http import urlquote
import logging

class SimpleSort(object):
    def __init__(self, label, order_by, description=''):
        self.label = label
        self.description = description
        self.order_by = order_by

    def apply(self, objects):
        return objects.order_by(self.order_by)


class PaginatorContext(object):
    visible_page_range = 5
    outside_page_range = 1

    base_path = None

    def __init__(self, id, sort_methods=None, default_sort=None, pagesizes=None, default_pagesize=None):
        self.id = id
        if sort_methods:
            self.has_sort = True
            self.sort_methods = SortedDict(data=sort_methods)

            if not default_sort:
                default_sort = sort_methods[0][0]

            self.default_sort = default_sort
        else:
            self.has_sort = False


        if pagesizes:
            self.has_pagesize = True
            self.pagesizes = pagesizes

            if not default_pagesize:
                self.default_pagesize = pagesizes[int(math.ceil(float(len(pagesizes)) / 2)) - 1]
            else:
                self.default_pagesize = default_pagesize
        else:
            self.has_pagesize = False



class labels(object):
    PAGESIZE = _('pagesize')
    PAGE = _('page')
    SORT = _('sort')

page_numbers_template = template.loader.get_template('paginator/page_numbers.html')
page_sizes_template = template.loader.get_template('paginator/page_sizes.html')
sort_tabs_template = template.loader.get_template('paginator/sort_tabs.html')

def paginated(request, list_name, context, tpl_context):
    session_prefs = request.session.get('paginator_%s' % context.id, {})
    objects = tpl_context[list_name]

    if context.has_pagesize:
        if request.GET.get(labels.PAGESIZE, None):
            try:
                pagesize = int(request.GET[labels.PAGESIZE])
            except ValueError:
                logging.error('Found invalid page size "%s", loading %s, refered by %s' % (
                    request.GET.get(labels.PAGESIZE, ''), request.path, request.META.get('HTTP_REFERER', 'UNKNOWN')
                ))
                raise Http404()

            session_prefs[labels.PAGESIZE] = pagesize
        else:
            pagesize = session_prefs.get(labels.PAGESIZE, context.default_pagesize)

        if not pagesize in context.pagesizes:
            pagesize = context.default_pagesize
    else:
        pagesize = 30





    try:
        page = int(request.GET.get(labels.PAGE, 1))
    except ValueError:
        logging.error('Found invalid page number "%s", loading %s, refered by %s' % (
            request.GET.get(labels.PAGE, ''), request.path, request.META.get('HTTP_REFERER', 'UNKNOWN')
        ))
        raise Http404()

    sort = None
    if context.has_sort:
        if request.GET.get(labels.SORT, None):
            sort = request.GET[labels.SORT]
            if session_prefs.get('sticky_sort', False):
                session_prefs[labels.SORT] = sort
        else:
            sort = session_prefs.get(labels.SORT, context.default_sort)

        if not sort in context.sort_methods:
            sort = context.default_sort

        objects = context.sort_methods[sort].apply(objects)

    paginator = Paginator(objects, pagesize)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        logging.error('Found invalid page number "%s", loading %s, refered by %s' % (
            request.GET.get(labels.PAGE, ''), request.path, request.META.get('HTTP_REFERER', 'UNKNOWN')
        ))
        raise Http404()

    if context.base_path:
        base_path = context.base_path
    else:
        base_path = request.path
        get_params = ["%s=%s" % (k, v) for k, v in request.GET.items() if not k in (labels.PAGE, labels.PAGESIZE, labels.SORT)]

        if get_params:
            base_path += "?" + "&".join(get_params)

    url_joiner = "?" in base_path and "&" or "?"


    def get_page():
        object_list = page_obj.object_list

        if hasattr(object_list, 'lazy'):
            return object_list.lazy()
        return page_obj.object_list
    objects.page = get_page

    total_pages = paginator.num_pages

    if total_pages > 1:
        def page_nums():
            total_pages = paginator.num_pages

            has_previous = page > 1
            has_next = page < total_pages

            range_start = page - context.visible_page_range / 2
            range_end = page + context.visible_page_range / 2

            if range_start < 1:
                range_end = context.visible_page_range
                range_start = 1

            if range_end > total_pages:
                range_start = total_pages - context.visible_page_range + 1
                range_end = total_pages
                if range_start < 1:
                    range_start = 1

            page_numbers = []

            if sort:
                url_builder = lambda n: mark_safe("%s%s%s=%s&%s=%s" % (base_path, url_joiner, labels.SORT, sort, labels.PAGE, n))
            else:
                url_builder = lambda n: mark_safe("%s%s%s=%s" % (base_path, url_joiner, labels.PAGE, n))

            if range_start > (context.outside_page_range + 1):
                page_numbers.append([(n, url_builder(n)) for n in range(1, context.outside_page_range + 1)])
                page_numbers.append(None)
            elif range_start > 1:
                page_numbers.append([(n, url_builder(n)) for n in range(1, range_start)])

            page_numbers.append([(n, url_builder(n)) for n in range(range_start, range_end + 1)])

            if range_end < (total_pages - context.outside_page_range):
                page_numbers.append(None)
                page_numbers.append([(n, url_builder(n)) for n in range(total_pages - context.outside_page_range + 1, total_pages + 1)])
            elif range_end < total_pages:
                page_numbers.append([(n, url_builder(n)) for n in range(range_end + 1, total_pages + 1)])

            return page_numbers_template.render(template.Context({
                'has_previous': has_previous,
                'previous_url': has_previous and url_builder(page - 1) or None,
                'has_next': has_next,
                'next_url': has_next and url_builder(page + 1) or None,
                'current': page,
                'page_numbers': page_numbers
            }))
        objects.page_numbers = page_nums
    else:
        objects.page_numbers = ''

    if pagesize:
        def page_sizes():
            if sort:
                url_builder = lambda s: mark_safe("%s%s%s=%s&%s=%s" % (base_path, url_joiner, labels.SORT, sort, labels.PAGESIZE, s))
            else:
                url_builder = lambda s: mark_safe("%s%s%s=%s" % (base_path, url_joiner, labels.PAGESIZE, s))

            sizes = [(s, url_builder(s)) for s in context.pagesizes]

            return page_sizes_template.render(template.Context({
                'current': pagesize,
                'sizes': sizes
            }))

        objects.page_sizes = page_sizes
    else:
        objects.page_sizes = ''

    if sort:
        def sort_tabs():
            url_builder = lambda s: mark_safe("%s%s%s=%s" % (base_path, url_joiner, labels.SORT, s))
            sorts = [(n, s.label, url_builder(n), s.description) for n, s in context.sort_methods.items()]

            return sort_tabs_template.render(template.Context({
                'current': sort,
                'sorts': sorts,
                'sticky': session_prefs.get('sticky_sort', False)
            }))
        objects.sort_tabs = sort_tabs()
    else:
        objects.sort_tabs = ''

    request.session['paginator_%s' % context.id] = session_prefs
    tpl_context[list_name] = objects
    return tpl_context