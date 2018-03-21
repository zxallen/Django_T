from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from functools import wraps
from django.db import transaction


class LoginRequiredMixin(object):
    """重写as_view()"""

    @classmethod
    def as_view(cls, **initkwargs):
        # 需要获取到View的as_view()执行之后的结果,并且使用login_required装饰器装饰
        view = super().as_view(**initkwargs)
        return login_required(view)

        # 如果直接返回view,就是相当于返回了没有装饰的视图函数
        # return view





def login_required_json(view_func):
    """验证用户是否登录,跟JSON交互的"""

    # 装饰器在装饰函数时,会修改函数内部的__name__属性,和文档信息,从而有可能改变函数名称,造成请求方法不成功
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """判断用户是否登录,如果登录进入到视图,反之,响应json给ajax"""
        if not request.user.is_authenticated():
            return JsonResponse({'code':1, 'message':'用户未登录'})
        else:
            return view_func(request, *args, **kwargs)

    return wrapper


class LoginRequiredJSONMixin(object):
    """重写as_view()"""

    @classmethod
    def as_view(cls, **initkwargs):
        # 需要获取到View的as_view()执行之后的结果,并且使用login_required装饰器装饰
        view = super().as_view(**initkwargs)
        return login_required_json(view)


class TransactionAtomicMixin(object):
    """重写as_view()"""

    @classmethod
    def as_view(cls, **initkwargs):
        # 需要获取到View的as_view()执行之后的结果,并且使用login_required装饰器装饰
        view = super().as_view(**initkwargs)
        return transaction.atomic(view)