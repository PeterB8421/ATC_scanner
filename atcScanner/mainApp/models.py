from django.db import models
from django.urls import reverse


class Recording(models.Model):
    file_path = models.FilePathField()
    country = models.CharField(max_length=60)
    location = models.CharField(max_length=20)
    center_freq = models.FloatField()
    airport_codes = models.CharField(max_length=80)
    date = models.DateTimeField()
    snr = models.FloatField()
    duration = models.FloatField()
    transcript = models.TextField()

    def get_absolute_url(self):
        return reverse('detail', kwargs={
            'year': self.date.strftime('%Y'),
            'month': self.date.strftime('%m'),
            'day': self.date.strftime('%d'),
            'pk': self.pk
        })
