from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
import json


# Create your views here.


class DeleteCartView(View):
    """删除购物车记录:一次删除一条"""

    def post(self, request):

        # 接收参数：sku_id
        sku_id = request.POST.get('sku_id')

        # 校验参数：not，判断是否为空
        if not sku_id:
            return JsonResponse({'code':1, 'message':'sku_id为空'})

        # 判断sku_id是否合法
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code':2, 'message':'要删除的商品不存在'})

        # 判断用户是否登录
        if request.user.is_authenticated():
            # 如果用户登陆，删除redis中购物车数据
            redis_conn = get_redis_connection('default')
            user_id = request.user.id
            redis_conn.hdel('cart_%s' % user_id, sku_id)

        else:
            # 如果用户未登陆，删除cookie中购物车数据
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                cart_dict = json.loads(cart_json)

                # 删除字典中某个key及对应的内容
                del cart_dict[sku_id]

                # 将最新的cart_dict,转成json字符串
                new_cart_json = json.dumps(cart_dict)

                # 删除结果写入cookie
                response = JsonResponse({'code': 0, 'message': '删除成功'})
                response.set_cookie('cart', new_cart_json)

                return response

        return JsonResponse({'code': 0, 'message': '删除成功'})


class UpdateCartView(View):
    """更新购物车信息"""

    def post(self, request):
        """+ - 手动输入"""

        # 获取参数：sku_id, count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验参数all()
        if not all([sku_id, count]):
            return JsonResponse({'code': 1, 'message':'缺少参数'})

        # 判断商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '商品不存在'})

        # 判断count是否是整数
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code': 3, 'message': '商品数量错误'})

        # 判断库存
        if count > sku.stock:
            return JsonResponse({'code': 4, 'message': '库存不足'})

        # 判断用户是否登陆
        if request.user.is_authenticated():
            # 如果用户登陆，将修改的购物车数据存储到redis中
            redis_conn = get_redis_connection('default')
            user_id = request.user.id

            # 因为我们设计的接口是幂等的风格.传入的count就是用户最后要记录的商品的数量
            redis_conn.hset('cart_%s' % user_id, sku_id, count)

            return JsonResponse({'code': 0, 'message': '更新购物车成功'})
        else:
            # 如果用户未登陆，将修改的购物车数据存储到cookie中
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {}

            # 因为我们设计的接口是幂等的风格.传入的count就是用户最后要记录的商品的数量
            cart_dict[sku_id] = count

            # 把cart_dict转成最新的json字符串
            new_cart_json = json.dumps(cart_dict)

            # 更新cookie中的购物车信息
            response = JsonResponse({'code': 0, 'message': '更新购物车成功'})
            response.set_cookie('cart', new_cart_json)

            return response


class CartInfoView(View):
    """购物车信息"""

    def get(self, request):
        """登录和未登录时查询购物车数据,并渲染"""

        if request.user.is_authenticated():
            # 用户已登录时,查询redis中购物车数据
            redis_conn = get_redis_connection('default')
            user_id = request.user.id
            # 如果字典是通过redis_conn.hgetall()得到的,那么字典的key和value信息都是bytes类型
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
        else:
            # 用户未登录时,查询cookie中的购物车数据
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                # 如果cart_dict字典从cookie中得到的,那么key是字符串,value是int
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {}

        # 定义临时变量
        skus = []
        total_count = 0
        total_sku_amount = 0

        # cart_dict = {sku_id1:count1, sku_id2:count2}
        for sku_id, count in cart_dict.items():

            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                continue # 有异常,跳过.展示没有异常的数据

            #  统一count的数据类型为int,方便后续代码的计算和比较
            count = int(count)
            # 小计
            amount = count * sku.price

            # 提示:python是动态的面向对象的语言,所以可以动态的给sku对象添加属性,存储count和amount
            sku.count = count
            sku.amount = amount
            # 记录sku
            skus.append(sku)

            # 总金额和总计
            total_sku_amount += amount
            total_count += count

        # 构造上下文
        context = {
            'skus':skus,
            'total_sku_amount':total_sku_amount,
            'total_count':total_count
        }

        # 渲染模板
        return render(request, 'cart.html', context)


class AddCartView(View):
    """添加到购物车"""

    def post(self, request):
        """接受购物车参数,校验购物车参数,保存购物车参数"""

        # 判断用户是否登录
        # if not request.user.is_authenticated():
        #     return JsonResponse({'code':1, 'message':'用户未登录'})

        # 接受购物车参数 : sku_id, count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验参数 : all()
        if not all([sku_id, count]):
            return JsonResponse({'code':2, 'message':'缺少参数'})

        # 判断sku_id是否合法
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code':3, 'message': '商品不存在'})

        # 判断count是否合法
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code':4, 'message': '商品数量错误'})

        # 判断库存是否超出
        if count > sku.stock:
            return JsonResponse({'code':5, 'message': '库存不足'})

        if request.user.is_authenticated():

            # 获取user_id
            user_id = request.user.id

            # 保存购物车数据到Redis
            redis_conn = get_redis_connection('default')
            # 需要查询要保存到购物车的商品数据是否存在,如果存在,需要累加,反之,赋新值
            origin_count = redis_conn.hget('cart_%s' % user_id, sku_id)
            if origin_count is not None:
                count += int(origin_count) # django_redis保存的hash类型的数据是bytes类型的

            # 再次:判断库存是否超出,拿着最终的结果和库存比较
            if count > sku.stock:
                return JsonResponse({'code': 5, 'message': '库存不足'})

            redis_conn.hset('cart_%s' % user_id, sku_id, count)

            # 查询购物车中的商品数量,响应给前端
            cart_num = 0
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)
            for val in cart_dict.values():
                cart_num += int(val)

            # 响应结果
            return JsonResponse({'code':0, 'message': '添加购物车成功', 'cart_num':cart_num})
        else:
            # 用户未登录,保存购物车数据到cookie {sku_id:count}
            # 读取cookie中的购物车数据
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                # 把cart_json转成字典 : loads 将json字符串转成json字典
                cart_dict = json.loads(cart_json)
            else:
                cart_dict = {} # 为了后面继续很方便的操作购物车数据,这里定义空的字典对象

            # 判断要存储的商品信息,是否已经存在.如果已经存在就累加.反之,赋新值
            # 提醒 : 需要保证 sku_id和cart_dict里面的key的类型一致;此处的正好一致
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id] # origin_count : 在json模块中,数据类型不变
                count += origin_count

            # 再再次:判断库存是否超出,拿着最终的结果和库存比较
            if count > sku.stock:
                return JsonResponse({'code': 5, 'message': '库存不足'})

            # 把最新的商品的数量,赋值保存到购物车字典
            cart_dict[sku_id] = count

            # 在写入cookie之前,将cart_dict转成json字符串
            new_cart_json = json.dumps(cart_dict)

            # 为了方便前端展示最新的购物车数量,后端添加购物车成功后,需要查询购物车
            cart_num = 0
            for val in cart_dict.values():
                cart_num += val # val 是json模块运作的,存储的市数字,读取的也是数字

            # 创建response
            response = JsonResponse({'code':0, 'message':'添加购物车成功', 'cart_num':cart_num})

            # 写入cookie
            response.set_cookie('cart', new_cart_json)

            return response
