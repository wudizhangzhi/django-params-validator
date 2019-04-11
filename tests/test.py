import unittest
import sys
from django.conf import settings

# Django settings need to be configured before importing the decorator


if __name__ == '__main__':
    settings.configure()
    sys.path.append('..')
    from django_params_validator import Params, ParamsErrorException

from rest_framework.response import Response


class _MockUserManager(object):
    """ Mock Manager object for _MockUser """

    _objects = {}
    _next_id = 1

    def create(self, **kwargs):
        """ Create a mocked model """
        u = _MockUser(**kwargs)
        u.id = _MockUserManager._next_id
        u.pk = u.id
        _MockUserManager._next_id += 1
        _MockUserManager._objects[u.id] = u
        return u

    def get(self, **kwargs):
        """ Fake .get() returns first thing in _objects that matches one of the kwarg pairs """
        for k, v in kwargs.items():
            for id, obj in _MockUserManager._objects.items():
                if k == 'id' or k == 'pk':
                    if obj.id == int(v):
                        return obj
                elif getattr(obj, k) == v:
                    return obj
        raise Exception("Invalid argument(s): .get(%s='%s')" % (k, v))

    def only(self, *args):
        """ Just no-op """
        return self


class _MockUser(object):
    """ A mock model to test that our Django model integration works correctly """

    _default_manager = None  # @Params looks for this property to determine if the object if a Django model
    objects = _MockUserManager()

    name = None
    email = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class ParamDecoratorTest(unittest.TestCase):
    def setUp(self):
        pass

    def do_fake_request(self, request_fn, expected_status=True, method_='GET', get={}, post={}):
        """ Perform a fake request to a request fn, check that we got the status code we expected """
        class ListDict(dict):
            def getlist(self, key, default=None):
                return [self[key]] if self[key] else  default

        class Req(object):
            method = 'GET'

        class FakeR(object):
            data = {}
            GET = ListDict() 
            POST = {}
            META = {
                'REQUEST_METHOD': None
            }
            _request = Req()

        fake_request = FakeR()
        fake_request.GET.update(get)
        fake_request.data = post
        fake_request._request.method = method_

        # Did we accidentally make one of these a set?
        self.assertTrue(isinstance(fake_request.GET, dict))
        self.assertTrue(isinstance(fake_request.data, dict))

        try:
            response = request_fn(fake_request)
            response_status = True
            response_msg = response.data
        except ParamsErrorException as e:
            response_status = False
            response_msg = str(e)
        if response_status != expected_status:
            import pprint
            pp = lambda o: pprint.PrettyPrinter(indent=2).pprint(o)
            print("\n============================== ERROR ==============================\n")
            pp(response_msg)
            print("\n===================================================================\n")
            self.assertEqual(expected_status, response_status)
        return response_msg

    def test_int(self):
        """ Test that we can require an 'int' param """

        @Params(my_int=int)
        def my_request(request, *args, **kwargs):
            my_int = kwargs.get('my_int')
            if my_int:
                self.assertTrue(isinstance(my_int, int))
            return Response({'status': 'success'})

        # try without int
        self.do_fake_request(my_request, expected_status=True)

        # try with int
        self.do_fake_request(my_request, get={'my_int': 100})

        # try with wrong type
        self.do_fake_request(my_request, expected_status=False, get={'my_int': "not an int"})

    def test_float(self):
        """ Test that we can require a 'float' param """

        @Params(my_float=float)
        def my_request(request, *args, **kwargs):
            my_float = kwargs.get('my_float')
            if my_float:
                self.assertTrue(isinstance(my_float, float))
            return Response({'status': 'success'})

        # try without float
        self.do_fake_request(my_request, expected_status=True)

        # try with float
        self.do_fake_request(my_request, get={'my_float': 100.0})

        # TODO maybe need accept
        self.do_fake_request(my_request, expected_status=False, get={'my_float': 100})

        # try with wrong type
        self.do_fake_request(my_request, expected_status=False, get={'my_float': "not an float"})

    def test_str(self):
        """ Test that we can require a 'str' param """

        @Params(my_str=str)
        def my_request(request, *args, **kwargs):
            my_str = kwargs.get('my_str')
            return Response({'status': 'success'})

        # try without str
        self.do_fake_request(my_request, expected_status=True)

        # try with str
        self.do_fake_request(my_request, get={'my_str': 'a str'})

        # try with wrong type
        self.do_fake_request(my_request, expected_status=False, get={'my_str': 100})

    def test_bool(self):
        """ Test that we can require a 'bool' param """

        @Params(my_bool=bool, my_bool__default=True)
        def my_request(request, *args, **kwargs):
            my_bool = kwargs.get('my_bool')
            print('output: %r' % my_bool)
            if my_bool is not None:
                self.assertTrue(isinstance(my_bool, bool))
            return Response({'result': my_bool})

        # check things that should be true
        for v in 1, '1', 'true', None:
            print('intput: %r' % v)
            self.assertTrue(self.do_fake_request(my_request, get={'my_bool': v})['result'])

        # things that should be false
        # for v in 0, '0', 'false', 'False':
        #     self.assertFalse(self.do_fake_request(my_request, get={'my_bool': v})['result'])

        # make sure some other values don't count as true
        self.do_fake_request(my_request, expected_status=False, get={'my_bool': 'ok'})
        self.do_fake_request(my_request, expected_status=False, get={'my_bool': 2})
        self.do_fake_request(my_request, expected_status=False, method_='POST', post={'my_bool': 'T'})

    def test_tuple(self):
        """ Test that we can specify a tuple for param """

        @Params(color=('red', 'green'))
        def my_request(request, *args, **kwargs):
            color = kwargs.get('color')
            self.assertTrue(color == 'red' or color == 'green')
            return Response({'status': 'success'})

        # don't specify param
        # self.do_fake_request(my_request, expected_status=True, get={})
        #
        # ok, specify something not in tuple
        self.do_fake_request(my_request, expected_status=False, get={'color': 'orange'})

        # ok, specify something in tuple
        self.do_fake_request(my_request, get={'color': 'red'})

        # def test_lt(self):
        #     @Params(my_int=int, my_int__lt=100)
        #     def my_request(request, my_int):
        #         self.assertTrue(my_int < 100)
        #         return Response({'status': 'success'})
        #
        #     # # invalid
        #     # self.do_fake_request(my_request, expected_status_code=200, get={'my_int': 100})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_int': 99})
        #
        # def test_lte(self):
        #     @Params(my_int=int, my_int__lte=100)
        #     def my_request(request, my_int):
        #         self.assertTrue(my_int <= 100)
        #         return Response({'status': 'success'})
        #
        #     # invalid
        #     self.do_fake_request(my_request, expected_status_code=200, get={'my_int': 101})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_int': 100})
        #
        # def test_gt(self):
        #     @Params(my_int=int, my_int__gt=10)
        #     def my_request(request, my_int):
        #         self.assertTrue(my_int > 10)
        #         return Response({'status': 'success'})
        #
        #     # invalid
        #     self.do_fake_request(my_request, expected_status_code=200, get={'my_int': 10})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_int': 11})
        #
        # def test_gte(self):
        #     @Params(my_int=int, my_int__gte=10)
        #     def my_request(request, my_int):
        #         self.assertTrue(my_int >= 10)
        #         return Response({'status': 'success'})
        #
        #     # invalid
        #     self.do_fake_request(my_request, expected_status_code=200, get={'my_int': 9})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_int': 10})
        #
        # def test_str_length_gt_lt(self):
        #     """ Test that lt/gt (etc) work on len(str) """
        #
        #     @Params(my_str=str, my_str__lt=5, my_str__gte=2)
        #     def my_request(request, my_str):
        #         self.assertTrue(len(my_str) < 5)
        #         self.assertTrue(len(my_str) >= 2)
        #         return Response({'status': 'success'})
        #
        #     # invalid
        #     self.do_fake_request(my_request, expected_status_code=200, get={'my_str': 'THIS STRING IS WAY TOO LONG'})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_str': 'GOOD'})
        #
        # def test_str_length_eq(self):
        #     """ Test that str__length__eq works """
        #
        #     @Params(my_str=str, my_str__eq=4)
        #     def my_request(request, my_str):
        #         self.assertEqual(len(my_str), 4)
        #         return Response({'status': 'success'})
        #
        #     # invalid
        #     self.do_fake_request(my_request, expected_status_code=200, get={'my_str': 'THIS STRING IS WAY TOO LONG'})
        #
        #     # valid
        #     self.do_fake_request(my_request, get={'my_str': 'GOOD'})
        #

    def test_optional(self):
        """ Test that we can make a param optional """

        @Params(my_int=int, my_int__optional=False)
        def my_request(request, my_int):
            return Response({'status': 'success'})

        self.do_fake_request(my_request, get={}, expected_status=False)  # don't set it

    def test_default(self):
        """ Test that we can specify a default value for a param """

        @Params(my_int=int, my_int__default=100)
        def my_request(request, *args, **kwargs):
            my_int = kwargs.get('my_int')
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, get={})  # don't set it
        #
        # def test_name(self):
        #     """ Test that we can specify a name for the param different from what we'll call it in our function """
        #
        #     @Params(my_int=int, my_int__name='my_int_param')
        #     def my_request(request, my_int):
        #         self.assertEqual(my_int, 100)
        #         return Response({'status': 'success'})
        #
        #     self.do_fake_request(my_request, get={'my_int_param': 100})
        #
        # def test_method_get(self):
        #     """ Test that we can specify param must be 'GET' """
        #
        #     @Params(my_int=int, my_int__method='GET')
        #     def my_request(request, my_int):
        #         self.assertEqual(my_int, 100)
        #         return Response({'status': 'success'})
        #
        #     self.do_fake_request(my_request, method_='POST', get={'my_int': 100})
        #     self.do_fake_request(my_request, method_='POST', expected_status_code=200, post={'my_int': 100})
        #
        # def test_method_post(self):
        #     """ Test that we can specify param must be 'POST' """
        #
        #     @Params(my_int=int, my_int__method='POST')
        #     def my_request(request, my_int):
        #         self.assertEqual(my_int, 100)
        #         return Response({'status': 'success'})
        #
        #     self.do_fake_request(my_request, method_='POST', expected_status_code=200, get={'my_int': 100})
        #     self.do_fake_request(my_request, method_='POST', post={'my_int': 100})
        #
        # def test_method_any(self):
        #     """ Test that we can allow either GET or POST. """
        #
        #     @Params(my_int=int, my_int__method=('GET', 'POST'))
        #     def my_request(request, my_int):
        #         self.assertEqual(my_int, 100)
        #         return Response({'status': 'success'})
        #
        #     self.do_fake_request(my_request, method_='POST', get={'my_int': 100})
        #     self.do_fake_request(my_request, method_='POST', post={'my_int': 100})
        #

    def test_many(self):
        """ Test that __many=True will let yoy pass CSV or JSON Array params """

        @Params(user_ids=int, user_ids__many=True)
        def my_request(request, *args, **kwargs):
            user_ids = kwargs.get('user_ids')
            self.assertEqual(user_ids[-1], 100)
            return Response({'status': 'success'})

        # single val should work
        # self.do_fake_request(my_request, get={'user_ids': 100})
        #
        # # multiple vals should work
        # self.do_fake_request(my_request, get={'user_ids': '98,99,100'})

        # POST - single val
        self.do_fake_request(my_request, method_='POST', post={'user_ids': 100}, expected_status=False)

        # POST - multiple vals
        self.do_fake_request(my_request, method_='POST', post={'user_ids': [87, 97, 100]})

    def test_date(self):
        """ Test date format"""

        @Params(my_date=Params.DATETIME_STR, my_date__format='%Y-%m-%d')
        def my_request(request, *args, **kwargs):
            my_date = kwargs.get('my_date')
            # self.assertEqual(my_date, '2018-10-10')
            return Response({'status': 'success'})

        self.do_fake_request(my_request, method_='POST', post={'my_date': '2018-10-10'}, expected_status=True)

        self.do_fake_request(my_request, method_='POST', post={}, expected_status=True)
    
    def test_choices_set_null(self):
        @Params(test_choices=('days', 'weeks', 'months'), test_choices__many=True)
        def my_request(request, *args, **kwargs):
            test_choices = kwargs.get('test_choices')
            self.assertEqual(test_choices, [])
            return Response({'status': 'success'})
        
        self.do_fake_request(my_request, method_='GET', get={'test_choices': ''}, expected_status=True)


if __name__ == '__main__':
    unittest.main()
    # ParamDecoratorTest().test_choices_set_null()