# Generated by Django 3.2.6 on 2022-12-08 09:02

from django.db import migrations, models


def migrate_fpr_file_type(apps, schema_editor):
    FileType = apps.get_model('partners', 'FileType')
    FileType.objects.filter(name='Final Partnership Review').update(name='(Legacy) Final Partnership Review')


def migrate_fpr_file_type_backwards(apps, schema_editor):
    FileType = apps.get_model('partners', 'FileType')
    FileType.objects.filter(name='(Legacy) Final Partnership Review').update(name='Final Partnership Review')


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0106_merge_20221206_1550'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='final_review_approved',
            field=models.BooleanField(default=False, verbose_name='Final Review Approved'),
        ),
        migrations.AlterField(
            model_name='filetype',
            name='name',
            field=models.CharField(choices=[('FACE', 'FACE'), ('Progress Report', 'Progress Report'), ('(Legacy) Final Partnership Review', '(Legacy) Final Partnership Review'), ('Correspondence', 'Correspondence'), ('Supply/Distribution Plan', 'Supply/Distribution Plan'), ('Data Processing Agreement', 'Data Processing Agreement'), ('Activities involving children and young people', 'Activities involving children and young people'), ('Special Conditions for Construction Works', 'Special Conditions for Construction Works'), ('Other', 'Other')], max_length=64, unique=True, verbose_name='Name'),
        ),
        migrations.RunPython(migrate_fpr_file_type, migrate_fpr_file_type_backwards),
    ]
