# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import url, include
from django.views.static import serve

urlpatterns = [
    url(r"^auth/", include("helios_auth.urls")),
    url(r"^helios/", include("helios.urls")),
    # SHOULD BE REPLACED BY APACHE STATIC PATH
    url(
        r"booth/(?P<path>.*)$",
        serve,
        {"document_root": str(settings.APPS_DIR.path("heliosbooth"))},
    ),
    url(
        r"verifier/(?P<path>.*)$",
        serve,
        {"document_root": str(settings.APPS_DIR.path("/heliosverifier"))},
    ),
    url(
        r"static/auth/(?P<path>.*)$",
        serve,
        {"document_root": str(settings.APPS_DIR.path("/helios_auth/media"))},
    ),
    url(
        r"static/helios/(?P<path>.*)$",
        serve,
        {"document_root": str(settings.APPS_DIR.path("/helios/media"))},
    ),
    url(
        r"static/(?P<path>.*)$",
        serve,
        {"document_root": str(settings.APPS_DIR.path("/server_ui/media"))},
    ),
    url(r"^", include("server_ui.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls)),] + urlpatterns
