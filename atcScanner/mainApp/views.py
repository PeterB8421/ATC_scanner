"""
Author: Bc. Petr Balok
"""

import glob
import json
import logging
import os.path
import math
import re
import zipfile

from pathlib import Path
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.db import OperationalError
from django.db.models.functions import TruncDay, TruncHour
from django.db.models import Count, Avg, Sum
from datetime import datetime
from .models import Recording, Transcripts, Deleted
from .forms import SettingsForm
from config_utils import get_config


def index(request):
    """ Homepage """
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


def delete_rec(request):
    """ Delete recording API endpoint """
    fpath = request.GET.get('file_path')
    if fpath is None:
        # File path unspecified
        return JsonResponse({'error': 'Invalid request!'}, status=400)
    if not fpath.startswith('/data/out/'):
        # Someone tried directory traversal
        return JsonResponse({'error': 'Invalid file path!'}, status=400)
    try:
        # Remove file from system disk
        os.remove(fpath)
        os.remove(fpath.replace('.wav', '.json'))
    except FileNotFoundError:
        return JsonResponse({'error': 'File not found!'}, status=400)

    except PermissionError:
        return JsonResponse({'error': 'No permission to delete file!'}, status=400)

    except IsADirectoryError:
        return JsonResponse({'error': 'Invalid file path!'}, status=400)

    except OSError as e:
        # Catch-all for any other OS-level issues
        return JsonResponse({'error': 'An unexpected OS error occurred!'}, status=400)

    try:
        # Remove database row
        Recording.objects.filter(file_path=fpath).delete()
    except OperationalError:
        logging.error(f'Database error occurred when deleting file {fpath}')
    try:
        # Add row to deleted files log
        Deleted.objects.create(
            file_path=fpath,
            reason=Deleted.DeletionReason.USER,
            date=datetime.now()
        )
    except OperationalError:
        logging.error('Database error occurred when inserting deletion log')
    return JsonResponse({'message': 'File deleted successfully!'}, status=200)


def get_monthly_snr(request):
    """ Returns average SNR for every day for specified month """
    try:
        year = request.GET.get('year', datetime.now().year)
        month = request.GET.get('month', datetime.now().month)

        daily_stats = (
            Recording.objects.filter(date__year=year, date__month=month)
            .annotate(day=TruncDay('date'))
            .values('day')
            .annotate(avg_snr=Avg('snr'))
            .order_by('day')
        )

        labels = []
        data = []
        for stat in daily_stats:
            if stat['day'] and stat['avg_snr'] is not None:
                labels.append(stat['day'].strftime('%d %b'))
                data.append(round(stat['avg_snr'], 2))
        response = JsonResponse({'labels': labels, 'data': data})
        response['X-Fallback-Mode'] = 'false'
    except OperationalError:
        # If database error occurred, return fallback mode header
        labels = []
        data = []
        response = JsonResponse({'labels': labels, 'data': data})
        response['X-Fallback-Mode'] = 'true'

    return response


def get_daily_snr(request):
    """ Endpoint that returns average SNR for every hour in specified day """
    try:
        date = request.GET.get('date')
        date = parse_datetime(date)
        year = date.year
        month = date.month
        day = date.day

        hourly_stats = (
            Recording.objects.filter(date__year=year, date__month=month, date__day=day)
            .annotate(hour=TruncHour('date'))
            .values('hour')
            .annotate(avg_snr=Avg('snr'))
            .order_by('hour')
        )

        labels = []
        data = []
        for stat in hourly_stats:
            if stat['hour'] and stat['avg_snr'] is not None:
                labels.append(stat['hour'].strftime('%H:00'))
                data.append(round(stat['avg_snr'], 2))
        response = JsonResponse({"labels": labels, "data": data})
        response['X-Fallback-Mode'] = 'false'
    except OperationalError:
        # If database error occurred, send fallback mode header
        labels = []
        data = []
        response = JsonResponse({"labels": labels, "data": data})
        response['X-Fallback-Mode'] = 'true'
    return response


def get_freqs_codes(request):
    """ Endpoint that returns distinct frequencies from database  """
    try:
        unique_freqs = Recording.objects.values_list('freq', flat=True).distinct()
        freq_list = list(unique_freqs)
        unique_codes = Recording.objects.values_list('code', flat=True).distinct()
        code_list = list(unique_codes)
        return JsonResponse({'freq_list': freq_list, 'code_list': code_list}, status=200)
    except OperationalError:
        # On database error, return empty list
        return JsonResponse({'freq_list': [], 'code_list': []}, status=500)


def _parse_json_files(json_files):
    """ Reads JSON metadata in case the db fails """
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
                'freq': meta['freq'],
                'code': meta['code'],
                'transcript': meta['transcript'],
            })
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return parsed_data


def get_recs_from_disk(filter_date, sort_key):
    """ Read metadata files from disk in case of db error """
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
    """ API endpoint to retrieve recordings from db or disk """
    sort_key = request.GET.get('sort')
    filter_date = request.GET.get('filter_date')
    filter_hour = request.GET.get('filter_hour')
    filter_freq = request.GET.get('freq')
    filter_code = request.GET.get('code')

    try:
        page_nr = int(request.GET.get('page', 1))
    except ValueError:
        # If provided page number wasn't int, reset to 1
        page_nr = 1

    # Allowed database columns used to sort the data
    allowed_keys = {
        'snr': 'snr',
        '-snr': '-snr',
        'date': 'date',
        '-date': '-date',
        'duration': 'duration',
        '-duration': '-duration',
    }

    if sort_key not in allowed_keys:
        # Return error if specified key was not allowed
        return JsonResponse({
            'error': f'Invalid sort key: {sort_key}'
        }, status=400)

    sort = allowed_keys[sort_key]
    try:
        # Try loading data from database at first
        recordings = Recording.objects.all()

        if filter_date:
            recordings = recordings.filter(date__date=filter_date)
        if filter_hour:
            recordings = recordings.filter(date__hour=filter_hour)
        if filter_freq:
            recordings = recordings.filter(freq=filter_freq)
        if filter_code:
            recordings = recordings.filter(code=filter_code)

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
                'freq': rec.freq,
                'code': rec.code,
                'transcript': rec.transcript,
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
        # In case of database error, load data from system disk
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
    """ Endpoint that returns number of recordings for each day in specified month """
    year = request.GET.get('year')
    month = request.GET.get('month')

    day_counts = {}

    try:
        # Try to retrieve counts from database
        recs = Recording.objects.filter(date__year=year, date__month=month).annotate(day=TruncDay('date')).values('day').annotate(count=Count('id'))

        for rec in recs:
            day_str = rec['day'].strftime('%Y-%m-%d')
            day_counts[day_str] = rec['count']
    except OperationalError:
        # Read from system disk if there is database error
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
    """ Detail page """
    if fname is None and pk is None:
        # File path or id was not provided
        return HttpResponse('Incorrect URL', status=404)
    if pk is not None:
        # If id was provided, load from database
        recording = get_object_or_404(Recording, pk=pk)
        recording.file_name = os.path.basename(recording.file_path)
    else:
        # Otherwise load from system disk
        fpath = os.path.join('/data/out', year, month, day, fname)
        with open(fpath.replace('.wav', '.json'), 'r') as f:
            metadata = json.load(f)  # Load metadata

        kwargs = {
            'file_path': metadata['file_path'],
            'country': metadata['country'],
            'location': metadata['location'],
            'center_freq': metadata['center_freq'],
            'airport_codes': metadata['airport_codes'],
            'date': parse_datetime(metadata['date']),
            'snr': metadata['snr'],
            'duration': metadata['duration'],
            'transcript': metadata['transcript'],
        }

        recording = Recording(**kwargs)
        recording.file_name = fname
    recording.metadata_file_path = recording.file_path.replace('.wav', '.json')
    recording.metadata_file_name = os.path.basename(recording.file_name.replace('.wav', '.json'))
    return render(request, 'detail.html', {'recording': recording, 'year': year, 'month': month, 'day': day})


def settings(request):
    """ Settings page """
    if request.method == "GET":
        # User wants to render the page
        form = SettingsForm(get_config('/scripts/conf/pipeline.json'))
        airport_data = get_config('/scripts/conf/pipeline.json').get('airports', [])
        return render(request, 'settings.html', {"form": form, 'airport_data': airport_data})

    elif request.method == "POST":
        # User saved settings
        form = SettingsForm(request.POST)

        if form.is_valid():
            if form.cleaned_data['min_audio_len'] > form.cleaned_data['max_audio_len']:
                messages.error(request, 'Minimum audio length must be lower than maximum audio length')
                return render(request, 'settings.html', {"form": form})

            if form.cleaned_data['file_ext'] == '.cs16':
                form.cleaned_data['script_name'] = 'decode_cs16.sh'
            elif form.cleaned_data['file_ext'] == '.cf32':
                form.cleaned_data['script_name'] = 'decode_cf32.sh'
            else:
                messages.error(request, 'Unsupported input file type')
                return render(request, 'settings.html', {'form': form})
            current_config = get_config('/scripts/conf/pipeline.json')

            current_config.update(form.cleaned_data)  # Update config JSON

            with open('/app/scripts/conf/pipeline.json', 'w') as f:
                json.dump(current_config, f, indent=2, sort_keys=True)

            messages.success(request, 'Settings saved, restarting pipeline service')

            with open('/app/shared/restart_pipeline.flag', 'w') as f:
                f.write('restart')  # Send signal to pipeline service to reload settings

            return render(request, 'settings.html', {"form": form})

    else:
        # Some other HTTP method was used
        return HttpResponse("Method Not Allowed", status=400)


@require_POST
def upload_airband_config(request):
    """ Endpoint to load channels from RTL Airband config """
    if 'airband_config' not in request.FILES:
        messages.error(request, 'No file was provided.')
        return redirect('settings')

    config_file = request.FILES['airband_config']

    try:
        # Read uploaded file
        content = config_file.read().decode('utf-8')

        # Remove commented lines
        content = re.sub(r'#.*', '', content)

        country_match = re.search(r'country\s*=\s*"([^"]+)"', content)
        location_match = re.search(r'location\s*=\s*"([^"]+)"', content)
        centerfreq_match = re.search(r'centerfreq\s*=\s*([\d.]+)', content)

        extracted_airports = {}

        # Split file into chunks by 'freq =' string to extract airport data
        chunks = content.split('freq =')

        # Skip the first chunk (top level data)
        for chunk in chunks[1:]:
            # Get frequency from current chunk
            freq_match = re.search(r'^\s*([\d.]+)', chunk)

            # Get label from current chunk
            label_match = re.search(r'(?:label|name)\s*=\s*"([^"]+)"', chunk)

            # Get airport code from current chunk
            airport_match = re.search(r'airport\s*=\s*"([^"]+)"', chunk)

            # Get filename template from given airport
            template_match = re.search(r'filename_template\s*=\s*"([^"]+)"', chunk)

            if freq_match and label_match:
                freq = float(freq_match.group(1))
                identifier = label_match.group(1)

                # Use explicit airport code if found, otherwise guess from the label prefix
                airport_code = airport_match.group(1) if airport_match else identifier.split('_')[0]

                # Use provided template, or fall back to a default
                template = template_match.group(1) if template_match else f"{identifier}_{{date}}_{{time}}.mp3"

                extracted_airports[identifier] = {
                    "code"     : airport_code,
                    "frequency": freq,
                    "template" : template
                }

        # Configuration path
        config_path = '/scripts/conf/pipeline.json'

        with open(config_path, 'r', encoding='utf-8') as f:
                pipeline_config = json.load(f)

        if country_match:
            pipeline_config["country"] = country_match.group(1)
        if location_match:
            pipeline_config["location"] = location_match.group(1)
        if centerfreq_match:
            pipeline_config["center_freq"] = float(centerfreq_match.group(1))

        if "airports" not in pipeline_config:
            pipeline_config["airports"] = {}

        pipeline_config["airports"] = extracted_airports

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(pipeline_config, f, indent=2)

        messages.success(request,
                         f'Successfully extracted {len(extracted_airports)} airports and updated the pipeline configuration! Click SAVE to apply changes!')

    except Exception as e:
        messages.error(request, f'Failed to process configuration file: {str(e)}')

    return redirect('settings')


def deleted_log(request):
    """ Deleted files log page """
    deleted_records = Deleted.objects.all().order_by('date')
    return render(request, 'deleted.html', {"deleted_records": deleted_records})


def get_del_log(request):
    """ Endpoint to get deleted files log list """
    try:
        page_nr = int(request.GET.get('page', 1))
    except ValueError:
        page_nr = 1

    reason_filter = request.GET.get('reason')

    delete_log = Deleted.objects.all().order_by('-date')
    if reason_filter:
        delete_log = delete_log.filter(reason=reason_filter)
    paginator = Paginator(delete_log, 100)
    page_obj = paginator.get_page(page_nr)

    data = []
    for d in page_obj.object_list:
        data.append({
            'id'        : d.id,
            'file_path' : d.file_path,
            'reason'    : d.reason,
            'reason_text': str(d.get_reason_display()),
            'snr_thres' : d.snr_thres,
            'short_limit': d.short_limit,
            'long_limit': d.long_limit,
            'date'      : d.date,
            'duration'  : d.duration,
            'snr'       : d.snr,
        })

    response_data = {
        'data'      : data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages' : paginator.num_pages,
            'has_next'    : page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_recs'  : len(delete_log),
        }
    }
    response = JsonResponse(response_data, safe=False)
    return response


def get_deletion_reasons(request):
    """ Endpoint to get distinct reasons for deletion """
    reasons_list = []

    for value, label in Deleted.DeletionReason.choices:
        reasons_list.append({
            "value": value,
            "label": str(label)
        })

    return JsonResponse({"reasons": reasons_list})


@csrf_exempt
@require_POST
def receive_transcription(request):
    """ Endpoint to receive transcription from ATC_transcriber container """
    try:
        data = json.loads(request.body)

        job_id = data.get('job_id')
        status = data.get('status')
        text = data.get('text')

        if not job_id:
            logging.debug("The payload didn't contain a job_id at all!")
            return JsonResponse({"error": "Missing job id"}, status=400)

        try:
            transcript_record = Transcripts.objects.get(job_id=job_id)
            file_path = transcript_record.file_path
        except Transcripts.DoesNotExist:
            logging.debug(f"Could not find job_id {job_id} in the database!")
            return JsonResponse({"error": "Job id not found in DB"}, status=400)

        transcript_record.status = status
        transcript_record.save()

        if status == "completed":
            final_text = text
        else:
            final_text = "[Transcription failed]"

        Recording.objects.filter(file_path=file_path).update(transcript=final_text)

        json_path = file_path.replace('.wav', '.json')
        try:
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    metadata = json.load(f)

                metadata['transcript'] = final_text

                with open(json_path, "w") as f:
                    json.dump(metadata, f, indent=2, sort_keys=True)
            else:
                logging.warning(f'JSON metadata file missing for "{file_path}"')
        except Exception as e:
            logging.error(f"Failed to write metadata for webhook: {e}")

        logging.info("Webhook transcript processed successfully")
        return JsonResponse({"message": "File processed successfully"}, status=200)
    except json.JSONDecodeError:
        logging.error("Received invalid JSON payload")
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        logging.error(f"Error occurred while processing transcript: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


def stats(request):
    """ Statistics page """
    return render(request, "stats.html")


def get_stats(request):
    """ Endpoint to get data for charts on statistics page """
    # RECORDINGS PER DAY & AVERAGE SNR
    daily_stats = (
        Recording.objects
        .annotate(day=TruncDay('date'))
        .values('day')
        .annotate(
            total_count=Count('id'),
            avg_snr=Avg('snr'),
            total_duration=Sum('duration')
        )
        .order_by('day')
    )

    # Format for charting libraries
    dates_label = []
    volume_data = []
    snr_data = []
    duration_data = []

    for stat in daily_stats:
        if stat['day']:  # Ensure date isn't null
            dates_label.append(stat['day'].strftime('%Y-%m-%d'))
            volume_data.append(stat['total_count'])
            # Round SNR to 2 decimal places, default to 0 if None
            snr_data.append(round(stat['avg_snr'], 2) if stat['avg_snr'] else 0)

            # Get total duration in hours
            raw_seconds = stat['total_duration'] or 0
            hours = raw_seconds / 3600
            duration_data.append(round(hours, 2))

    # DELETION REASONS BREAKDOWN
    deletion_stats = (
        Deleted.objects
        .values('reason')
        .annotate(count=Count('id'))
        .order_by('-count')  # Sort highest to lowest
    )

    deletion_labels = []
    deletion_data = []

    # Map the raw database values back to the human-readable strings
    reason_dict = dict(Deleted.DeletionReason.choices)

    for stat in deletion_stats:
        raw_reason = stat['reason']
        human_readable = reason_dict.get(raw_reason, "Unknown")

        deletion_labels.append(str(human_readable))
        deletion_data.append(stat['count'])

    processed_files = len(Recording.objects.all())
    deleted_files = len(Deleted.objects.all())

    airport_qs = (
        Recording.objects
        .exclude(code__isnull=True).exclude(code__exact='')  # Ignore blank ones
        .values('code')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]  # Grab the top 10 most active
    )

    airport_labels = [entry['code'] for entry in airport_qs]
    airport_counts = [entry['count'] for entry in airport_qs]

    # RETURN AS A UNIFIED JSON RESPONSE
    return JsonResponse({
        "timeline": {
            "labels": dates_label,
            "volume": volume_data,
            "snr": snr_data
        },
        "deletions": {
            "labels": deletion_labels,
            "data": deletion_data
        },
        "total": {
            "processed": processed_files,
            "deleted": deleted_files
        },
        "airports": {
            'airport_labels': airport_labels,
            'airport_counts': airport_counts
        },
        "duration": {
            "labels": dates_label,
            "duration": duration_data
        }
    })


def export_page(request):
    """ Export page """
    return render(request, 'export.html')


def new_export(request):
    """ Endpoint to create new export archive """
    date = datetime.now()
    year = request.GET.get('year')
    month = request.GET.get('month')
    day = request.GET.get('day')
    hour = request.GET.get('hour')

    if not all([year, month, day]):
        # If date wasn't specified, return error
        return JsonResponse({"error": "Year, month, and day are required"}, status=400)

    # Pad the numbers with zeros just in case the frontend sends "4" instead of "04"
    padded_month = str(month).zfill(2)
    padded_day = str(day).zfill(2)

    export_path = f'/data/out/{year}/{padded_month}/{padded_day}'

    if not os.path.exists(export_path):
        # If export path does not exist, return error
        return JsonResponse({"error": "No data found for this date"}, status=404)

    prefix = f'DAY-{year}-{padded_month}-{padded_day}'
    if hour is not None:
        padded_hour = str(hour).zfill(2)
        prefix = f'HOUR-{year}-{padded_month}-{padded_day}-{padded_hour}'

    # The final output archive name
    filename = date.strftime(f'{prefix}_%Y-%m-%d_%H-%M-%S.zip')
    export_dir = '/data/export'
    os.makedirs(export_dir, exist_ok=True)

    zip_filepath = os.path.join(export_dir, filename)

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:

            for root, dirs, files in os.walk(export_path):
                for file in files:

                    if hour is not None:
                        # Filename with hour
                        time_marker = f"_{year}{padded_month}{padded_day}_{padded_hour}"

                        # If that exact sequence isn't in the filename, skip it
                        if time_marker not in file:
                            continue

                    absolute_file_path = os.path.join(root, file)
                    relative_arc_path = os.path.relpath(absolute_file_path, export_path)

                    zipf.write(absolute_file_path, arcname=relative_arc_path)

        clean_filename = filename.replace('.zip', '')
        return JsonResponse({'filename': clean_filename}, status=200)

    except Exception as e:
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
        return JsonResponse({'error': str(e)}, status=500)


def get_export_archives(request):
    """ Endpoint to get list of created archives """
    export_path = '/data/export'
    if not os.path.exists(export_path):
        # If export directory does not exist, return error
        return JsonResponse({'files': []}, status=200)

    file_paths = glob.glob(f'{export_path}/*.zip')

    files_data = []
    for file_path in file_paths:
        # Get the raw size in bytes
        size_bytes = os.path.getsize(file_path)

        # Get size in MB
        size_mb = round(size_bytes / (1024 * 1024), 2)

        # Grab just the filename for cleaner UI display
        filename = os.path.basename(file_path)

        files_data.append({
            'path'      : file_path,
            'filename'  : filename,
            'size_bytes': size_bytes,
            'size_mb'   : size_mb
        })

    return JsonResponse({'files': files_data}, status=200)


def delete_export_archive(request):
    """ Endpoint to delete export archive """
    file_path = request.GET.get('file')
    if not file_path:
        # File path was not provided
        return JsonResponse({'error': "No file path provided!"}, status=400)
    if not file_path.startswith('/data/export/'):
        # Someone tried directory traversal
        return JsonResponse({'error': "Invalid file path!"}, status=400)
    if os.path.exists(file_path):
        os.remove(file_path)
        return JsonResponse({'message': "File successfully deleted!"}, status=200)
    else:
        return JsonResponse({'error': "File does not exist!"}, status=400)
