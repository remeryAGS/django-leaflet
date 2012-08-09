import os, json

from django import template
from django.template import Context
from django.conf import settings

from leaflet import app_settings, SPATIAL_EXTENT


register = template.Library()


def base_url():
    version = app_settings.get('LEAFLET_VERSION')
    paths = (settings.STATIC_URL, "leaflet")
    if version:
        paths += (version,)
    return os.path.join(*paths)


@register.simple_tag
def leaflet_css():
    return """<link rel="stylesheet" type="text/css" href="%(static)s/leaflet.css">
    <!--[if lte IE 8]>
    <link rel="stylesheet" type="text/css" href="%(static)s/leaflet.ie.css" />
    <![endif]-->
    """ % {'static': base_url()}


@register.simple_tag
def leaflet_js():
    leafletjs = 'leaflet.min.js'
    if settings.TEMPLATE_DEBUG:
        leafletjs = 'leaflet.js'
    return """<script src="%(base)s/%(lf)s" type="text/javascript"></script>
              <script src="%(base)s/leaflet.extras.js" type="text/javascript"></script>""" % {
                'base': base_url(),
                'lf': leafletjs
            }


@register.simple_tag
def leaflet_map(name, callback=None, fitextent=True):
    if callback is None:
        callback = "%sInit" % name
    tilesurl = app_settings.get('TILES_URL')
    if tilesurl and isinstance(tilesurl, basestring):
        tilesurl = (('background', tilesurl),)
    extent = None
    if SPATIAL_EXTENT is not None:
        xmin, ymin, xmax, ymax = SPATIAL_EXTENT
        extent = (ymin, xmin, ymax, xmax)
    t = template.loader.get_template("leaflet/map_fragment.html")
    return t.render(Context(dict(name=name,
                                 extent=extent,
                                 fitextent=fitextent,
                                 tilesurl=[list(url) for url in tilesurl],
                                 callback=callback,
                                 scale=app_settings.get('SCALE'))))

@register.simple_tag
def leaflet_json_config():
    settings_as_json = app_settings.copy()

    if SPATIAL_EXTENT is not None:
        xmin, ymin, xmax, ymax = settings_as_json.pop('SPATIAL_EXTENT')
        settings_as_json['SPATIAL_EXTENT'] = { 'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax }

    return json.dumps(settings_as_json)
