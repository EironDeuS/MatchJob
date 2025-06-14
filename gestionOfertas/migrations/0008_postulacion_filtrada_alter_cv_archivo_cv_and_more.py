# Generated by Django 5.2 on 2025-05-04 16:55

import gestionOfertas.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionOfertas', '0007_alter_ofertatrabajo_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='postulacion',
            name='filtrada',
            field=models.BooleanField(default=False, help_text='Indica si la postulación ha sido filtrada manualmente', verbose_name='Filtrada'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='archivo_cv',
            field=models.FileField(blank=True, null=True,upload_to='cvs/', verbose_name='Archivo CV'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('filtrado', 'Filtrado'), ('match', 'Match'), ('contratado', 'Contratado'), ('rechazado', 'Rechazado'), ('finalizado', 'Finalizado')], default='pendiente', max_length=20, verbose_name='Estado'),
        ),
        migrations.AddIndex(
            model_name='postulacion',
            index=models.Index(fields=['filtrada'], name='gestionOfer_filtrad_3de3aa_idx'),
        ),
    ]
