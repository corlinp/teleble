import json, uuid
import os, os.path, shutil, sys, atexit

import markdown

from flask import current_app, Flask, jsonify, render_template, request, send_from_directory, redirect
from flask.views import MethodView


del_button_code = """<form action="/get_url/delete" id="{0}" removable="{0}">

        <div align="left" id="result_{0}">
<input type="submit" value="Delete" style="display: inline-block; background-color:#f0303f; padding:4px;" />
<a href="{2}" style="display: inline-block;">
<div style="display: inline-block;text-align:left; width:400px; border-top:1px solid #b0b0b0; padding:4px; background-color:#f0f0f8">{1}</div></a>
</div>
    </form>
    <!-- the result of the search will be rendered inside this div -->
    <div id="result"></div>
    <script>
        /* attach a submit handler to the form */
        $("#{0}").submit(function(event) {{

            /* stop form from submitting normally */
            event.preventDefault();

            /* get some values from elements on the page: */
            var $form = $(this),
                url = $form.attr('action');// + window.location.href;
				torem = $form.attr('removable');

            /* Send the data using post */
            var posting = $.post(url, {{
				s: torem
            }});

            /* Put the results in a div */
            posting.done(function(data) {{
                var content = $(data).find('#content');
                $("#result_{0}").empty().append(data);
            }});
        }});
    </script>"""


############# BEGIN STUFF I MOSTLY TOOK FROM FINEUPLOADER GITHUB #######################
######################## DONT WORRY IT'S UNDER MIT LICENSE #########################

BASE_DIR = os.path.dirname(__file__)

MEDIA_ROOT = os.path.join(BASE_DIR, 'files')
#UPLOAD_DIRECTORY = os.path.join(MEDIA_ROOT, 'upload')
UPLOAD_DIRECTORY = 'files/upload/'
CHUNKS_DIRECTORY = os.path.join(MEDIA_ROOT, 'chunks')

app = Flask(__name__)
app.config.from_object(__name__)

# Utils
##################
def make_response(status=200, content=None):
    """ Construct a response to an upload request.
    Success is indicated by a status of 200 and { "success": true }
    contained in the content.
    Also, content-type is text/plain by default since IE9 and below chokes
    on application/json. For CORS environments and IE9 and below, the
    content-type needs to be text/html.
    """
    return current_app.response_class(json.dumps(content,
        indent=None if request.is_xhr else 2), mimetype='text/plain')


def validate(attrs):
    """ No-op function which will validate the client-side data.
    Werkzeug will throw an exception if you try to access an
    attribute that does not have a key for a MultiDict.
    """
    try:
        #print(attrs)
        #required_attributes = ('qquuid', 'qqfilename')
        #[attrs.get(k) for k,v in attrs.items()]
        return True
    except Exception as e:
        return False


def handle_delete(uuid):
    """ Handles a filesystem delete based on UUID."""
    location = os.path.join(app.config['UPLOAD_DIRECTORY'], uuid)
    print(uuid)
    print(location)
    shutil.rmtree(location)

def handle_upload(f, attrs, secretuuid):
    """ Handle a chunked or non-chunked upload.
    """
    chunked = False
    dest_folder = os.path.join(app.config['UPLOAD_DIRECTORY'], secretuuid)
    dest = os.path.join(dest_folder, attrs['qqfilename'])

    # Chunked
    if 'qqtotalparts' in attrs and int(attrs['qqtotalparts']) > 1:
        chunked = True
        dest_folder = os.path.join(app.config['CHUNKS_DIRECTORY'], secretuuid)
        dest = os.path.join(dest_folder, attrs['qqfilename'], str(attrs['qqpartindex']))

    save_upload(f, dest)

    if chunked and (int(attrs['qqtotalparts']) - 1 == int(attrs['qqpartindex'])):
        combine_chunks(attrs['qqtotalparts'],
            attrs['qqtotalfilesize'],
            source_folder=os.path.dirname(dest),
            dest=os.path.join(app.config['UPLOAD_DIRECTORY'], secretuuid,
                attrs['qqfilename']))

        shutil.rmtree(os.path.dirname(os.path.dirname(dest)))


def save_upload(f, path):
    """ Save an upload.
    Uploads are stored in media/uploads
    """
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'wb+') as destination:
        destination.write(f.read())


class UploadAPI(MethodView):
    """ View which will handle all upload requests sent by Fine Uploader.
    Handles POST and DELETE requests.
    """

    def post(self):
        """A POST request. Validate the form and then handle the upload
        based ont the POSTed data. Does not handle extra parameters yet.
        """
        secretuuid = request.environ['HTTP_REFERER'].split('/')[-1]
        #request.form['qquuid'] = secretuuid

        if validate(request.form):
            handle_upload(request.files['qqfile'], request.form, secretuuid)
            return make_response(200, {"success": True})
        else:
            return make_response(400, {"error", "Invalid request"})

    def delete(self, uuid):
        """A DELETE request. If found, deletes a file with the corresponding
        UUID from the server's filesystem.
        """
        try:
            handle_delete(uuid)
            return make_response(200, {"success": True})
        except Exception as e:
            return make_response(400, {"success": False, "error": e})

def combine_chunks(total_parts, total_size, source_folder, dest):
    """ Combine a chunked file into a whole file again. Goes through each part
    , in order, and appends that part's bytes to another destination file.
    Chunks are stored in media/chunks
    Uploads are saved in media/uploads
    """
    if not os.path.exists(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))

    with open(dest, 'wb+') as destination:
        for i in range(int(total_parts)):
            part = os.path.join(source_folder, str(i))
            with open(part, 'rb') as source:
                destination.write(source.read())

######################### END GITHUB PLAGIARISM ##############################



############################## FILE VIEWING ENDPOINTS ##############################


@app.route("/<sid>/<fname>")
def get_file(sid, fname):
    if sid in guest_routes:
        sid = guest_routes[sid]
    return send_from_directory(os.path.join(UPLOAD_DIRECTORY, sid), fname)


def render_index(sid):
    fdir = os.path.join(UPLOAD_DIRECTORY, sid)
    if not os.path.exists(fdir):
        return render_template('index.html', files='', guest_links = '')

    out = '<h2>Files in this directory:</h2>'
    for file in os.listdir(fdir):
        out += '\n' + create_link('/'+sid+'/'+file, create_nice_label(file))

    glinks = ''
    if sid in reverse_guest_routes:
        for l, n in reverse_guest_routes[sid].items():
            #glinks += '<br>' + create_link(l, n)
            glinks += del_button_code.format(l, n, l)

    return render_template('index.html', files=out, guest_links=glinks)


def render_guest(sid, guest_sid):
    fdir = os.path.join(UPLOAD_DIRECTORY, sid)
    if not os.path.exists(fdir):
        return render_template('index.html', files='')

    out = '<h2>Files in this directory:</h2>'
    for file in os.listdir(fdir):
        out += '\n' + create_link('/'+guest_sid+'/'+file, create_nice_label(file))
    return render_template('guest.html', files=out)

############################### TYPICAL ENDPOINTS ################################

guest_routes = {}
reverse_guest_routes = {}

acceptable_routes = set()


@app.route("/<sid>")
def index(sid):
    print(guest_routes)
    if sid in guest_routes:
        return render_guest(guest_routes[sid], sid)
    if sid in acceptable_routes:
        return render_index(sid)
    elif os.path.exists('static/'+sid):
        return send_from_directory('static', sid)
    else:
        return render_template('404.html'), 404


@app.route("/")
def default():
    sid = str(uuid.uuid4())
    acceptable_routes.add(sid)
    return redirect("/" + sid, code=302)


@app.route("/get_url/delete", methods=['POST'])
def delete_guest():
    sid = request.environ['HTTP_REFERER'].split('/')[-1]
    guest_sid = request.form['s']
    del guest_routes[guest_sid]
    del reverse_guest_routes[sid][guest_sid]
    save_routes()
    return 'deleted'


@app.route("/get_url/guest", methods=['POST'])
def get_guest():
    sid = request.environ['HTTP_REFERER'].split('/')[-1]
    name = request.form['s']
    if name is None or len(name) < 1:
        name = "Guest Link"
    # Make a guest alias
    guest_id = str(uuid.uuid4())
    guest_routes[guest_id] = sid
    if sid not in reverse_guest_routes:
        reverse_guest_routes[sid] = {}

    reverse_guest_routes[sid][guest_id] = name

    save_routes()
    link = create_link(request.environ['HTTP_ORIGIN'] + '/' + guest_id, name)
    return del_button_code.format(guest_id, name, request.environ['HTTP_ORIGIN'] + '/' + guest_id)


@app.route("/doc")
def docs():
    """
    Automatically renders the README.md into /doc
    """
    with open('README.md', 'r') as content_file:
        content = content_file.read()
    html = markdown.markdown(content)
    return render_template("doc.html", title="Teleble API documentation", body=html)


def create_link(url, title):
    return '<a href="%s">%s</a>'%(url, title)


def create_nice_label(text):
    return '<div style="text-align:left; border-top:1px solid #b0b0b0; padding:4px; background-color:#f0f0f8">%s</div>' % text


upload_view = UploadAPI.as_view('upload_view')
app.add_url_rule('/uploads', view_func=upload_view, methods=['POST', 'GET', 'PUT', ])
app.add_url_rule('/uploads/<uuid>', view_func=upload_view, methods=['DELETE'])


def save_routes():
    outobj = {'guest_routes': guest_routes, 'reverse_guest_routes': reverse_guest_routes}
    print(outobj)
    with open("current_state.json", "w") as outfile:
        json.dump(outobj, outfile)

def open_routes():
    try:
        with open('current_state.json') as json_data:
            data = json.load(json_data)
            guest_routes.update(data['guest_routes'])
            reverse_guest_routes.update(data['reverse_guest_routes'])
    except:
        pass

# Main
##################
def main():
    # Add the existing folders to the acceptable routes
    open_routes()
    atexit.register(save_routes)
    acceptable_routes.update([name for name in os.listdir(UPLOAD_DIRECTORY) if os.path.isdir(UPLOAD_DIRECTORY+name)])
    app.run(host='0.0.0.0', port=80)
    return 0

if __name__ == '__main__':
    status = main()
    save_routes()
    sys.exit(status)

