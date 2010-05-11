import re

from django.utils.html import escape
from django.http import get_host

from forum.authentication.base import AuthenticationConsumer, InvalidAuthentication
import settings

from openid.yadis import xri
from openid.consumer.consumer import Consumer, SUCCESS, CANCEL, FAILURE, SETUP_NEEDED
from openid.consumer.discover import DiscoveryFailure
from openid.extensions.sreg import SRegRequest, SRegResponse
from openid.extensions.ax import FetchRequest as AXFetchRequest, AttrInfo, FetchResponse as AXFetchResponse
from django.utils.translation import ugettext as _

from store import OsqaOpenIDStore

class OpenIdAbstractAuthConsumer(AuthenticationConsumer):

    dataype2ax_schema = {
        #'username': 'http://axschema.org/namePerson/friendly',
        'email': 'http://axschema.org/contact/email',
        #'web': 'http://axschema.org/contact/web/default',
        #'firstname': 'http://axschema.org/namePerson/first',
        #'lastname': 'http://axschema.org/namePerson/last',
        #'birthdate': 'http://axschema.org/birthDate',
    }

    def get_user_url(self, request):
        try:
            return request.POST['openid_identifier']
        except:
            raise NotImplementedError()

    def prepare_authentication_request(self, request, redirect_to):
        if not redirect_to.startswith('http://') or redirect_to.startswith('https://'):
		    redirect_to =  get_url_host(request) + redirect_to

        user_url = self.get_user_url(request)

        if xri.identifierScheme(user_url) == 'XRI' and getattr(
            settings, 'OPENID_DISALLOW_INAMES', False
        ):
            raise InvalidAuthentication('i-names are not supported')

        consumer = Consumer(request.session, OsqaOpenIDStore())

        try:
            auth_request = consumer.begin(user_url)
        except DiscoveryFailure:
            raise InvalidAuthentication(_('Sorry, but your input is not a valid OpenId'))

        #sreg = getattr(settings, 'OPENID_SREG', False)

        #if sreg:
        #    s = SRegRequest()
        #    for sarg in sreg:
        #        if sarg.lower().lstrip() == "policy_url":
        #            s.policy_url = sreg[sarg]
        #        else:
        #            for v in sreg[sarg].split(','):
        #                s.requestField(field_name=v.lower().lstrip(), required=(sarg.lower().lstrip() == "required"))
        #    auth_request.addExtension(s)

        #auth_request.addExtension(SRegRequest(required=['email']))

        if request.session.get('force_email_request', True):
            axr = AXFetchRequest()
            for data_type, schema in self.dataype2ax_schema.items():
                if isinstance(schema, tuple):
                    axr.add(AttrInfo(schema[0], 1, True, schema[1]))
                else:
                    axr.add(AttrInfo(schema, 1, True, data_type))

            auth_request.addExtension(axr)

        trust_root = getattr(
            settings, 'OPENID_TRUST_ROOT', get_url_host(request) + '/'
        )

        return auth_request.redirectURL(trust_root, redirect_to)

    def process_authentication_request(self, request):
        consumer = Consumer(request.session, OsqaOpenIDStore())

        query_dict = dict([
            (k.encode('utf8'), v.encode('utf8')) for k, v in request.GET.items()
        ])

        #for i in query_dict.items():
            #print "%s : %s" % i

        url = get_url_host(request) + request.path
        openid_response = consumer.complete(query_dict, url)

        if openid_response.status == SUCCESS:
            if request.session.get('force_email_request', True):
                try:
                    ax = AXFetchResponse.fromSuccessResponse(openid_response)

                    axargs = ax.getExtensionArgs()

                    ax_schema2data_type = dict([(s, t) for t, s in self.dataype2ax_schema.items()])

                    available_types = dict([
                        (ax_schema2data_type[s], re.sub('^type\.', '', n))
                        for n, s in axargs.items() if s in ax_schema2data_type
                    ])

                    available_data = dict([
                        (t, axargs["value.%s.1" % s]) for t, s in available_types.items()
                    ])
                    
                    request.session['auth_consumer_data'] = {
                        'email': available_data.get('email', None),
                    }

                except Exception, e:
                    pass
                    #import sys, traceback
                    #traceback.print_exc(file=sys.stdout)

            return request.GET['openid.identity']
        elif openid_response.status == CANCEL:
            raise InvalidAuthentication(_('The OpenId authentication request was canceled'))
        elif openid_response.status == FAILURE:
            raise InvalidAuthentication(_('The OpenId authentication failed: ') + openid_response.message)
        elif openid_response.status == SETUP_NEEDED:
            raise InvalidAuthentication(_('Setup needed'))
        else:
            raise InvalidAuthentication(_('The OpenId authentication failed with an unknown status: ') + openid_response.status)

    def get_user_data(self, key):
        return {}

def get_url_host(request):
    if request.is_secure():
        protocol = 'https'
    else:
        protocol = 'http'
    host = escape(get_host(request))
    return '%s://%s' % (protocol, host)

def get_full_url(request):
    return get_url_host(request) + request.get_full_path()