from django.db import models


class Recording(models.Model):
    file_path = models.FilePathField()
    country = models.CharField(max_length=60)
    location = models.CharField(max_length=20)
    center_freq = models.FloatField()
    airport_codes = models.CharField(max_length=80)
    date = models.DateTimeField()
