from django.conf.urls import url
from orders import views


urlpatterns = [
    # 订单确认 : http://127.0.0.1:8000/orders/place (需要的sku_id和count存放在post请求体中)
    url(r'^place$', views.PlaceOrderView.as_view(), name='place'),

    # 提交订单 : http://127.0.0.1:8000/orders/commit (需要的sku_id和count存放在post请求体中)
    url(r'^commit$', views.CommitOrderView.as_view(), name='commit'),

    # 我的全部订单
    url(r'^(?P<page>\d+)$', views.UserOrdersView.as_view(), name='info'),

    #支付宝支付：http://127.0.0.1:8000/orders/pay

    url(r'^pay$', views.PayView.as_view(), name='pay'),

    # 支付宝查询:http://127.0.0.1:8000/orders/checkpay?order_id="+order_id"
    url(r'^checkpay$', views.CheckPayView.as_view(), name='checkpay'),

    #评价
    url('^comment/(?P<order_id>\d+)$', views.CommentView.as_view(), name="comment"),
]