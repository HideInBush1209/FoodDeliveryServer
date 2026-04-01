import json
import logging
import os
from django.http import JsonResponse
from django.shortcuts import render
from wxcloudrun.models import Counters
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('log')


def index(request, _):
    """
    获取主页

     `` request `` 请求对象
    """

    return render(request, 'index.html')


def counter(request, _):
    """
    获取当前计数

     `` request `` 请求对象
    """

    rsp = JsonResponse({'code': 0, 'errorMsg': ''}, json_dumps_params={'ensure_ascii': False})
    if request.method == 'GET' or request.method == 'get':
        rsp = get_count()
    elif request.method == 'POST' or request.method == 'post':
        rsp = update_count(request)
    else:
        rsp = JsonResponse({'code': -1, 'errorMsg': '请求方式错误'},
                            json_dumps_params={'ensure_ascii': False})
    logger.info('response result: {}'.format(rsp.content.decode('utf-8')))
    return rsp


def get_count():
    """
    获取当前计数
    """

    try:
        data = Counters.objects.get(id=1)
    except Counters.DoesNotExist:
        return JsonResponse({'code': 0, 'data': 0},
                    json_dumps_params={'ensure_ascii': False})
    return JsonResponse({'code': 0, 'data': data.count},
                        json_dumps_params={'ensure_ascii': False})


def update_count(request):
    """
    更新计数，自增或者清零

    `` request `` 请求对象
    """

    logger.info('update_count req: {}'.format(request.body))

    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)

    if 'action' not in body:
        return JsonResponse({'code': -1, 'errorMsg': '缺少action参数'},
                            json_dumps_params={'ensure_ascii': False})

    if body['action'] == 'inc':
        try:
            data = Counters.objects.get(id=1)
        except Counters.DoesNotExist:
            data = Counters()
        data.id = 1
        data.count += 1
        data.save()
        return JsonResponse({'code': 0, "data": data.count},
                    json_dumps_params={'ensure_ascii': False})
    elif body['action'] == 'clear':
        try:
            data = Counters.objects.get(id=1)
            data.delete()
        except Counters.DoesNotExist:
            logger.info('record not exist')
        return JsonResponse({'code': 0, 'data': 0},
                    json_dumps_params={'ensure_ascii': False})
    else:
        return JsonResponse({'code': -1, 'errorMsg': 'action参数错误'},
                    json_dumps_params={'ensure_ascii': False})

@csrf_exempt
@require_http_methods(["POST"])
def order_notify(request):
    try:
        data = json.loads(request.body)
        order_items = data.get('orderItems', [])
        timestamp = data.get('timestamp', '')

        if not order_items:
            return JsonResponse({"code": 0, "msg": "no orders"})

        # 组装邮件内容
        message = f"【新订单通知】\n时间：{timestamp}\n"
        for idx, item in enumerate(order_items, 1):
            store = item.get('storeName', '')
            product = item.get('productName', '')
            temp = item.get('temperature', '')
            line = f"{idx}. {store} - {product}"
            if temp:
                line += f" ({temp})"
            message += line + "\n"

        logger.info(message)

        # 发送邮件给管理员
        admin_email = os.environ.get('ADMIN_EMAIL', '')
        if admin_email:
            try:
                send_mail(
                    subject='点餐小程序新订单通知',
                    message=message,
                    from_email=None,  # 使用 settings.DEFAULT_FROM_EMAIL
                    recipient_list=[admin_email],
                    fail_silently=False,
                )
                logger.info(f"邮件已发送至 {admin_email}")
            except Exception as e:
                logger.error(f"邮件发送失败: {e}")
        else:
            logger.warning("未配置 ADMIN_EMAIL，未发送邮件")

        return JsonResponse({"code": 0, "msg": "success"})

    except Exception as e:
        logger.error(f"订单通知处理失败: {str(e)}")
        return JsonResponse({"code": -1, "msg": str(e)})