from flask import Blueprint, request, jsonify, current_app
from modules.comparisons.frontend_queries import get_all_attribute_types, get_attribute_values, get_types
from routes.file_utils import fix_uri
from middleware.decorators import tofromHumanReadable

bp_ra_views = Blueprint('reactapp_views', __name__)


@tofromHumanReadable
def convert(q):
    """
    Used to convert the human-readable string back into a proper URI.
    """
    print 'ra_views call_get_attribute_values() convert(): ' + str(q)
    return q


@bp_ra_views.route('/api/v0/get_attribute_values/type/<path:attributetype>')
def call_get_attribute_values(attributetype):
    """
    Front-End API:
    Get all attribute values for a given attribute type.
    This is used to populate the 'Attributes' section of GroupsForm.
    """
    # workaround: Flask's path converter allows slashes, but only a SINGLE slash
    # this adds the second slash
    # also convert to a rdflib.URIRef object
    print 'call_get_attribute_values() attributetype:  ' + attributetype
    uri = fix_uri(attributetype)
    print 'call_get_attribute_values() uri: ' + str(uri)
    values = get_attribute_values(attributeTypeUri=uri)
    print 'call_get_attribute_values() values: ' + str(values)
    d = convert(values)
    return jsonify(d)
    # set_attribute_types = set(get_all_attribute_types())
    # set_object_types = get_types() # get types returns a set by default
    # return jsonify(list(set_attribute_types.union(set_object_types)))


@bp_ra_views.route('/api/v0/get_all_types')
def combine_types():
    """
    Returns all URIs that is either a attribute type or and object type.
    This is used to populate the 'Relations' section of GroupsForm.
    """
    set_attribute_types = set(get_all_attribute_types())
    set_object_types = get_types()  # get types returns a set by default
    l = list(set_attribute_types.union(set_object_types))
    d = convert(l)
    return jsonify(d)


@bp_ra_views.route('/api/v0/get_all_attribute_types')
def call_get_all_atribute_types():
    """
    Front-End API:
    Get all possible attribute types.
    This is used to populate the 'Targets' section of GroupsForm.
    """
    l = get_all_attribute_types()
    d = convert(l)
    return jsonify(d)
