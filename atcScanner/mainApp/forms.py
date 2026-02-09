from django import forms

FILE_TYPES = [
    ('.cs16', 'cs16'),
    ('.cf32', 'cf32'),
]

class SettingsForm(forms.Form):
    sleep_time = forms.IntegerField(min_value=1, label='Sleep time', help_text='How long to wait between checking for new files (in seconds)')
    # file_ext = forms.CharField(max_length=20, label='Raw file extension', help_text='Extension of raw files to look for')
    file_ext = forms.ChoiceField(choices=FILE_TYPES)
    snr_thres = forms.FloatField(label='SNR threshold')
    # script_name = forms.CharField(max_length=100, label='Filename of raw file processing script')
    country = forms.CharField(max_length=60, label='Country')
    location = forms.CharField(max_length=30, label='GPS location')
    center_freq = forms.FloatField(min_value=0, step_size=0.1, label='Center frequency')
    airport_codes = forms.CharField(max_length=40, label='Airport codes')
