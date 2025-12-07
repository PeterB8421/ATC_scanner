import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from .models import Recording


def index(request):
    recordings = Recording.objects.order_by('-date')[:20]
    return render(request, 'index.html', {'recordings': recordings})


@csrf_exempt
def insert_rec(request):
    if request.method != 'POST':
        return HttpResponse(status=400)

    try:
        data = json.loads(request.body)
        data['date'] = date.fromisoformat(data['date'])
        new_rec = Recording.objects.create(file_path=data['file_path'], country=data['country'], location=data['location'],
                                           center_freq=data['center_freq'], airport_codes=data['airport_codes'])
        new_rec.save()
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
