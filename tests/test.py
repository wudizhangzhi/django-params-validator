from django_params_validator import *


class TestRequest(object):
    _get = lambda x: object()

    def __init__(self):
        pass

    @property
    def GET(self):
        pass


@Params(blank_param=int, )
def test_func(request, *args, **kwargs):
    pass


def main():
    pass


if __name__ == '':
    pass
