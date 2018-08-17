# django-params-validator
django restframe params validator

use for check django rest api params
用于检查django的rest接口的参数
包括参数的类型、范围
如果参数是bool类型，能将 1, 0转化为布尔值
```bash
pip install django-params-validator
```
# Example

```python
from django_params_validator import Params

@Params(book_num=int, book_num__gte=100, book_num__lte=200, book__optional=False)
def some_interface(request, *args, **kwargs):
    pass
    
    
@Params(name=str, name__default='jack',
        create_datetime=Params.DATETIME_STR, create_datetime__format='%Y-%m-%d',
        colors=('red', 'blue', 'yellow'), colors__many=True)
def other_interface(request, *args, **kwargs):
    colors = kwargs.get('colors')
    # colors = ['']
    pass
```


# Options

## TYPE

```name=str```
指定参数的类型

其中Params.DATETIME_STR是特殊的时间戳字符串格式

## gt/lt/gte/lte
制定参数的范围
```num__gte=100```


## optional
是否是可选参数


## default
默认值

## many
```colors__many=True```
是否是列表。