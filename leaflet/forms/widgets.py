# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms.widgets import Widget, Select
from django.template import loader, Template, Context
try:
    from django.contrib.gis.forms.widgets import BaseGeometryWidget
except ImportError:
    from .backport import BaseGeometryWidget

from leaflet import PLUGINS, PLUGIN_FORMS


class LeafletWidget(BaseGeometryWidget):
    template_name = 'leaflet/widget.html'
    map_srid = 4326
    map_width = None
    map_height = None
    modifiable = True
    supports_3d = False
    include_media = False

    @property
    def media(self):
        if not self.include_media:
            return forms.Media()

        # We assume that including media for widget means there is
        # no Leaflet at all in the page.
        js = ['leaflet/leaflet.js'] + PLUGINS[PLUGIN_FORMS]['js']
        css = ['leaflet/leaflet.css'] + PLUGINS[PLUGIN_FORMS]['css']
        return forms.Media(js=js, css={'screen': css})

    def serialize(self, value):
        return value.geojson if value else ''

    def render(self, name, value, attrs=None):
        assert self.map_srid == 4326, 'Leaflet vectors should be decimal degrees.'

        # Retrieve params from Field init (if any)
        self.geom_type = self.attrs.get('geom_type', self.geom_type)

        attrs = attrs or {}

        # In BaseGeometryWidget, geom_type is set using gdal, and fails with generic.
        # See https://code.djangoproject.com/ticket/21021
        if self.geom_type == 'GEOMETRY':
            attrs['geom_type'] = 'Geometry'

        map_id = attrs.get('id', name).replace('-', '_')  # JS-safe
        attrs.update(id_map=map_id + '_map',
                     id_map_callback=map_id + '_map_callback',
                     modifiable=self.modifiable,
                     geometry_field_class=attrs.get('geometry_field_class', 'L.GeometryField'),
                     field_store_class=attrs.get('field_store_class', 'L.FieldStore'))
        return super(LeafletWidget, self).render(name, value, attrs)


class MapChooserWidget(Widget):
    # Name of the map widget template
    template_name = 'leaflet/map_chooser_widget.html'

    def __init__(self, attrs=None, allow_multi=True, choices=(), initial=()):

        super(MapChooserWidget, self).__init__(attrs)

        self.allow_multi = allow_multi
        self.choices = list(choices)
        self.initial = list(initial)

    def value_from_datadict(self, data, files, name):
        # Get string from POST array
        value = data.get(name, None)

        if value:
            # Turn string into list of ids and return them
            ids = value.split(',')
            return ids

        # No countries were submitted, return None
        return value

    def render(self, name, value, attrs=None, choices=(), initial=()):
        for shape in self.choices.queryset:
            shape.geometry.transform(4326)

        geojson = {}

        if(self.choices):
            #Create JSON for every object
            geojson_tpl = """{ "type": "FeatureCollection",
            "features": [
            {% for ob in objects %}
                { "type": "Feature",
                    "geometry": {{ob.geometry.json|safe}},
                    "properties": {
                        "id": "{{ob.pk}}",
                        "name": "{{ ob }}"
                    }
                }{% if not forloop.last %},{% endif %}
            {% endfor %}
            ]
             }"""
            t = Template(geojson_tpl)
            geojson = t.render(Context({'objects':self.choices.queryset}))

            #remove newlines to avoid problems with multi-line strings
            geojson = geojson.replace('\n', ' \\\n')
        
        init_choices = {}
        if self.initial:
            init_tpl = """[{% for ob in objects%}'{{ob.pk}}'{% if not forloop.last %},{% endif %}{% endfor %}]"""
            t2 = Template(init_tpl)
            init_choices = t2.render(Context({'objects':self.initial}))

        context = self.build_attrs(
            attrs,
            name=name,
            allow_multi=self.allow_multi,
            geofeatures=geojson,
            initial_choices=init_choices
        )
        return loader.render_to_string(self.template_name, context)
