import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from datetime import date
from .models import Recording
from .forms import SettingsForm
from scripts.pipeline import get_config


def index(request):
    recordings = Recording.objects.order_by('-date')[:20]
    return render(request, 'index.html', {'recordings': recordings})


def settings(request):
    if request.method == "GET":
        form = SettingsForm(get_config())
        return render(request, 'settings.html', {"form": form})
    elif request.method == "POST":
        form = SettingsForm(request.POST)
        if form.is_valid():
            with open('/app/scripts/conf/pipeline.json', 'w') as f:
                json.dump(form.cleaned_data, f)
            messages.success(request, 'Settings saved, restarting pipeline service')
            with open('/app/shared/restart_pipeline.flag', 'w') as f:
                f.write('restart')
            return render(request, 'settings.html', {"form": form})
    else:
        return HttpResponse("Method Not Allowed", status=400)
