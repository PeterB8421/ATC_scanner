import glob
import json
import os.path
import math

from pathlib import Path
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.db import OperationalError
from django.db.models import Count
from django.db.models.functions import TruncDay
from datetime import date
from .models import Recording
from .forms import SettingsForm
from config_utils import get_config


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


def _parse_json_files(json_files):
    # Reads JSON metadata in case the db fails
    parsed_data = []
    for j_file in json_files:
        try:
            with open(j_file, 'r') as f:
                meta = json.load(f)

            d = parse_datetime(meta['date'])

            abs_url = f"/{d.strftime('%Y/%m/%d')}/{os.path.basename(meta['file_path'])}"

            parsed_data.append({
                'id'       : None,  # No database ID exists
                'file_path': meta['file_path'],
                'file_name': os.path.basename(meta['file_path']),
                'date'     : meta['date'],
                'snr'      : meta['snr'],
                'abs_url'  : abs_url,
                'duration' : meta['duration'],
            })
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return parsed_data


def get_recs_from_disk(filter_date, sort_key):
    # Read metadata files from disk in case of db error
    base_path = Path('/data/out')
    data = []

    if not base_path.exists():
        return data

    # Filter by given date
    if filter_date:
        try:
            year, month, day = filter_date.split('-')
            target_path = base_path / year / month / day

            if target_path.exists() and target_path.is_dir():
                json_files = list(target_path.glob('*.json'))
                data = _parse_json_files(json_files)
        except ValueError:
            pass  # Invalid date format

    # If filter_date wasn't provided, get the day with most recent data
    else:
        # Get the newest year
        years = sorted([d for d in base_path.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)

        if years:
            newest_year = years[0]

            # Get the newest Month
            months = sorted([d for d in newest_year.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)

            if months:
                newest_month = months[0]

                # Get the newest Day
                days = sorted([d for d in newest_month.iterdir() if d.is_dir()], key=lambda x: x.name, reverse=True)

                if days:
                    newest_day = days[0]

                    json_files = list(newest_day.glob('*.json'))
                    data = _parse_json_files(json_files)
    reverse_sort = sort_key.startswith('-')
    sort_field = sort_key.lstrip('-')

    if sort_field in ['date', 'snr', 'duration']:
        data.sort(key=lambda x: x.get(sort_field, 0) if x.get(sort_field) is not None else 0, reverse=reverse_sort)

    return data


def get_recs(request):
    # API endpoint to retrieve recordings from db or disk
    sort_key = request.GET.get('sort')
    filter_date = request.GET.get('filter_date')

    try:
        page_nr = int(request.GET.get('page', 1))
    except ValueError:
        page_nr = 1

    allowed_keys = {
        'snr': 'snr',
        '-snr': '-snr',
        'date': 'date',
        '-date': '-date',
        'duration': 'duration',
        '-duration': '-duration',
    }

    if sort_key not in allowed_keys:
        return JsonResponse({
            'error': f'Invalid sort key: {sort_key}'
        }, status=400)

    sort = allowed_keys[sort_key]
    try:
        recordings = Recording.objects.all()

        if filter_date:
            recordings = recordings.filter(date__date=filter_date)

        recordings = recordings.order_by(sort)
        total_recs = len(recordings)

        paginator = Paginator(recordings, 20)
        page_obj = paginator.get_page(page_nr)

        for rec in recordings:
            rec.file_name = os.path.basename(rec.file_path)
            rec.month_str = f'{rec.date.month:02d}'
            rec.day_str = f'{rec.date.day:02d}'
            rec.abs_url = rec.get_absolute_url()

        data = []
        for rec in page_obj.object_list:
            data.append({
                'id': rec.id,
                'file_path': rec.file_path,
                'file_name': rec.file_name,
                'date': rec.date,
                'snr': rec.snr,
                'abs_url': rec.abs_url,
                'duration': rec.duration,
            })

        response_data = {
            'data': data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_recs': total_recs,
            }
        }
        response = JsonResponse(response_data, safe=False)
        response['X-Fallback-Mode'] = 'false'
        return response

    except OperationalError:
        fallback_data = get_recs_from_disk(filter_date, sort_key)

        total_items = len(fallback_data)
        total_pages = math.ceil(total_items / 20) if total_items > 0 else 1

        if page_nr < 1: page_nr = 1
        if page_nr > total_pages: page_nr = total_pages

        start_idx = (page_nr - 1) * 20
        end_idx = start_idx + 20
        paged_data = fallback_data[start_idx:end_idx]

        response_data = {
            'data'      : paged_data,
            'pagination': {
                'current_page': page_nr,
                'total_pages' : total_pages,
                'has_next'    : page_nr < total_pages,
                'has_previous': page_nr > 1,
                'total_recs' : total_items,
            }
        }

        response = JsonResponse(response_data, safe=False)
        response['X-Fallback-Mode'] = 'true'
        return response


def get_month_counts(request):
    year = request.GET.get('year')
    month = request.GET.get('month')

    day_counts = {}

    try:
        recs = Recording.objects.filter(date__year=year, date__month=month).annotate(day=TruncDay('date')).values('day').annotate(count=Count('id'))

        for rec in recs:
            day_str = rec['day'].strftime('%Y-%m-%d')
            day_counts[day_str] = rec['count']
    except OperationalError:
        # Fallback if there is db error
        month_path = Path(f'/data/out/{year}/{month}')

        if month_path.exists() and month_path.is_dir():
            for day_dir in month_path.iterdir():
                if day_dir.is_dir():
                    file_count = len(list(day_dir.glob('*.wav')))
                    if file_count > 0:
                        date_key = f'{year}-{month}-{day_dir.name}'
                        day_counts[date_key] = file_count

    return JsonResponse(day_counts)


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
    recording.metadata_file_path = recording.file_path.replace('.wav', '.json')
    recording.metadata_file_name = os.path.basename(recording.file_name.replace('.wav', '.json'))
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
