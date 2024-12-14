import os
import requests
import gnupg

from pprint import pformat
from kizano import getLogger, getConfig

# BEGIN: #StackOverflow
# @Source: https://stackoverflow.com/a/16630836/2769671
# These two lines enable debugging at httplib level (requests->urllib3->http.client)
# You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# The only thing missing will be the response.body which is not logged.
if os.getenv('DEBUG', False):
    requests_log = getLogger("requests.urllib3", 10)
    requests_log.propagate = True
# END: #StackOverflow


class MeterReader:
    HOSTNAME = 'services.smartmetertexas.net'
    HOST = f'https://{HOSTNAME}'
    USER_AGENT = 'API Calls (python3; Linux x86_64) Track your own metrics with SmartMeterTX: https://github.com/markizano/smartmetertx'
    TIMEOUT = 30

    def __init__(self, timeout: int = 10):
        self.log = getLogger(__name__)
        self.config = getConfig()
        self.logged_in = False
        self.gpg = gnupg.GPG(gnupghome=os.path.join(os.environ['HOME'], '.gnupg'), use_agent=True)
        self.session = requests.Session()
        self.timeout = timeout
        self.lastError = None
        self.session.headers['Authority'] = MeterReader.HOSTNAME
        self.session.headers['Origin'] = MeterReader.HOST
        self.session.headers['Accept'] = 'application/json, text/plain, */*'
        self.session.headers['Accept-Language'] = 'en-US,en;q=0.9'
        self.session.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.session.headers['dnt'] = '1'
        self.session.headers['User-Agent'] = MeterReader.USER_AGENT

    def api_call(self, url: str, json: dict) -> requests.Response:
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
                # Since Feb2024 update, you need to be whitelisted and have a client cert to access the endpoint.
                cert=(os.path.expanduser(self.config['smartmetertx']['cert_path']), os.path.expanduser(self.config['smartmetertx']['key_path'])),
                auth=(self.config['smartmetertx']['user'], self.gpg.decrypt(self.config['smartmetertx']['pass']).data.decode('utf-8'))
            )
        except Exception as ex:
            self.log.error(repr(ex))
            raise ex

    def get_daily_read(self, esiid: str, start_date: str, end_date: str) -> dict|bool:
        '''
        Gets a daily meter read.
        @param esiid :string: The ESIID to get the daily read.
        @param start_date :string: The start date to get the read in MM/DD/YYYY format.
        @param end_date :string: The end date to get the read in MM/DD/YYYY format.
        @throws Exception: If the API call fails.
        @return :object: JSON response back or False if failed.
        '''
        json = {
            "trans_id": esiid,
            "requestorID": self.config['smartmetertx']['user'].upper(),
            "requesterType": "RES",
            "startDate": start_date,
            "endDate": end_date,
            "version": "L",
            "readingType": "c",
            "esiid": [ esiid ],
            "SMTTermsandConditions": "Y"
        }
        url = f"{MeterReader.HOST}/dailyreads/"
        try:
            response = self.api_call(url, json=json)
        except Exception as ex:
            self.log.error(repr(ex))
            self.lastError = {
                'url': url,
                'request': json,
                'exception': repr(ex),
            }
            return False
        if response.status_code != 200 or "error" in response.text.lower():
            self.log.warning("Failed fetching daily read!")
            self.log.debug(response.text)
            self.log.debug(pformat(response.headers.__dict__))
            self.lastError = {
                'status': response.status_code,
                'headers': response.headers.__dict__,
                'url': url,
                'request': json,
                'response': response.text,
            }
            return False
        else:
            return response.json()

    def get_last_error(self) -> dict|None:
        if self.lastError:
            error = self.lastError
            self.lastError = None
            return error
        return None

