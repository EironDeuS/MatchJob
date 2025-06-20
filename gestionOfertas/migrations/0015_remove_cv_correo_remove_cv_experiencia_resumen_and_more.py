# Generated by Django 5.2 on 2025-06-11 03:02

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionOfertas', '0014_postulacion_fecha_contratacion_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cv',
            name='correo',
        ),
        migrations.RemoveField(
            model_name='cv',
            name='experiencia_resumen',
        ),
        migrations.RemoveField(
            model_name='cv',
            name='habilidades',
        ),
        migrations.RemoveField(
            model_name='cv',
            name='nombre',
        ),
        migrations.AddField(
            model_name='cv',
            name='datos_analizados_ia',
            field=models.JSONField(blank=True, help_text='JSON completo de la información extraída del CV por la IA.', null=True, verbose_name='Datos analizados por IA'),
        ),
        migrations.AddField(
            model_name='cv',
            name='email_contacto',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='Correo de contacto'),
        ),
        migrations.AddField(
            model_name='cv',
            name='nombre_completo',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Nombre completo del CV'),
        ),
        migrations.AddField(
            model_name='cv',
            name='resumen_profesional',
            field=models.TextField(blank=True, null=True, verbose_name='Resumen profesional'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='fecha_actualizacion',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now, verbose_name='Fecha de actualización'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='cv',
            name='fecha_subida',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Fecha de subida'),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='CertificadoAntecedentes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo_pdf', models.FileField(help_text='Cargue el certificado de antecedentes en formato PDF.', upload_to='certificados_antecedentes/', verbose_name='Archivo PDF del Certificado')),
                ('rut_certificado', models.CharField(blank=True, max_length=12, verbose_name='RUT del certificado')),
                ('nombre_completo_certificado', models.CharField(blank=True, max_length=200, verbose_name='Nombre completo en certificado')),
                ('fecha_nacimiento_certificado', models.DateField(blank=True, null=True, verbose_name='Fecha de nacimiento en certificado')),
                ('tiene_antecedentes_penales', models.BooleanField(default=False, help_text='Marca si el certificado indica antecedentes penales.', verbose_name='¿Tiene antecedentes penales?')),
                ('fecha_emision', models.DateField(blank=True, null=True, verbose_name='Fecha de emisión del certificado')),
                ('fecha_carga', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de carga a la plataforma')),
                ('fecha_vencimiento', models.DateField(blank=True, help_text='Los certificados de antecedentes suelen tener una validez de 60 o 90 días. Se calculará automáticamente si no se provee.', null=True, verbose_name='Fecha de vencimiento')),
                ('esta_vigente', models.BooleanField(default=True, verbose_name='¿Está vigente?')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='certificado_antecedentes', to=settings.AUTH_USER_MODEL, verbose_name='Usuario asociado')),
            ],
            options={
                'verbose_name': 'Certificado de Antecedentes',
                'verbose_name_plural': 'Certificados de Antecedentes',
                'ordering': ['-fecha_emision'],
            },
        ),
        migrations.DeleteModel(
            name='ExperienciaLaboral',
        ),
        migrations.AddIndex(
            model_name='certificadoantecedentes',
            index=models.Index(fields=['usuario'], name='gestionOfer_usuario_4fa1f5_idx'),
        ),
        migrations.AddIndex(
            model_name='certificadoantecedentes',
            index=models.Index(fields=['esta_vigente'], name='gestionOfer_esta_vi_5a15a1_idx'),
        ),
        migrations.AddIndex(
            model_name='certificadoantecedentes',
            index=models.Index(fields=['tiene_antecedentes_penales'], name='gestionOfer_tiene_a_856846_idx'),
        ),
    ]
