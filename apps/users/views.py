from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View, TemplateView
from django.core.urlresolvers import reverse
import re
from users.models import User, Address
from django import db
from celery_tasks.tasks import send_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from utils.views import LoginRequiredMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
import json


# Create your views here.


class UserInfoView(LoginRequiredMixin, View):
    """个人信息"""

    def get(self, request):
        """查询基本信息和最近浏览,并渲染模板"""

        # 获取user
        user = request.user

        # 查询基本信息 : 用户名+联系方式+详细地址
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            # 将来在模板中,判断地址是否为空,如果为空,地址对应的html内容不写
            address = None

        # 查询最近浏览 : 使用django_redis操作redis
        # 创建一个连接到redis的对象
        redis_conn = get_redis_connection('default')
        # 调用对应的方法,查询出redis列表中保存的sku_ids = [2 8 5 3 7]
        sku_ids = redis_conn.lrange('history_%s' % user.id, 0, 4)
        # 定义临时列表容器
        sku_list = []
        # 遍历sku_ids,取出里面的sku_id
        for sku_id in sku_ids:
            # 查询出sku_id对应的GoodsSKU
            sku = GoodsSKU.objects.get(id=sku_id)
            sku_list.append(sku)

        # 构造上下文
        context = {
            'address': address,
            'sku_list': sku_list,
        }

        # 渲染模板
        return render(request, 'user_center_info.html', context)


class AddressView(LoginRequiredMixin, View):
    """收货地址"""

    def get(self, request):
        """提供收货地址页面，查询地址信息，并且渲染"""

        #获取登录的用户
        user = request.user

        # 查询登录用户的地址信息:查询用户最近创建的地址信息,取最新的一个地址,(按照时间倒叙,取第0个)
        # address = Address.objects.filter(user=user).order_by('-create_time')[0]
        # address = user.address_set.order_by('-create_time')[0]
        # latest : 默认倒叙,取出第0个
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            # 将来在模板中,判断地址是否为空,如果为空,地址对应的html内容不写
            address = None

        #构造上下文
        context = {
            # 'user':user, # user信息不需要传递给模板,因为user在request中,render会把request参数带入到模板
            'address':address
        }

        #渲染模板
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """修改地址信息"""

        # 接受编辑的地址参数
        recv_name = request.POST.get('recv_name')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recv_mobile = request.POST.get('recv_mobile')

        # 校验地址参数: 说明,实际开发,还需要校验数据是否真实.比如,手机号,邮编是否是符合规则的

        if all([recv_name, addr, zip_code, recv_mobile]):
            # 保存地址参数
            Address.objects.create(
                user=request.user,
                receiver_name=recv_name,
                receiver_mobile=recv_mobile,
                detail_addr=addr,
                zip_code=zip_code
            )

        # 响应结果
        return redirect(reverse('users:address'))

"""
if not request.user.is_authenticated():
    return redirect(reverse('users:login'))
else:
    return render(request, 'user_center_site.html')
"""


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        """处理退出登录逻辑: 确定谁要退出登录.也就是要确定清理谁的状态保持信息"""
        logout(request)

        return redirect(reverse('users:login'))


class LoginView(View):
    """登录"""

    def get(self, request):
        """提供登录页面"""
        return render(request, 'login.html')

    def post(self, request):
        """处理登录逻辑"""

        # 接受登录请求参数
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')

        # # 获取是否勾选'记住用户名'
        # remembered = request.POST.get('remembered')

        # 校验登录请求static/login.html参数
        if not all([user_name, pwd]):
            # 实际开发根据,开发文件实现
            return redirect(reverse('users:login'))

        # 判断用户是否存在
        user = authenticate(username=user_name, password=pwd)
        if user is None:
            # 提示用户:用户名或密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})

        # 判断用户是否是激活用户
        if user.is_active == False:
            return render(request, 'login.html', {'errmsg': '请激活'})

        # 登入该用户:主要的是生成状态保持的数据,并默认的写入到django_session表中
        # 提示 : 如果调用login(),没有指定SESSION_ENGINE,那么默认就存储在django_session表中
        # 提示 : 如果指定了SESSION_ENGINE,那么久按照引擎的指引进行session数据的存储,需要搭配django-redis使用
        login(request, user)

        #实现记住用户名/多少天免登录：如果用户勾选了‘记住用户名’，就把状态保持10天，反之，保持0秒
        # 获取是否勾选'记住用户名'
        remembered = request.POST.get('remembered')
        if remembered != 'on':
            request.session.set_expiry(0)  #状态保持0秒
        else:
            request.session.set_expiry(60*60*24*10)  #状态保持10天

        #在界面跳转之前，将cookie中的购物车信息合并得到redis
        cart_json = request.COOKIES.get('cart')
        if cart_json is not None:
            cart_dict_cookie = json.loads(cart_json)
        else:
            cart_dict_cookie = {}

        #查询redis中的购物车信息
        redis_conn = get_redis_connection('default')
        cart_dict_redis = redis_conn.hgetall('cart_%s' % user.id)

        #遍历cart_dict_cookie,取出其中的sku_id和count信息，存储到redis
        for sku_id, count in cart_dict_cookie.items():

            #将string转bytes
            #提醒：在做计算和比较时，需要记住类型统一
            sku_id = sku_id.encode()
            if sku_id in cart_dict_redis:
                origin_count = cart_dict_redis[sku_id]
                count += int(origin_count)

                #在这里合并有可能造成库存不足
                # sku = GoodsSKU.objects.get(id=sku_id)
                # if count > sku.stock:
                #     pass

            #保存合并的数据到redis
            cart_dict_redis[sku_id] = count


        #一次性向redis中新增多条记录
        if cart_dict_redis:
            redis_conn.hmset('cart_%s' % user.id, cart_dict_redis)


        # 在界面跳转之前，需要判断登录之后跳转的地方，如果有next就跳转到next指向的地方，反之跳转到住主页
        next = request.GET.get('next')
        if next is None:
            # 响应结果：跳转到主页
            return redirect(reverse('goods:index'))
        else:
            # 跳转到next指向的地方
            return redirect(next)

        # 在界面跳转以前,需要判断登录之后跳转的地方.如果有next就跳转到next指向的地方,反之,跳转到主页
        # http://127.0.0.1:8000/users/login?next=/users/info
        next = request.GET.get('next')
        # 登陆成功，根据next参数决定跳转方向
        if next is None:
            # 如果是直接登陆成功，就重定向到首页
            response = redirect(reverse('goods:index'))
        else:
            # 如果是用户中心重定向到登陆页面，就回到用户中心
            response = redirect(next)

        #删除cookie
        response.delete_cookie('cart')

        return response

        # # 响应结果: 跳转到主页
        # return HttpResponse('登入成功')


class ActiveView(View):
    """邮件激活"""

    def get(self, request, token):
        """处理激活逻辑"""

        # 创建序列化器: 注意<调用loads方法的序列化器的参数要和调用dumps方法时的参数一致>
        serializer = Serializer(settings.SECRET_KEY, 3600)

        # 解出原始字典 {"confirm": self.id}
        try:
            result = serializer.loads(token)
        except SignatureExpired: # 签名过期异常
            return HttpResponse('激活链接已过期')

        # 获取user_id
        user_id = result.get('confirm')

        # 查询user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist: # 查询的结果不存在的异常
            return HttpResponse('用户不存在')

        # 重置激活状态为True
        user.is_active = True
        # 一定要记得手动保存一次
        user.save()

        # 响应结果: 跳转到登录页面
        return redirect(reverse('users:login'))


class RegisterView(View):
    """类视图, 注册:提供注册页面和实现注册逻辑"""

    def get(self, request):
        """提供注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """处理注册逻辑,存储注册信息"""

        # 接受用户注册参数
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 校验用户注册参数: 只要有一个数据为空,那么久返回假,只有全部为真,才返回真
        if not all([user_name, pwd, email]):
            # 公司中,根据开发文档实现需求
            return redirect(reverse('users:register'))

        # 判断邮箱格式
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg':'邮箱格式错误'})

        # 判断是否勾选了协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg':'请勾选用户协议'})

        # 保存用户注册参数
        try:
            user = User.objects.create_user(user_name, email, pwd)
        except db.IntegrityError: # 重名异常判断
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 重置激活状态 : 需要使用邮件激活
        user.is_active = False
        # 注意: 需要重新保存一下
        user.save()

        # 生成token
        token = user.generate_active_token()

        # 异步发送激活邮件:不能阻塞HttpResponse
        # send_active_email(email, user_name, token) # 这是错误写法,不会触发异步的send_active_email
        # 正确的写法  delay()触发异步任务
        send_active_email.delay(email, user_name, token)

        # return HttpResponse('这里是处理注册逻辑')
        return redirect(reverse('goods:index'))

# def register(request):
#     """
#     函数视图, 注册:提供注册页面和实现注册逻辑
#     如果要在一个视图中,实现多种请求逻辑,请求地址使用相同的地址,只是请求方法不同而已
#     """
#
#     if request.method == 'GET':
#         """提供注册页面"""
#         return render(request, 'register.html')
#
#     if request.method == 'POST':
#         """处理注册逻辑,存储注册信息"""
#         return HttpResponse('这里是处理注册逻辑')
