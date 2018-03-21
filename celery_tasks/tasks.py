from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
from goods.models import GoodsCategory, Goods, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexCategoryGoodsBanner
from django.template import loader
import os

# 创建Celery客户端/Celery对象
# 参数1 : 指定任务所在的路径,从包名开始; 参数2 : 指定任务队列(broker),可以作为任务队列的有多种,此处以Redis数据库为例
app = Celery('celery_tasks.tasks', broker='redis://192.168.59.134:6379/4')

# 生产任务
@app.task
def send_active_email(to_email, user_name, token):
    """封装发送邮件的任务"""

    subject = "天天生鲜用户激活"  # 标题
    body = ""  # 文本邮件体
    sender = settings.EMAIL_FROM  # 发件人
    receiver = [to_email]  # 接收人
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (user_name, token, token)
    send_mail(subject, body, sender, receiver, html_message=html_body)


@app.task
def generate_static_index_html():
    """异步生成静态主页"""

    #查询商品分类信息
    categorys = GoodsCategory.objects.all()

    #查询图片轮播信息：需求，根据index从小到大排序
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    #查询商品活动信息：需求，根据index从小到大排序
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    #查询主页分类商品列表信息
    for category in categorys:
        title_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0)
        category.title_banners = title_banners

        image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1)
        category.image_banners = image_banners


    #查询购物车信息
    cart_num = 0

    #构造上下文
    context = {
        'categorys': categorys,
        'goods_banners': goods_banners,
        'promotion_banners': promotion_banners,
        'cart_num': cart_num
    }

    #获取模板
    template = loader.get_template('static_index.html')

    #渲染模板
    html_data = template.render(context)

    # 保存模板html_data
    # 保存到celery服务器上,因为代码在celery服务器运行的
    # 保存到celery服务器什么地方:随便/但是我会放在celery服务器中static文件夹下
    path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')


    with open(path, 'w')as file:
        file.write(html_data)