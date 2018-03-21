from django.contrib import admin
from goods.models import GoodsCategory, Goods, IndexPromotionBanner
from celery_tasks.tasks import generate_static_index_html
from django.core.cache import cache


# Register your models here.


class BaseAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        """保存数据/g更新数据时调用"""

        #执行父类的保存逻辑，实现数据的保存
        obj.save()

        #触发生成静态主页的异步任务
        generate_static_index_html.delay()

        #手动删除缓存的数据
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """删除数据时调用"""

        obj.delete()
        generate_static_index_html.delay()
        cache.delete('index_page_data')

class IndexPromotionBannerAdmin(BaseAdmin):
    """IndexPromotionBanner  模型类的管理类"""

    # list_display = [id]

    pass


class GoodsCategoryAdmin(BaseAdmin):

    # list_per_page = 10

    pass


class GoodsAdmin(BaseAdmin):

    pass

admin.site.register(GoodsCategory, GoodsCategoryAdmin)

admin.site.register(Goods, GoodsAdmin)

admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)