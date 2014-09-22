from flask import Flask, render_template, session, request,\
        redirect, url_for, make_response

from requests_oauthlib import OAuth1
from ims_lti_py import ToolConsumer, ToolConfig,\
        OutcomeRequest, OutcomeResponse

import collections

import urlparse

from my_tool_consumer import MyToolConsumer

import hashlib
import requests
import logging

import json

app = Flask(__name__)
app.secret_key = '\xb9\xf8\x82\xa9\xf4\xdcC\xf4L<\x9c\xf1\x87\xa6\x7fI\xb9\x04\x9d\xed\xb0\xf2\x83\x0c'

# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
try:
    import http.client as http_client
except ImportError:
    # Python 2
    import httplib as http_client
http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

#launch_url = "https://sandbox.turnitin.com/api/lti/1p0/assignment"
launch_url = None
consumer_key = "69440"
#consumer_key = "59439"
consumer_secret = "12345678"


rtp_data = {"rtp": {"no": "data", "launch_url": "/api/lti/1p0/assignment"}}
otp_data = {"otp": {"no": "data", "launch_url": "/api/lti/1p0/assignment"}}
outcome = "No grade passed back yet"

default_launch_data = collections.OrderedDict([
    ("method","POST"),
    ("tool_name", "Flask LTI Tool"),
    ("launch_url","http://dev5.oak:5863/api/lti/1p0/assignment"),
    ("oauth_version", "1.0"),
    ("oauth_consumer_key", "59439"),
    ("consumer_secret", "12345678"),
    ("oauth_signature_method", "HMAC-SHA1"),
    ("lti_message_type", "basic-lti-launch-request"),
    ("lti_version", "LTI-1p0"),
    ("resource_link_id", "88391-e1919-bb3456"),
    ("resource_link_title", "My Weekly Wiki"),
    ("resource_link_description", "hello"),
    ("user_id", "0ae836b9-7fc9-4060-006f-27b2066ac545"),
    ("user_image", None),
    ("custom_startdate", None),
    ("custom_duedate", None),
    ("custom_feedbackreleasedate", None),
    ("custom_maxpoints", None),
    ("roles", "Instructor"),
    ("lis_person_name_given", "Jane"),
    ("lis_person_name_family", "Public"),
    ("lis_person_name_full", "Jane Q. Public"),
    ("lis_person_contact_email_primary", "user@school.edu"),
    ("lis_outcome_service_url", "outcomes_service"),
    ("lis_result_sourcedid", None),
    ("lis_person_sourcedid", None),
    ("lis_course_offering_sourcedid", None),
    ("lis_course_section_sourcedid", None),
    ("context_id", "8213060-006f-27b2066ac545"),
    ("context_type", "CourseSection"),
    ("context_title", "Design of Personal Environments"),
    ("context_label", "SI182"),
    ("launch_presentation_locale", "en-US"),
    ("launch_presentation_document_target", "iframe"),
    ("launch_presentation_css_url", None),
    ("launch_presentation_width", "320"),
    ("launch_presentation_height", "240"),
    ("launch_presentation_return_url", "http://lmsng.example.com/portal/123/page/988/"),
    ("tool_consumer_info_product_family_code", "desire2learn"),
    ("tool_consumer_info_version", "9.2.4"),
    ("tool_consumer_instance_guid", "lmsng.school.edu"),
    ("tool_consumer_instance_name", "SchoolU"),
    ("tool_consumer_instance_description", "University of School (LMSng)"),
    ("tool_consumer_instance_url", None),
    ("tool_consumer_instance_contact_email", "System.Admin@school.edu"),
    ("ext_resource_tool_placement_url", "resource_tool_placement"),
    ("ext_outcomes_tool_placement_url", "outcomes_tool_placement"),
    ("custom_studentlist", None),
    ("custom_submission_url", None),
    ("custom_submission_title", None),
    ("custom_xmlresponse", None)])

@app.route('/LTI', methods = ['GET'])
def LTI():
    return render_template('index.html')


@app.route('/tool_config', methods = ['GET'])
def tool_config():
    if request.args.get('launch_url'):
        global launch_url
        launch_url = request.args.get('launch_url')

    parsed_url = urlparse.urlparse(request.url)
    if parsed_url.path[-1] == '/':
        basepath = urlparse.urlunparse(
            urlparse.ParseResult(parsed_url.scheme,
                                 parsed_url.netloc,
                                 parsed_url.path,
                                 "", "", ""))
    else:
        basepath = urlparse.urlunparse(
            urlparse.ParseResult(parsed_url.scheme,
                                 parsed_url.netloc,
                                 parsed_url.path[:-len(parsed_url.path.split("/")[-1])],
                                 "", "", ""))

    launch_data = default_launch_data.copy()

    if launch_url != None:
        launch_data["launch_url"] = launch_url

    launch_data["ext_resource_tool_placement_url"] = basepath + launch_data["ext_resource_tool_placement_url"]
    launch_data["ext_outcomes_tool_placement_url"] = basepath + launch_data["ext_outcomes_tool_placement_url"]
    launch_data["lis_outcome_service_url"] = basepath + launch_data["lis_outcome_service_url"]


    return render_template('tool_config.html',
                           message = request.form.get('message'),
                           default_launch_data = launch_data,
                           consumer_key = consumer_key,
                           consumer_secret = consumer_secret)

@app.route('/tool_launch', methods = ['POST'])
def tool_launch():
    # Parse form and ensure necessary parameters are included
    for param in ['tool_name', 'launch_url', 'oauth_consumer_key',
                  'consumer_secret', 'roles']:
        if request.form.get(param) == None:
            return redirect(url_for('tool_config?message=Please%20set%20all%values'))


    params = {}
    custom_params = {}
    for k, v in request.form.items():
        if v != "":
            if k[:4] == "ext_" or k[:7] == "custom_":
                custom_params[k] = v
            elif k != "consumer_secret":
                params[k] = v


    if (request.form.get("user_id") != None):
        hash = hashlib.md5()
        hash.update(request.form.get("user_id"))
        params["lis_result_sourcedid"] = hash.hexdigest()

    # Create a new tool configuration
    config = ToolConfig(title = request.form.get('tool_name'),
                        launch_url = request.form.get('launch_url'),
                        custom_params = custom_params)


    # Create tool consumer! Yay LTI!
    consumer = MyToolConsumer(request.form.get('oauth_consumer_key'),
                              request.form.get('consumer_secret'),
                              params = params)

    consumer.set_config(config)

    global consumer_key
    consumer_key = request.form.get('oauth_consumer_key')
    global consumer_secret
    consumer_secret = request.form.get('consumer_secret')
    global launch_url
    launch_url = request.form.get('launch_url')
    

    autolaunch = True if request.form.get('autolaunch') else False

    return render_template('tool_launch.html',
                           autolaunch = autolaunch,
                           launch_data = consumer.generate_launch_data(),
                           launch_url = consumer.launch_url)


@app.route("/launch_test")
def launch():
    url = 'http://dev5.oak:5863/api/lti/1p0/assignment'
    payload = { "lti_message_type":"basic-lti-launch-request",

                'lti_version': 'LTI-1p0',
                'resource_link_id': '88391-e1919-bb3456',
                'user_id': '0ae836b9-7fc9-4060-006f-27b2066ac545',
                'roles': 'Instructor',
                'lis_person_name_given': 'Jane',
                'lis_person_name_family': 'Public',
                'lis_person_name_full': 'Jane Q. Public',
                'lis_person_contact_email_primary': 'user@school.edu',
                'context_id': '8213060-006f-27b2066ac545',
                'context_type': 'CourseSection',
                'context_title': 'Design of Personal Environments',
                'context_label': 'SI182',
                'tool_consumer_info_version': '9.2.4',
                'tool_consumer_instance_guid': 'lmsng.school.edu',
                'tool_consumer_instance_name': 'SchoolU',
                'tool_consumer_instance_description': 'University of School (LMSng)',
                'tool_consumer_instance_contact_email': 'System.Admin@school.edu'}
    # { "lti_message_type":"basic-lti-launch-request",
                # 'resource_link_id': 'thisistotallyunique',
                # 'lti_version': 'LTI-1p0',
                # 'roles': 'Instructor',
                # 'lis_person_contact_email_primary': 'hello@example.org',
                # 'context_id': 'bestcourseever',
                # 'context_type': 'CourseSection'}

    auth = OAuth1(consumer_key,
                  consumer_secret,
                  signature_type='query')
    req = requests.post(url,
                        data = payload,
                        auth = auth)

    return req.content

@app.route('/tool_return', methods = ['GET'])
def tool_return():
    error_message = request.args.get('lti_errormsg')
    message = request.args.get('lti_msg')
    return render_template('tool_return',
            message =  message,
            error_message = error_message)

@app.route("/resource_tool_placement", methods=['POST'])
def rtp():
    jsond = request.get_json()
    url = jsond[u'resource_tool_placement_url']

    auth = OAuth1(consumer_key,
                  consumer_secret,
                  signature_type='body')
    response = requests.post(url,
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                        auth = auth)
    global rtp_data
    rtp_data =json.loads(response.content)
    return "rtp"

@app.route("/resource_tool_placement", methods=['GET'])
def view_rtp():
    return render_template('tp.html',
                           title = "Resource tool placement urls",
                           tp_data = rtp_data)

@app.route("/outcomes_tool_placement", methods=['POST'])
def otp():
    jsond = request.get_json()
    url = jsond[u'outcomes_tool_placement_url']

    auth = OAuth1(consumer_key,
                  consumer_secret,
                  signature_type='query')
    response = requests.post(url,
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'},
                        auth = auth)
    global otp_data
    otp_data =json.loads(response.content)
    return "otp"

@app.route("/outcomes_tool_placement", methods=['GET'])
def view_otp():
    return render_template('tp.html',
                           title = "Outcomes tool placement urls",
                           tp_data = otp_data)


@app.route('/outcomes_service', methods = ['POST'])
def grade_passback():
    outcome_request = OutcomeRequest.from_post_request(request)
    sourcedid = outcome_request.lis_result_sourcedid
    consumer = ToolConsumer('test', 'secret')

    print "outcomes service url triggered"
    #    if consumer.is_valid_request(request):
    if True:

        # TODO: Check oauth timestamp
        # TODO: Check oauth nonce

        response = OutcomeResponse()
        response.message_ref_identifier = outcome_request.message_identifier
        response.operation = outcome_request.operation
        response.code_major = 'success'
        response.severity = 'status'

        if outcome_request.is_replace_request():
            response.description = 'Your old score of 0 has been replaced with %s' %(outcome_request.score)
            global outcome
            outcome = outcome_request.score
        elif outcome_request.is_read_request():
            response.description = 'Your score is 50'
            response.score = 50
        elif outcome_request.is_delete_request():
            response.description = 'Your score has been cleared'
        else:
            response.code_major = 'unsupported'
            response.severity = 'status'
            response.description = '%s is not supported' %(outcome_request.operation)
        return response.generate_response_xml()
    else:
        throw_oauth_error()


@app.route('/outcomes_service', methods = ['GET'])
def view_grade_passback():
    return outcome

@app.route('/submission', methods = ['GET'])
def send_submission():
    return "test test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test testtest test test"



def throw_oauth_error():
    resp = make_response('Not authorized', 401)
    resp.headers['WWW-Authenticate'] = 'OAuth realm="%s"' %(request.host)
    return resp

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port = 80)
