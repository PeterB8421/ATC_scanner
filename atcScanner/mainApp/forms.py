from django import forms


class SettingsForm(forms.Form):
    sleep_time = forms.IntegerField(min_value=1)
    file_ext = forms.CharField(max_length=20)
    script_name = forms.CharField(max_length=100)
    country = forms.CharField(max_length=60)
    location = forms.CharField(max_length=30)
    center_freq = forms.FloatField(min_value=0, step_size=0.1)
    airport_codes = forms.CharField(max_length=40)
