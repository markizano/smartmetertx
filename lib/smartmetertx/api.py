import os
import json
import requests

from pprint import pformat
from kizano import getLogger
from smartmetertx.utils import getConfig

# BEGIN: #StackOverflow
# @Source: https://stackoverflow.com/a/16630836/2769671
# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
if os.getenv('DEBUG', False):
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

    requests_log = getLogger("requests.urllib3", 10)
    requests_log.propagate = True
# END: #StackOverflow

USE_HTTP2 = os.getenv('USE_HTTP2')
if USE_HTTP2:
    import collections.abc
    #hyper needs the four following aliases to be done manually.
    collections.Iterable = collections.abc.Iterable
    collections.Mapping = collections.abc.Mapping
    collections.MutableSet = collections.abc.MutableSet
    collections.MutableMapping = collections.abc.MutableMapping
    from hyper.contrib import HTTP20Adapter


# @markizano: Personal notes: I realize now that it's impossible to get this working with https://www.smartmetertexas.com
# They cast some very strange spells on the SSL certificates that prevents {requests.ssl} to ever verify them properly.
# The HTTP/2.0 negotiation also throws things off with SNI. I spent more time trying to decode this protocol than I did
# copying the module over from the credits in the README.md.
# Alas: It's not very clean as far as a purist is concerned, but it gets the job done. Unfortunately, this app is vulnerable
# to MITM attack =(
# This explains the why behind the condition of using HTTP2
class MeterReader:
    HOSTNAME = 'smartmetertexas.com'
    HOST = 'https://www.smartmetertexas.com' if USE_HTTP2 else 'https://smartmetertexas.com'
    USER_AGENT = 'Mozilla/5.0 (python3; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    TIMEOUT = 30

    def __init__(self, timeout=10):
        self.log = getLogger(__name__)
        self.logged_in = False
        self.session = requests.Session()
        if USE_HTTP2:
            self.session.mount('https://', HTTP20Adapter())
        self.timeout = timeout
        self.session.headers['Authority'] = MeterReader.HOSTNAME
        self.session.headers['Origin'] = MeterReader.HOST
        self.session.headers['Accept'] = 'application/json, text/plain, */*'
        self.session.headers['Accept-Language'] = 'en-US,en;q=0.9'
        self.session.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.session.headers['dnt'] = '1'
        self.session.headers['sec-ch-ua'] = '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"'
        self.session.headers['sec-ch-ua-mobile'] = '?0'
        self.session.headers['sec-ch-ua-platform'] = 'Linux'
        self.session.headers['sec-fetch-dest'] = 'empty'
        self.session.headers['sec-fetch-mode'] = 'cors'
        self.session.headers['sec-fetch-site'] = 'same-origin'
        self.session.headers['User-Agent'] = MeterReader.USER_AGENT

    def api_call(self, url, json):
        '''
        Generic API call that can be made to the site for JSON results back.
        @param url :string: Where to send POST request.
        @param json :object: Data to send to the server.
        @return :object: JSON response back or ERROR
        '''
        self.log.debug(f'MeterReader.api_call(url={url}, json={json})')
        try:
            return self.session.post(
                url=url,
                json=json,
                timeout=self.timeout,
                verify=False
            )
        except Exception as ex:
            self.log.error(repr(ex))
            raise ex

    def login(self, username, password):
        '''
        Make API call to login and acquire a session token.
        @param username :string: Username or email used to Login to the webpage.
        @param password :string: Password used to login.
        @return :string: The login token that will be used going forward.
        '''
        creds = {
            "username": username,
            "password": password
        }
        url = f"{MeterReader.HOST}/api/user/authenticate"
        r = self.api_call(url, json=creds)
        if r.status_code != 200:
            self.log.error("Login failed.")
            self.log.debug(pformat(r.headers.__dict__))
            self.log.debug(r.text)
            self.log.debug(self.session.cookies.__dict__)
            return False
        else:
            self.token = r.json()['token']
            self.log.info("Login successful!")
            self.log.debug(f"Got \x1b[33m{self.token}\x1b[0m as token.")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            self.logged_in = True
            return self.token

    def get_daily_read(self, esiid, start_date, end_date):
        if self.logged_in == False:
            self.log.error("You must login first.")
            return False

        json = {
            "esiid": esiid,
            "endDate": end_date,
            "startDate": start_date,
        }
        url = f"{MeterReader.HOST}/api/usage/daily"
        r = self.api_call(url, json=json)
        if r.status_code != 200 or "error" in r.text.lower():
            self.log.warning("Failed fetching daily read!")
            self.log.debug(r.text)
            self.log.debug(pformat(r.headers.__dict__))
            return False
        else:
            return r.json()
