import os
import requests
import gnupg
import dateparser
from datetime import datetime

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

class MeterReaderException(Exception):
    def __init__(self, url: str, request: dict, previous: Exception):
        self.url = url
        self.request = request
        self.previous = previous
        super().__init__(f"MeterReaderException: {url}, {request}, {previous}")

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
        self.expiry = None
        self.token = None
        self.session.headers.update({
            'Authority': MeterReader.HOSTNAME,
            'Origin': MeterReader.HOST,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json; charset=UTF-8',
            'dnt': '1',
            'User-Agent': MeterReader.USER_AGENT,
        })
        if os.getenv('LOCAL', False):
            # I use a local proxy for just the SMTX API because they whitelist by IP.
            # Using a local SSH Dynamic Proxy allows me to source from PROD without interfering with boto3.
            self.log.info('Using local proxy...')
            self.session.proxies.update({
                'http': 'socks5://127.0.0.1:5000',
                'https': 'socks5://127.0.0.1:5000',
            })
        self.login()

    def login(self) -> str:
        '''
        Since 2025-09, SMT has updated to implement JWT.
        To authenticate, we no longer send credentials in the POST method.
        Similar to OAuth2, you post credentials to a login API endpoint and cache a credential
        received from the token generation API endpoint.
        '''
        if self.expiry and self.expiry > datetime.now():
            self.log.debug(f'Token is still valid until {self.expiry}')
            return self.token
        url = f"{MeterReader.HOST}/v2/token/"
        self.log.debug(f'Logging in to {url}...')
        json = {
            "username": self.config['smartmetertx']['user'],
            "password": self.gpg.decrypt(self.config['smartmetertx']['pass']).data.decode('utf-8')
        }
        try:
            response = self.session.post(
                url=url,
                json=json,
                timeout=self.timeout,
                # Since Feb2024 update, you need to be whitelisted and have a client cert to access the endpoint.
                # As of 2025-09, you no longer need a client cert to access the endpoint.
                #cert=(os.path.expanduser(self.config['smartmetertx']['cert_path']), os.path.expanduser(self.config['smartmetertx']['key_path'])),
                auth=(self.config['smartmetertx']['user'], self.gpg.decrypt(self.config['smartmetertx']['pass']).data.decode('utf-8'))
            )
        except Exception as ex:
            self.log.error(repr(ex))
            raise MeterReaderException(url, json, ex)
        payload = response.json()
        self.token = payload['accessToken']
        tokenType = payload['tokenType']
        self.session.headers.update({
            'Authorization': f'{tokenType} {self.token}'
        })
        self.expiry = dateparser.parse(payload['expiresAt'])
        return self.token

    def api_call(self, url: str, json: dict) -> requests.Response:
        '''
        Generic API call that can be made to the site for JSON results back.
        @param url :string: Where to send POST request.
        @param json :object: Data to send to the server.
        @return :object: JSON response back or ERROR
        '''
        self.login()
        self.log.debug(f'MeterReader.api_call(url={url}, json={json})')
        try:
            return self.session.post(
                url=url,
                json=json,
                timeout=self.timeout,
            )
        except Exception as ex:
            self.log.error(repr(ex))
            raise MeterReaderException(url, json, ex)

    def get_daily_read(self, esiid: str, start_date: str, end_date: str) -> dict:
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
            "readingType": "C",
            "esiid": [ esiid ],
            "SMTTermsandConditions": "Y"
        }
        url = f"{MeterReader.HOST}/v2/dailyreads/"
        response = self.api_call(url, json=json)
        if response.status_code != 200 or "error" in response.text.lower():
            ex = Exception(f'Failed fetching daily read! {response.text}')
            raise MeterReaderException(url, json, ex)
        return response.json()

    def get_15min_reads(self, esiid: str, start_date: str, end_date: str) -> dict|bool:
        '''
        Gets a 15 minute interval meter read.
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
            "readingType": "C",
            "esiid": [ esiid ],
            "SMTTermsandConditions": "Y"
        }
        url = f"{MeterReader.HOST}/v2/15minintervalreads/"
        response = self.api_call(url, json=json)
        if response.status_code != 200 or "error" in response.text.lower():
            ex = Exception(f'Failed fetching 15 minute interval read! {response.text}')
            raise MeterReaderException(url, json, ex)
        return response.json()

