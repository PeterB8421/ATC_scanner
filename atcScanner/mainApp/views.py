import glob
import json
import os.path

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from datetime import date
from .models import Recording
from .forms import SettingsForm
from scripts.pipeline import get_config


def index(request):
    recordings = Recording.objects.order_by('-date')[:20]
    for rec in recordings:
        rec.file_name = os.path.basename(rec.file_path)
        rec.month_str = f'{rec.date.month:02d}'
        rec.day_str = f'{rec.date.day:02d}'

    base_path = '/data/out'
    years = []
    for name in os.listdir(base_path):
        full = os.path.join(base_path, name)
        if os.path.isdir(full) and len(name) == 4 and name.isdigit():
            years.append(name)
    return render(request, 'index.html', {'recordings': recordings, 'years': years})


def detail(request, year, month, day, fname=None, pk=None):
    if fname is None and pk is None:
        return HttpResponse('Incorrect URL', status=404)
    if pk is not None:
        recording = get_object_or_404(Recording, pk=pk)
        recording.file_name = os.path.basename(recording.file_path)
    else:
        fpath = os.path.join('/data/out', year, month, day, fname)
        with open(fpath.replace('.wav', '.json'), 'r') as f:
            metadata = json.load(f)

        kwargs = {
            'file_path': metadata['file_path'],
            'country': metadata['country'],
            'location': metadata['location'],
            'center_freq': metadata['center_freq'],
            'airport_codes': metadata['airport_codes'],
            'date': parse_datetime(metadata['date']),
            'snr': metadata['snr'],
        }

        recording = Recording(**kwargs)
        recording.file_name = fname
    return render(request, 'detail.html', {'recording': recording, 'year': year, 'month': month, 'day': day})


def year(request, year):
    base_path = '/data/out/' + year
    months = []
    for name in os.listdir(base_path):
        full = os.path.join(base_path, name)
        if os.path.isdir(full) and len(name) == 2 and name.isdigit():
            months.append(name)
    for m in months:
        m.lstrip('0')
    return render(request, 'year.html', {'months': months, 'year': year})


def month(request, year, month):
    base_path = '/data/out/' + year + '/' + month
    days = []
    for name in os.listdir(base_path):
        full = os.path.join(base_path, name)
        if os.path.isdir(full) and len(name) == 2 and name.isdigit():
            days.append(name)
    return render(request, 'month.html', {'days': days, 'year': year, 'month': month})


def day(request, year, month, day):
    base_path = '/data/out/' + year + '/' + month + '/' + day
    recs = glob.glob(base_path + '/*.wav')
    recs = [os.path.basename(path) for path in recs]
    return render(request, 'day.html', {'recs': recs, 'year': year, 'month': month, 'day': day})


def settings(request):
    if request.method == "GET":
        form = SettingsForm(get_config())
        return render(request, 'settings.html', {"form": form})
    elif request.method == "POST":
        form = SettingsForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['file_ext'] == '.cs16':
                form.cleaned_data['script_name'] = 'decode_cs16.sh'
            elif form.cleaned_data['file_ext'] == '.cf32':
                form.cleaned_data['script_name'] = 'decode_cf32.sh'
            else:
                messages.error(request, 'Unsupported input file type')
                return render(request, 'settings.html', {'form': form})
            with open('/app/scripts/conf/pipeline.json', 'w') as f:
                json.dump(form.cleaned_data, f, indent=2, sort_keys=True)
            messages.success(request, 'Settings saved, restarting pipeline service')
            with open('/app/shared/restart_pipeline.flag', 'w') as f:
                f.write('restart')
            return render(request, 'settings.html', {"form": form})
    else:
        return HttpResponse("Method Not Allowed", status=400)
