from ims_lti_py import ToolConsumer, ToolConfig,\
        OutcomeRequest, OutcomeResponse

from ims_lti_py.utils import InvalidLTIConfigError, generate_identifier
from urllib2 import urlparse, unquote

import oauth2
import time

import logging

import json

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

from collections import defaultdict

# List of the standard launch parameters for an LTI launch
LAUNCH_DATA_PARAMETERS = [
    'context_id',
    'context_label',
    'context_title',
    'context_type',
    'launch_presentation_css_url',
    'launch_presentation_document_target',
    'launch_presentation_height',
    'launch_presentation_locale',
    'launch_presentation_return_url',
    'launch_presentation_width',
    'lis_course_section_sourcedid',
    'lis_outcome_service_url',
    'lis_person_contact_email_primary',
    'lis_person_name_family',
    'lis_person_name_full',
    'lis_person_name_given',
    'lis_person_sourcedid',
    'lis_result_sourcedid',
    'lti_message_type',
    'lti_version',
    'oauth_callback',
    'oauth_consumer_key',
    'oauth_nonce',
    'oauth_signature',
    'oauth_signature_method',
    'oauth_timestamp',
    'oauth_version',
    'resource_link_description',
    'resource_link_id',
    'resource_link_title',
    'roles',
    'tool_consumer_info_product_family_code',
    'tool_consumer_info_version',
    'tool_consumer_instance_contact_email',
    'tool_consumer_instance_description',
    'tool_consumer_instance_guid',
    'tool_consumer_instance_name',
    'tool_consumer_instance_url',
    'user_id',
    'user_image'
]



class MyToolConsumer(ToolConsumer):


    def process_params(self, params):
        '''
        Populates the launch data from a dictionary. Only cares about keys in
        the LAUNCH_DATA_PARAMETERS list, or that start with 'custom_' or
        'ext_'.
        '''
        for key, val in params.items():
            if key in LAUNCH_DATA_PARAMETERS and val != 'None':
                setattr(self, key, unicode(val))
            elif 'custom_' in key:
                self.custom_params[key] = unicode(val)
            elif 'ext_' in key:
                self.ext_params[key] = unicode(val)

    def set_config(self, config):
        '''
        Set launch data from a ToolConfig.
        '''
        self.custom_params.update(config.custom_params)
        if self.launch_url == None:
            self.launch_url = config.launch_url

    def generate_launch_data(self):
        # Validate params
        if not self.has_required_params():
            raise InvalidLTIConfigError('ToolConsumer does not have all required attributes: consumer_key = %s, consumer_secret = %s, resource_link_id = %s, launch_url = %s' %(self.consumer_key, self.consumer_secret, self.resource_link_id, self.launch_url))

        params = self.to_params()
        params['lti_version'] = 'LTI-1p0'
        params['lti_message_type'] = 'basic-lti-launch-request'

        # Get new OAuth consumer
        consumer = oauth2.Consumer(key = self.consumer_key,\
                secret = self.consumer_secret)

        params.update({
            'oauth_nonce': str(generate_identifier()),
            'oauth_timestamp': str(int(time.time())),
            'oauth_consumer_key': consumer.key
        })

        uri = urlparse.urlparse(self.launch_url)

        cleaned_params = {}
        for key in params:
            if params[key] != None:
                cleaned_params[key] = params[key]

        request = oauth2.Request(method = 'POST',
            url = self.launch_url,
            parameters = cleaned_params)

        signature_method = oauth2.SignatureMethod_HMAC_SHA1()
        request.is_form_encoded = True
        request.sign_request(signature_method, consumer, None)

        # Request was made by an HTML form in the user's browser.
        # Return the dict of post parameters ready for embedding
        # in an html view.
        return_params = {}
        for key in request:
            if request[key] == None:
                return_params[key] = None
            elif isinstance(request[key], list):
                return_params[key] = request.get_parameter(key)
            else:
                return_params[key] = unquote(request.get_parameter(key))
        return return_params
