"""
Author: Bc. Petr Balok
"""

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Recording(models.Model):
    """
    Recording metadata
    """
    file_path = models.FilePathField()
    country = models.CharField(max_length=60)
    location = models.CharField(max_length=20)
    center_freq = models.FloatField()
    freq = models.FloatField()
    airport_codes = models.CharField(max_length=80)
    code = models.CharField(max_length=10)
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


class Transcripts(models.Model):
    """
    Link file path and job id for transcripts
    """
    file_path = models.FilePathField()
    job_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50)


class Deleted(models.Model):
    """
    Deleted recordings and reasons for deletion
    """
    class DeletionReason(models.TextChoices):
        EMPTY_FILE = 'empty_file', _('Empty file')
        SNR = 'snr', _('SNR threshold')
        TOO_SHORT = 'short', _('Audio too short')
        TOO_LONG = 'long', _('Audio too long')
        USER = 'user', _('User deleted')
        UNK = 'unk', _('Unknown')
    file_path = models.FilePathField()
    reason = models.CharField(max_length=30, choices=DeletionReason.choices, default=DeletionReason.UNK)
    snr_thres = models.FloatField(blank=True, null=True)
    short_limit = models.FloatField(blank=True, null=True)
    long_limit = models.FloatField(blank=True, null=True)
    date = models.DateTimeField()
    duration = models.FloatField(blank=True, null=True)
    snr = models.FloatField(blank=True, null=True)
