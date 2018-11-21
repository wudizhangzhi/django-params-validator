import unittest

from django.conf import settings
from rest_framework.response import Response

# Django settings need to be configured before importing the decorator


if __name__ == '__main__':
    settings.configure()
    from django_params_validator import Params


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

    def do_fake_request(self, request_fn, expected_status_code=200, method='GET', get={}, post={}):
        """ Perform a fake request to a request fn, check that we got the status code we expected """
        class FakeR(object):
            GET = {}
            POST = {}
            META = {
                'REQUEST_METHOD': None
            }
        fake_request = FakeR()
        fake_request.GET = get
        fake_request.DATA = post
        fake_request.META['REQUEST_METHOD'] = method

        # Did we accidentally make one of these a set?
        self.assertTrue(isinstance(fake_request.GET, dict))
        self.assertTrue(isinstance(fake_request.DATA, dict))

        response = request_fn(fake_request)
        if response.status_code != expected_status_code:
            import pprint
            pp = lambda o: pprint.PrettyPrinter(indent=2).pprint(o)
            print("\n============================== ERROR ==============================\n")
            pp(response.data)
            print("\n===================================================================\n")
            self.assertEqual(response.status_code, expected_status_code)
        return response.data

    def test_int(self):
        """ Test that we can require an 'int' param """

        @Params(my_int=int)
        def my_request(request, my_int):
            self.assertTrue(isinstance(my_int, int))
            return Response({'status': 'success'})

        # try without int
        self.do_fake_request(my_request, expected_status_code=400)

        # try with int
        self.do_fake_request(my_request, get={'my_int': 100})

        # try with wrong type
        self.do_fake_request(my_request, expected_status_code=400, get={'my_int': "not an int"})

    def test_float(self):
        """ Test that we can require a 'float' param """
        @Params(my_float=float)
        def my_request(request, my_float):
            self.assertTrue(isinstance(my_float, float))
            return Response({'status': 'success'})

        # try without float
        self.do_fake_request(my_request, expected_status_code=400)

        # try with float
        self.do_fake_request(my_request, get={'my_float': 100.0})

        # should still accept an int
        self.do_fake_request(my_request, get={'my_float': 100})

        # try with wrong type
        self.do_fake_request(my_request, expected_status_code=400, get={'my_float': "not an float"})

    def test_str(self):
        """ Test that we can require a 'str' param """

        @Params(my_str=str)
        def my_request(request, my_str):
            return Response({'status': 'success'})

        # try without str
        self.do_fake_request(my_request, expected_status_code=400)

        # try with str
        self.do_fake_request(my_request, get={'my_str': 'a str'})

        # try with wrong type
        self.do_fake_request(my_request, expected_status_code=400, get={'my_str': 100})

    def test_bool(self):
        """ Test that we can require a 'bool' param """
        @Params(my_bool=bool)
        def my_request(request, my_bool):
            self.assertTrue(isinstance(my_bool, bool))
            return Response({'result': my_bool})

        # check things that should be true
        for v in 1, 'true', 'True', 'TRUE':
            self.assertTrue(self.do_fake_request(my_request, get={'my_bool': v})['result'])

        # things that should be false
        for v in 0, 'false', 'False', 'FALSE':
            self.assertFalse(self.do_fake_request(my_request, get={'my_bool': v})['result'])

        # make sure some other values don't count as true
        self.do_fake_request(my_request, expected_status_code=400, get={'my_bool': 'ok'})
        self.do_fake_request(my_request, expected_status_code=400, get={'my_bool': 2})
        self.do_fake_request(my_request, expected_status_code=400, post={'my_bool': 'T'})


    def test_tuple(self):
        """ Test that we can specify a tuple for param """
        @Params(color=('red', 'green'))
        def my_request(request, color):
            self.assertTrue(color == 'red' or color == 'green')
            return Response({'status': 'success'})

        # don't specify param
        self.do_fake_request(my_request, expected_status_code=400, get={})

        # ok, specify something not in tuple
        self.do_fake_request(my_request, expected_status_code=400, get={'color': 'orange'})

        # ok, specify something in tuple
        self.do_fake_request(my_request, get={'color': 'red'})

    def test_django_model(self):
        """ Test that we can specify a Django model for a param """
        @Params(user=_MockUser)
        def my_request(request, user):
            self.assertTrue(isinstance(user, _MockUser))
            return Response({'status': 'success'})

        # don't specify
        self.do_fake_request(my_request, expected_status_code=400, get={})

        # specify something not and int
        self.do_fake_request(my_request, expected_status_code=400, get={'user': "Not a User ID"})

        # specify valid
        user = _MockUser.objects.create(name='Cam Saul', email='Myfakeemail@toucan.farm')
        self.assertTrue(user.id)
        self.do_fake_request(my_request, get={'user': user.id})

        # should work with str
        self.do_fake_request(my_request, get={'user': str(user.id)})

    def test_lt(self):
        @Params(my_int=int, my_int__lt=100)
        def my_request(request, my_int):
            self.assertTrue(my_int < 100)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_int': 100})

        # valid
        self.do_fake_request(my_request, get={'my_int': 99})

    def test_lte(self):
        @Params(my_int=int, my_int__lte=100)
        def my_request(request, my_int):
            self.assertTrue(my_int <= 100)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_int': 101})

        # valid
        self.do_fake_request(my_request, get={'my_int': 100})

    def test_gt(self):
        @Params(my_int=int, my_int__gt=10)
        def my_request(request, my_int):
            self.assertTrue(my_int > 10)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_int': 10})

        # valid
        self.do_fake_request(my_request, get={'my_int': 11})

    def test_gte(self):
        @Params(my_int=int, my_int__gte=10)
        def my_request(request, my_int):
            self.assertTrue(my_int >= 10)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_int': 9})

        # valid
        self.do_fake_request(my_request, get={'my_int': 10})

    def test_str_length_gt_lt(self):
        """ Test that lt/gt (etc) work on len(str) """
        @Params(my_str=str, my_str__length__lt=5, my_str__length__gte=2)
        def my_request(request, my_str):
            self.assertTrue(len(my_str) < 5)
            self.assertTrue(len(my_str) >= 2)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_str': 'THIS STRING IS WAY TOO LONG'})

        # valid
        self.do_fake_request(my_request, get={'my_str': 'GOOD'})

    def test_str_length_eq(self):
        """ Test that str__length__eq works """
        @Params(my_str=str, my_str__length__eq=4)
        def my_request(request, my_str):
            self.assertEqual(len(my_str), 4)
            return Response({'status': 'success'})

        # invalid
        self.do_fake_request(my_request, expected_status_code=400, get={'my_str': 'THIS STRING IS WAY TOO LONG'})

        # valid
        self.do_fake_request(my_request, get={'my_str': 'GOOD'})

    def test_optional(self):
        """ Test that we can make a param optional """
        @Params(my_int=int, my_int__optional=True)
        def my_request(request, my_int):
            self.assertEqual(my_int, None)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, get={})  # don't set it

    def test_default(self):
        """ Test that we can specify a default value for a param """
        @Params(my_int=int, my_int__default=100)
        def my_request(request, my_int):
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, get={})  # don't set it

    def test_name(self):
        """ Test that we can specify a name for the param different from what we'll call it in our function """
        @Params(my_int=int, my_int__name='my_int_param')
        def my_request(request, my_int):
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, get={'my_int_param': 100})

    def test_deferred(self):
        """ Test that we can make a Django model deferred, or not """
        # TODO

    def test_method_get(self):
        """ Test that we can specify param must be 'GET' """
        @Params(my_int=int, my_int__method='GET')
        def my_request(request, my_int):
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, method='POST', get={'my_int': 100})
        self.do_fake_request(my_request, method='POST', expected_status_code=400, post={'my_int': 100})

    def test_method_post(self):
        """ Test that we can specify param must be 'POST' """
        @Params(my_int=int, my_int__method='POST')
        def my_request(request, my_int):
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, method='POST', expected_status_code=400, get={'my_int': 100})
        self.do_fake_request(my_request, method='POST', post={'my_int': 100})

    def test_method_any(self):
        """ Test that we can allow either GET or POST. """
        @Params(my_int=int, my_int__method=('GET', 'POST'))
        def my_request(request, my_int):
            self.assertEqual(my_int, 100)
            return Response({'status': 'success'})

        self.do_fake_request(my_request, method='POST', get={'my_int': 100})
        self.do_fake_request(my_request, method='POST', post={'my_int': 100})

    def test_many(self):
        """ Test that __many=True will let yoy pass CSV or JSON Array params """
        @Params(user_ids=int, user_ids__many=True)
        def my_request(request, user_ids):
            self.assertEqual(user_ids[-1], 100)
            return Response({'status': 'success'})

        # single val should work
        self.do_fake_request(my_request, get={'user_ids': 100})

        # multiple vals should work
        self.do_fake_request(my_request, get={'user_ids': '98,99,100'})

        # POST - single val
        self.do_fake_request(my_request, method='POST', post={'user_ids': 100})

        # POST - multiple vals
        self.do_fake_request(my_request, method='POST', post={'user_ids': [87, 97, 100]})



if __name__ == '__main__':
    unittest.main()