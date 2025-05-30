# Generated by Django 5.2 on 2025-04-23 02:13

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionOfertas', '0002_alter_cv_options_alter_empresa_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Valoracion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntuacion', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(blank=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Valoración',
                'verbose_name_plural': 'Valoraciones',
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.AlterModelOptions(
            name='cv',
            options={'verbose_name': 'CV', 'verbose_name_plural': 'CVs'},
        ),
        migrations.RemoveIndex(
            model_name='empresa',
            name='gestionOfer_rut_emp_7e3628_idx',
        ),
        migrations.RemoveIndex(
            model_name='ofertatrabajo',
            name='gestionOfer_empresa_7fd74b_idx',
        ),
        migrations.RenameField(
            model_name='cv',
            old_name='experiencia',
            new_name='experiencia_resumen',
        ),
        migrations.RenameField(
            model_name='ofertatrabajo',
            old_name='activa',
            new_name='esta_activa',
        ),
        migrations.RemoveField(
            model_name='cv',
            name='archivo_url',
        ),
        migrations.RemoveField(
            model_name='empresa',
            name='rut_empresa',
        ),
        migrations.RemoveField(
            model_name='ofertatrabajo',
            name='empresa',
        ),
        migrations.RemoveField(
            model_name='personanatural',
            name='rut',
        ),
        migrations.RemoveField(
            model_name='postulacion',
            name='cv',
        ),
        migrations.AddField(
            model_name='cv',
            name='archivo_cv',
            field=models.FileField(blank=True, null=True, upload_to='cvs/', verbose_name='Archivo CV'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='pagina_web',
            field=models.URLField(blank=True, null=True, verbose_name='Página Web'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='redes_sociales',
            field=models.TextField(blank=True, null=True, verbose_name='Redes Sociales'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='creador',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='ofertas_creadas', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='postulacion',
            name='cv_enviado',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='gestionOfertas.cv', verbose_name='CV enviado'),
        ),
        migrations.AlterField(
            model_name='categoria',
            name='icono',
            field=models.CharField(blank=True, help_text='Clase de icono', max_length=50, verbose_name='Icono'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='correo',
            field=models.EmailField(blank=True, max_length=254, verbose_name='Correo de contacto'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='fecha_actualizacion',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='Fecha de actualización'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='fecha_subida',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de subida'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='nombre',
            field=models.CharField(blank=True, max_length=100, verbose_name='Título del CV'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='persona',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cv', to='gestionOfertas.personanatural'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='giro',
            field=models.CharField(blank=True, max_length=100, verbose_name='Giro comercial'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='nombre_empresa',
            field=models.CharField(blank=True, max_length=100, verbose_name='Nombre de la empresa'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='razon_social',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Razón social'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='cv',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiencias', to='gestionOfertas.cv'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ofertas', to='gestionOfertas.categoria'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='fecha_publicacion',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de publicación'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='apellidos',
            field=models.CharField(blank=True, max_length=100, verbose_name='Apellidos'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='nombres',
            field=models.CharField(blank=True, max_length=100, verbose_name='Nombres'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='oferta',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postulaciones_recibidas', to='gestionOfertas.ofertatrabajo'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='persona',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postulaciones', to='gestionOfertas.personanatural'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='is_staff',
            field=models.BooleanField(default=False, verbose_name='Acceso Admin Site'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='username',
            field=models.CharField(help_text='RUT para login', max_length=50, unique=True, verbose_name='RUT/Username'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['creador'], name='gestionOfer_creador_949159_idx'),
        ),
        migrations.AddField(
            model_name='valoracion',
            name='emisor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='valoraciones_emitidas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='valoracion',
            name='postulacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='valoraciones', to='gestionOfertas.postulacion'),
        ),
        migrations.AddField(
            model_name='valoracion',
            name='receptor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='valoraciones_recibidas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='valoracion',
            index=models.Index(fields=['emisor'], name='gestionOfer_emisor__6710df_idx'),
        ),
        migrations.AddIndex(
            model_name='valoracion',
            index=models.Index(fields=['receptor'], name='gestionOfer_recepto_426af0_idx'),
        ),
        migrations.AddIndex(
            model_name='valoracion',
            index=models.Index(fields=['postulacion'], name='gestionOfer_postula_4adc93_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='valoracion',
            unique_together={('emisor', 'receptor', 'postulacion')},
        ),
    ]
