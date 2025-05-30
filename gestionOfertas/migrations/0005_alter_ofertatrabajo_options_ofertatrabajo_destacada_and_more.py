# Generated by Django 5.1.7 on 2025-04-23 22:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionOfertas', '0004_remove_personanatural_direccion_usuario_direccion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ofertatrabajo',
            options={'ordering': ['-destacada', '-fecha_publicacion'], 'verbose_name': 'Oferta de Trabajo', 'verbose_name_plural': 'Ofertas de Trabajo'},
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='destacada',
            field=models.BooleanField(default=False, help_text='Ofertas destacadas aparecen primero', verbose_name='Oferta destacada'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='empresa',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ofertas_publicadas', to='gestionOfertas.empresa', verbose_name='Empresa ofertante'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ofertas', to='gestionOfertas.categoria', verbose_name='Categoría'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='creador',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ofertas_creadas', to=settings.AUTH_USER_MODEL, verbose_name='Usuario creador'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='tipo_contrato',
            field=models.CharField(blank=True, choices=[('tiempo_completo', 'Tiempo completo'), ('medio_tiempo', 'Medio tiempo'), ('por_proyecto', 'Por proyecto'), ('temporal', 'Temporal'), ('freelance', 'Freelance')], max_length=50, verbose_name='Tipo de contrato'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['empresa'], name='gestionOfer_empresa_7fd74b_idx'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['esta_activa'], name='gestionOfer_esta_ac_8d6d79_idx'),
        ),
    ]
