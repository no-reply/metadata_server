from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from manifests import huam
from manifests import mets
from manifests import mods
from manifests import models
from manifests import ams
from os import environ
import json
import urllib2
import requests
import webclient

# Create your views here.

METS_DRS_URL = environ.get("METS_DRS_URL", "http://fds.lib.harvard.edu/fds/deliver/")
METS_API_URL = environ.get("METS_API_URL", "http://pds.lib.harvard.edu/pds/get/")
MODS_DRS_URL = "http://webservices.lib.harvard.edu/rest/MODS/"
HUAM_API_URL = "http://api.harvardartmuseums.org/object/"
HUAM_API_KEY = environ["HUAM_API_KEY"]
COOKIE_DOMAIN = environ.get("COOKIE_DOMAIN", ".hul.harvard.edu")
PDS_VIEW_URL = environ.get("PDS_VIEW_URL", "http://pds.lib.harvard.edu/pds/view/")

sources = {"drs": "mets", "via": "mods", "hollis": "mods", "huam" : "huam"}

def index(request, source=None):
    source = source if source else "drs"
    document_ids = models.get_all_manifest_ids_with_type(source)
    host = request.META['HTTP_HOST']
    cookie = request.COOKIES.get('hulaccess', None)
    manifests = ({"uri": "/manifests/view/%s:%s" % (source, d_id), "title": (models.get_manifest_title(d_id, source) or "Untitled Item") + " (id: %s)" % d_id} for d_id in document_ids)
    return render(request, 'manifests/index.html', {'manifests': manifests})

# view any number of MODS, METS, or HUAM objects
def view(request, view_type, document_id):
    doc_ids = document_id.split(';')
    manifests = {}
    manifests_json = []
    ams_cookie = None

    def layout_string(n):
        """Return nxn formatted string of y, x arrangement for windows"""
        return "{0}x{1}".format((n / 2) + (n % 2), 1 if n == 1 else 2)

    if 'hulaccess' in request.COOKIES:
        ams_cookie = request.COOKIES['hulaccess']
    host = request.META['HTTP_HOST']
    for doc_id in doc_ids:
        parts = doc_id.split(':')
        if len(parts) != 2:
            continue # not a valid id, don't display
        source = parts[0]
        id = parts[1]
        # drs: check AMS to see if this is a restricted obj
        # TODO:  move this check into get_manifest() for hollis
        if 'drs' == source:
            ams_redirect = ams.getAMSredirectUrl(request.COOKIES, id)
            if ams_redirect:
                return HttpResponseRedirect(ams_redirect)

        #print source, id
        (success, response, real_id, real_source) = get_manifest(id, source, False, host, ams_cookie)
        if success:
            title = models.get_manifest_title(real_id, real_source)
            uri = "http://%s/manifests/%s:%s" % (host,real_source,real_id)
            manifests[uri] = title
            manifests_json.append(json.dumps({ "manifestUri": uri,
                                               "location": "Harvard University",
                                               "title": title}))

    if len(manifests) > 0:
        view_locals = {'manifests' : manifests,
                       'manifests_json': manifests_json,
                       'num_manifests': len(manifests),
                       'loadedUri': manifests.keys()[0],
                       'pds_view_url': PDS_VIEW_URL,
                       'layout_string': layout_string(len(manifests)),
                   }
        # Check if its an experimental/dev Mirador codebase, otherwise use production
        if (view_type == "view-dev"):
            return render(request, 'manifests/dev.html', view_locals)
        else:
            return render(request, 'manifests/manifest.html', view_locals)
    else:
        return HttpResponse("The requested document ID(s) %s could not be displayed" % document_id, status=404) # 404 HttpResponse object

# Demo URL - a canned list of manifests
def demo(request):
    return render(request, 'manifests/demo.html', {'pds_view_url' : PDS_VIEW_URL})

# Returns a IIIF manifest of a METS, MODS or HUAM JSON object
# Checks if DB has it, otherwise creates it
def manifest(request, document_id):
    parts = document_id.split(":")
    host = request.META['HTTP_HOST']
    cookie = request.COOKIES.get('hulaccess', None)
    if len(parts) != 2:
        return HttpResponse("Invalid document ID. Format: [data source]:[ID]", status=404)
    source = parts[0]
    id = parts[1]
    (success, response_doc, real_id, real_source) = get_manifest(id, source, False, host, cookie)
    if success:
        response = HttpResponse(response_doc)
        add_headers(response)
        return response
    else:
        return response_doc # 404 HttpResponse

# Delete any document from db
def delete(request, document_id):
    # Check if manifest exists
    parts = document_id.split(":")
    if len(parts) != 2:
        return HttpResponse("Invalid document ID. Format: [data source]:[ID]", status=404)
    source = parts[0]
    id = parts[1]
    has_manifest = models.manifest_exists(id, source)

    if has_manifest:
        models.delete_manifest(id, source)
        return HttpResponse("Document ID %s has been deleted" % document_id)
    else:
        return HttpResponse("Document ID %s does not exist in the database" % document_id, status=404)

# Force refresh a single document
# Pull METS, MODS or HUAM JSON, rerun conversion script, and store in db
def refresh(request, document_id):
    parts = document_id.split(":")
    host = request.META['HTTP_HOST']
    cookie = request.COOKIES.get('hulaccess', None)
    if len(parts) != 2:
        return HttpResponse("Invalid document ID. Format: [data source]:[ID]", status=404)
    source = parts[0]
    id = parts[1]
    (success, response_doc, real_id, real_source) = get_manifest(id, source, True, host, cookie)

    if success:
        response = HttpResponse(response_doc)
        add_headers(response)
        return response
    else:
        return response_doc # This is actually the 404 HttpResponse, so return and end the function

# Force refresh all records from a single source
# WARNING: this could take a long time
# Pull all METS, MODS or HUAM JSON, rerun conversion script, and store in db
def refresh_by_source(request, source):
    document_ids = models.get_all_manifest_ids_with_type(source)
    counter = 0
    host = request.META['HTTP_HOST']
    cookie = request.COOKIES.get('hulaccess', None)
    for id in document_ids:
        (success, response_doc, real_id, real_source) = get_manifest(id, source, True,  host, cookie)
        if success:
            counter = counter + 1

    response = HttpResponse("Refreshed %s out of %s total documents in %s" % (counter, len(document_ids), source))
    return response

# this is a hack because the javascript uses relative paths for the PNG files, and Django creates the incorrect URL for them
# Need to find a better and more permanent solution
def get_image(request, view_type, filename):
    if view_type == "view-dev":
        return HttpResponseRedirect("/static/manifests/dev/images/%s" % filename)
    elif view_type == "view-annotator":
        return HttpResponseRedirect("/static/manifests/annotator/images/%s" % filename)
    elif view_type == "view-m1":
        return HttpResponseRedirect("/static/manifests/m1/images/%s" % filename)
    elif view_type == "view-m2":
        return HttpResponseRedirect("/static/manifests/m2/images/%s" % filename)
    else:
        return HttpResponseRedirect("/static/manifests/prod/images/%s" % filename)

def clean_url(request, view_type):
    cleaned = "/static" + request.path.replace("//","/").replace("view-","")
    return HttpResponseRedirect(cleaned)

## HELPER FUNCTIONS ##
# Gets METS XML from DRS
def get_mets(document_id, source, cookie=None):
    mets_url = METS_DRS_URL+document_id
    try:
        #response = urllib2.urlopen(mets_url)
        response = webclient.get(mets_url, cookie)
    except urllib2.HTTPError, err:
        if err.code == 500 or err.code == 404:
            # document does not exist in DRS, might need to add more error codes
            # TODO: FDS often seems to fail on its first request...maybe try again?
            return (False, HttpResponse("The document ID %s does not exist" % document_id, status=404))

    response_doc = response.read()
    return (True, response_doc)

# Gets MODS XML from Presto API
def get_mods(document_id, source, cookie=None):
    mods_url = MODS_DRS_URL+source+"/"+document_id
    #print mods_url
    try:
        #response = urllib2.urlopen(mods_url)
        response = webclient.get(mods_url, cookie)
    except urllib2.HTTPError, err:
        if err.code == 500 or err.code == 403: ## TODO
            # document does not exist in DRS
            return (False, HttpResponse("The document ID %s does not exist" % document_id, status=404))

    mods = response.read()
    return (True, mods)

# Gets HUAM JSON from HUAM API
def get_huam(document_id, source):
    huam_url = HUAM_API_URL+document_id+"?apikey="+HUAM_API_KEY
    try:
        response = urllib2.urlopen(huam_url)
    except urllib2.HTTPError, err:
        if err.code == 500 or err.code == 403: ## TODO
            # document does not exist in DRS
            return (False, HttpResponse("The document ID %s does not exist" % document_id, status=404))

    huam = response.read()
    return (True, huam)

# Adds headers to Response for returning JSON that other Mirador instances can access
def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response

# Uses other helper methods to create JSON
def get_manifest(document_id, source, force_refresh, host, cookie=None):
    # Check if manifest exists
    has_manifest = models.manifest_exists(document_id, source)

    ## TODO: add last modified check

    if not has_manifest or force_refresh:
        # If not, get MODS, METS, or HUAM JSON
        data_type = sources[source]
        if data_type == "mods":
            ## TODO: check image types??
            (success, response) = get_mods(document_id, source, cookie)
        elif data_type == "mets":
            (success, response) = get_mets(document_id, source, cookie)
        elif data_type == "huam":
            (success, response) = get_huam(document_id, source)
        else:
            success = False
            response = HttpResponse("Invalid source type", status=404)

        if not success:
            return (success, response, document_id, source) # This is actually the 404 HttpResponse, so return and end the function

        # Convert to shared canvas model if successful
        if data_type == "mods":
            converted_json = mods.main(response, document_id, source, host, cookie)
            # check if this is, in fact, a PDS object masked as a hollis request
            # If so, get the manifest with the DRS METS ID and return that
            json_doc = json.loads(converted_json)
            if 'pds' in json_doc:
                id = json_doc['pds']
                return get_manifest(id, 'drs', False, host, cookie)
        elif data_type == "mets":
            converted_json = mets.main(response, document_id, source, host, cookie)
        elif data_type == "huam":
            converted_json = huam.main(response, document_id, source, host)
        else:
            pass
        # Store to elasticsearch
        models.add_or_update_manifest(document_id, converted_json, source)
        # Return the documet_id and source in case this is a hollis record
        # that also has METS/PDS
        return (success, converted_json, document_id, source)
    else:
        # return JSON from db
        json_doc = models.get_manifest(document_id, source)
        return (True, json.dumps(json_doc), document_id, source)
