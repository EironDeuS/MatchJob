# Generated by Django 5.2 on 2025-06-19 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionOfertas', '0030_postulacion_estado_ia_analisis_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='postulacion',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('match', 'Match'), ('contratado', 'Contratado'), ('rechazado', 'Rechazado'), ('finalizado', 'Finalizado')], default='pendiente', max_length=20, verbose_name='Estado'),
        ),
    ]
