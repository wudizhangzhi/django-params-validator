from django_params_validator import *


class TestRequest(object):
    _get = lambda x: object()

    def __init__(self):
        pass

    @property
    def GET(self):
        pass


class TEST(object):
    @Params(blank_param=int, )
    def test_func(self, request, *args, **kwargs):
        pass


def main():
    request = TestRequest()


if __name__ == '':
    pass
