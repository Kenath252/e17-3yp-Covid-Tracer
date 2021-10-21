# Generated by Django 3.2.7 on 2021-10-21 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20210918_1414'),
    ]

    operations = [
        migrations.CreateModel(
            name='TraceLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=100)),
                ('percentage', models.FloatField(max_length=5)),
            ],
            options={
                'managed': True,
            },
        ),
    ]
