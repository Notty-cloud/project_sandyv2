from rest_framework.pagination import PageNumberPagination


class ConfigurablePageNumberPagination(PageNumberPagination):
    """
    Page-number pagination that lets the client choose the page size.

    The default PageNumberPagination ignores ?page_size entirely, so every list
    was capped at PAGE_SIZE. The student list has no pagination controls in the
    UI, which meant a school with 500 students silently saw the first 50 and no
    indication the rest existed — worse than an error, because it looks like the
    import lost records.

    max_page_size still bounds it: a roster is a few hundred rows, and an
    unbounded page size is a denial-of-service knob.
    """

    page_size_query_param = 'page_size'
    max_page_size = 1000
