#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/8/10 下午3:39
# @Author  : wudizhangzhi

from functools import wraps
from copy import deepcopy
import datetime
from rest_framework.exceptions import APIException
from rest_framework import status
from django.conf import settings
from collections import Iterable

if hasattr(settings, 'API_DEFAULT_MSG'):
    DEFAULT_MSG = settings.API_DEFAULT_MSG
else:
    DEFAULT_MSG = '请求参数错误'


def convert_bool(x):
    if str(x).lower() in ['0', 'false']:
        return False
    else:
        return True


class ParamsErrorException(APIException):
    status_code = status.HTTP_200_OK
    # status_code = status.HTTP_400_BAD_REQUEST
    default_detail = DEFAULT_MSG

    def __init__(self, detail=None, code=None):
        # 如果不是测试模式，只显示默认信息
        if not settings.DEBUG:
            detail = self.default_detail
        super(ParamsErrorException, self).__init__(detail, code)


class ParamValidator(object):
    ITERABLE_TYPES = tuple, list, set
    # 基础信息
    param_name = None
    param_type = None
    val = None

    # value validators
    gt = None
    gte = None
    lt = None
    lte = None
    eq = None
    choices = None
    format = '%Y-%m-%d %H:%M:%S'

    # optional
    optional = True
    default = None

    # multiple vals
    many = False

    # db use
    field = None

    def __init__(self, param_name, **kwargs):
        self.param_name = param_name
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<%s: %s>' % (self.param_name, self.param_type.__name__)

    def __eq__(self, other):
        return self.param_name == other

    def check(self, param):
        param = self.check_type(param)
        return self.check_val(param)

    def validate_datetime(self, time_str):
        try:
            datetime.datetime.strptime(time_str, self.format)
        except ValueError:
            raise ParamsErrorException("错误的日期格式: %s, 应该是: %s" % (time_str, self.format))

    def check_type(self, param):
        # 判断不能为空
        if self.param_type:
            if self.many:
                if not Params.is_iterable(param):
                    raise ParamsErrorException(
                        '%s 应该是 iterable, 收到的是 %s' % (self.param_name, type(param).__name__))
                copyed = deepcopy(self)
                copyed.many = False
                param = [copyed.check_type(p) for p in param]
            else:
                # 转换布尔值
                if self.param_type == bool and str(param).lower() in ['0', '1', 'true', 'false']:
                    param = convert_bool(param)
                # 转换digit
                if self.param_type in [int, float] and isinstance(param, str):
                    try:
                        param = self.param_type(param)
                    except:
                        pass

                # 如果是选项
                if self.choices:
                    if param not in self.choices:
                        if param in Params.NULL_VALUE_LIST and self.optional:
                            pass
                        else:
                            raise ParamsErrorException(
                                '%s 只能在 %r 内取值, 而接受到的是: %s' % (self.param_name, self.choices, param))
                # 如果是日期格式字符串
                if self.param_type == Params.DATETIME_STR:
                    self.validate_datetime(param)
                elif self.param_type and not self.choices and not isinstance(param, self.param_type):
                    raise ParamsErrorException(
                        '%s 应该是 %s类型, 收到的是 %s' % (self.param_name, self.param_type.__name__, type(param).__name__))
            return param

    def check_val(self, param):
        if Params.is_iterable(param):
            val_or_length = len(param)
        else:
            val_or_length = param
        # 判断取值范围
        if self.lt and not val_or_length < self.lt:
            raise ParamsErrorException('%s 应该小于 %s' % (self.param_name, self.lt))
        if self.lte and not val_or_length <= self.lte:
            raise ParamsErrorException('%s 应该小于等于 %s' % (self.param_name, self.lte))
        if self.gt and not val_or_length > self.gt:
            raise ParamsErrorException('%s 应该大于 %s' % (self.param_name, self.gt))
        if self.gt and not val_or_length >= self.gte:
            raise ParamsErrorException('%s 应该大于等于 %s' % (self.param_name, self.gte))
        return param


class Params(object):
    """
    参数检查装饰器
    @Params(param=float, param__gte=120, param__lte=200,
            is_true=boolean, is_true__default=True,
            colors=('red','blue','green','yellow'), colors__many=True)
    自动判断参数类型 int, float, str, datetime
    自动判断参数范围 大于小于等于，选项 
    如果参数类型是bool, 自动将['1', 1]转化为 True, ['0', 0]转化为False
    param__many=True, 是list
    param=iterable, 是选项
    """
    split_str = '__'
    choices_str = 'choices'
    param_type_str = 'param_type'
    # 日期时间类型
    DATETIME_STR = 'datetime_str'

    NULL_VALUE_LIST = [None, '', []]

    def __init__(self, **params):
        self._params = params
        self._validators = {}
        # 生成验证器
        for k, v in self._params.items():
            if self.split_str in k:
                p_name, arg = k.split(self.split_str)
            else:
                p_name = k
                arg = self.param_type_str
                if self.is_iterable(v):  # determine whether param is iterable
                    arg = self.choices_str
            if p_name not in self._validators:
                self._validators[p_name] = ParamValidator(p_name)
            validator = self._validators[p_name]
            setattr(validator, arg, v)
            # 如果是选项
            if arg == self.choices_str:
                setattr(validator, self.param_type_str, type(v[0]))

    @staticmethod
    def is_iterable(v):
        if isinstance(v, Iterable) and v != Params.DATETIME_STR:
            return True
        else:
            return False

    def __call__(self, func):
        @wraps(func)
        def wrapper(first_arg, *args, **kwargs):
            # import ipdb;ipdb.set_trace()
            # 获取参数
            if len(args) == 0:
                request = first_arg  # request function is a top-level function
            else:
                request = args[0]  # request fn is a method, first_arg is 'self'

            request_method = request._request.method

            if request_method == 'GET':
                request_data = request.GET
            else:
                request_data = request.data

            for arg_name, validator in self._validators.items():
                param_name = validator.param_name
                null_list = []
                if validator.many and request_method == 'GET':
                    param = request_data.getlist(param_name, null_list)
                    # 过滤
                    param = [i for i in param if i not in self.NULL_VALUE_LIST]
                else:
                    param = request_data.get(param_name, None)
                kwargs[param_name] = param
                if param in self.NULL_VALUE_LIST:  # 如果参数值是空
                    if validator.default is not None:  # 如果有默认值
                        kwargs[param_name] = validator.default
                        continue
                    if validator.optional:  # 如果不必填
                        continue
                    else:
                        raise ParamsErrorException('缺少参数 %s' % param_name)
                param = validator.check(param)
                # 没有办法修改querydict。先保存到kwargs
                kwargs[param_name] = param
            return func(first_arg, request, *args, **kwargs)

        return wrapper
