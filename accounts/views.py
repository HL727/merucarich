from django.shortcuts import render

from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.models import FJCMember
from settings_amazon.models import AmazonAPI


def _error_response(message):
    return JsonResponse({'message': message}, status=403)


@csrf_exempt
@require_POST
def fjc_member(request):
    ''' FJC Memberを取得するAPIです '''
    try:
        config = django_settings.FJC_MEMBER_CONFIG 
    except:
        config = {}
    token = request.POST.get('token')
    if token != config.get('TOKEN'):
        return _error_response('invalid parameters')

    member_list = []
    for api in AmazonAPI.objects.all():
        member_list.append({
            'account': api.account_id, 
            'username': api.author.username,
        })

    return JsonResponse({'fjc_members': member_list})

    
