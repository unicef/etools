# Generated by Django 1.10.8 on 2018-04-19 09:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tpm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tpmvisit',
            name='cancel_comment',
            field=models.TextField(blank=True, verbose_name='Cancel Comment'),
        ),        migrations.AlterField(
            model_name='tpmvisit',
            name='reject_comment',
            field=models.TextField(blank=True, verbose_name='Reason for Rejection'),
        ),
        migrations.AlterField(
            model_name='tpmvisitreportrejectcomment',
            name='reject_reason',
            field=models.TextField(verbose_name='Reason for Rejection'),
        ),
    ]
