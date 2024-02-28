
import os
import json
import cherrypy
import traceback as tb

class SmartMeterController(object):
    '''
    Base Controller abstract.
    If a method is common among all controllers it goes here.
    If a method should be implemented by all controllers, it could be included
    here for all controllers to enjoy.
    '''
    ERRORS = {
        'request-method': 'Request method not allowed.',
        'accept-json': 'Accept header must be application/json.',
        'not-json': 'Content-Type must be application/json.',
        'content-length': 'Content-Length header required.',
        'empty-body': 'Empty request body.',
        'invalid-json': 'Invalid JSON: %s',
    }

    def isValidJSONRequest(self, request, body):
        '''
        Collection of validations against the client request to this server.
        request: cherrypy.request object
        body: The result to attempt to parse as a string.

        400: bad request
        405: method not allowed
        406: not acceptable
        411: content-length required
        415: unsupported media type
        417: expectation failed
        422: Unprocessable entity

        Usage:

            isValid, errMesgs = self.isValidJSONRequest(request, payload)
            if not isValid:
                return { 'result': False, 'messages': errMesgs }
        '''
        result = True
        mesgs = []
        if request.get('REQUEST_METHOD', '') not in ['GET', 'POST', 'PUT']:
            result = False
            mesgs.append(SmartMeterController.ERRORS['request-method'])
            cherrypy.response.status = 405
        if request.get('REQUEST_URI', '').startswith('/api'):
            accept = request.get('HTTP_ACCEPT', '')
            if ('application/json' not in accept) and ('*/*' not in accept):
                result = False
                mesgs.append(SmartMeterController.ERRORS['accept-json'])
                cherrypy.response.status = 415
            if request['REQUEST_METHOD'] == 'POST':
                if 'application/json' not in request.get('CONTENT_TYPE', ''):
                    result = False
                    mesgs.append(SmartMeterController.ERRORS['not-json'])
                    cherrypy.response.status = 400
                cl = request.get('CONTENT_LENGTH', 0)
                if not cl or int(cl) < 1:
                    result = False
                    mesgs.append(SmartMeterController.ERRORS['content-length'])
                    cherrypy.response.status = 411
                if not body:
                    result = False
                    mesgs.append(SmartMeterController.ERRORS['empty-body'])
                    cherrypy.response.status = 411
                else:
                    try:
                        j = json.loads(body)
                    except ValueError as e:
                        result = False
                        mesgs.append(SmartMeterController.ERRORS['invalid-json'] % e)
                        cherrypy.response.status = 417
        return result, mesgs

    def returnError(self, err, mesgs):
        '''
        Return a [err] http response code and send the status message as an object.
        Usage:

          return self.returnError(500, ['no such file or directory'])
        '''
        kwargs = {}
        if not cherrypy.response.status or ( cherrypy.response.status >= 200 and cherrypy.response.status <= 299 ):
            cherrypy.response.status = int(err.get('status', 500))
        if isinstance(mesgs, str):
            mesgs = [mesgs]
        result = {
          'error': True,
          'mesgs': err.get('mesgs', mesgs),
          'value': None,
        }
        if 'DEBUG' in os.environ:
            kwargs['indent'] = 2
            kwargs['sort_keys'] = True
            if err.has_key('e'):
                result['exception'] = tb.format_exc(err['e'])
        return json.dumps(result, **kwargs) + "\n"

    def returnValue(self, result, value):
        '''
        Returns the value of the result you desire.
        result: Boolean to return as a result of the operation.
        value: object to return describing the result.
        @returns :string: JSON dump of a wrapped object of the input params.
        '''
        if not cherrypy.response.status:
            cherrypy.response.status = 200
        kwargs = {}
        if 'DEBUG' in os.environ:
            kwargs['indent'] = 2
            kwargs['sort_keys'] = True
        return {
            'error': False,
            'status': 200,
            'value': value,
            'return': result,
        }

