from django.conf.urls import url
from users import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    # 函数视图,注册http://127.0.0.1:8000/users/register
    # url(r'^register$', views.register,  name='register'),

    # 类视图, 注册: http://127.0.0.1:8000/users/register
    url(r'^register$', views.RegisterView.as_view(), name='register'),

    # 邮件激活 : http://127.0.0.1:8000/users/active/!@#$&(&*(GGDGKIYRGjusysgahaiuwqusagaasjwe76238238
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),

    # 登录 : http://127.0.0.1:8000/users/login
    url(r'^login$', views.LoginView.as_view(), name='login'),

    #退出登录
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),

    #收货地址
    url(r'^address$', views.AddressView.as_view(), name='address'),

    # url(r'^address$', login_required(views.AddressView.as_view()), name='address')

    # 个人信息 : http://127.0.0.1:8000/users/info
    url(r'info', views.UserInfoView.as_view(), name='info')
]