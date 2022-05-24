# Generated by Django 3.0.3 on 2022-05-24 04:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60)),
                ('winning_points', models.PositiveIntegerField(default=11)),
                ('winning_point_differential', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='DailyWordle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('word', models.CharField(max_length=5)),
                ('guesses', models.PositiveSmallIntegerField()),
                ('date', models.DateField(auto_now_add=True, unique=True)),
                ('time', models.DurationField()),
                ('player', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'wordle',
                'verbose_name_plural': 'wordles',
                'db_table': 'wordle',
            },
        ),
        migrations.CreateModel(
            name='ActiveWordle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField(auto_now_add=True, unique=True)),
                ('guess_history', models.CharField(blank=True, max_length=30)),
                ('word', models.CharField(max_length=5)),
                ('player', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'active_wordle',
                'verbose_name_plural': 'active_wordles',
                'db_table': 'active_wordle',
            },
        ),
    ]
