from django import forms

FILE_TYPES = [
    ('.cs16', 'cs16'),
    ('.cf32', 'cf32'),
]


class SettingsForm(forms.Form):
    sleep_time = forms.IntegerField(min_value=1, label='Sleep time', help_text='How long to wait between checking for new files (in seconds)')
    file_ext = forms.ChoiceField(choices=FILE_TYPES, label='Input file type')
    min_audio_len = forms.IntegerField(min_value=0, label='Minimum audio length (in seconds)', help_text='Use 0 to process all files')
    snr_thres = forms.FloatField(label='SNR threshold', help_text='Files with SNR lower than this thershold will be automatically deleted')
    in_autodelete = forms.BooleanField(label='Delete input files after processing?', required=False)
    country = forms.CharField(max_length=60, label='Country')
    location = forms.CharField(max_length=30, label='GPS location')
    center_freq = forms.FloatField(min_value=0, step_size=0.1, label='Center frequency')
    airport_codes = forms.CharField(max_length=40, label='Airport codes')
