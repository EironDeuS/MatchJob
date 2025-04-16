# Generated by Django 5.1.7 on 2025-04-16 00:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('gestionOfertas', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cv',
            options={'ordering': ['-fecha_subida'], 'verbose_name': 'Currículum Vitae', 'verbose_name_plural': 'Currículos Vitae'},
        ),
        migrations.AlterModelOptions(
            name='empresa',
            options={'ordering': ['nombre_empresa'], 'verbose_name': 'Empresa', 'verbose_name_plural': 'Empresas'},
        ),
        migrations.AlterModelOptions(
            name='experiencialaboral',
            options={'ordering': ['-fecha_inicio'], 'verbose_name': 'Experiencia Laboral', 'verbose_name_plural': 'Experiencias Laborales'},
        ),
        migrations.AlterModelOptions(
            name='ofertatrabajo',
            options={'ordering': ['-fecha_publicacion'], 'verbose_name': 'Oferta de Trabajo', 'verbose_name_plural': 'Ofertas de Trabajo'},
        ),
        migrations.AlterModelOptions(
            name='personanatural',
            options={'ordering': ['apellidos', 'nombres'], 'verbose_name': 'Persona Natural', 'verbose_name_plural': 'Personas Naturales'},
        ),
        migrations.AlterModelOptions(
            name='postulacion',
            options={'ordering': ['-fecha_postulacion'], 'verbose_name': 'Postulación', 'verbose_name_plural': 'Postulaciones'},
        ),
        migrations.AlterModelOptions(
            name='usuario',
            options={'ordering': ['fecha_creacion'], 'verbose_name': 'Usuario', 'verbose_name_plural': 'Usuarios'},
        ),
        migrations.RemoveField(
            model_name='empresa',
            name='id',
        ),
        migrations.RemoveField(
            model_name='empresa',
            name='razon_cial',
        ),
        migrations.RemoveField(
            model_name='ofertatrabajo',
            name='fecha_oferta',
        ),
        migrations.AddField(
            model_name='categoria',
            name='activa',
            field=models.BooleanField(default=True, verbose_name='Activa'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='descripcion',
            field=models.TextField(blank=True, verbose_name='Descripción'),
        ),
        migrations.AddField(
            model_name='categoria',
            name='icono',
            field=models.CharField(blank=True, help_text='Clase de icono para mostrar en la interfaz', max_length=50, verbose_name='Icono'),
        ),
        migrations.AddField(
            model_name='cv',
            name='fecha_actualizacion',
            field=models.DateField(auto_now=True, null=True, verbose_name='Fecha de actualización'),
        ),
        migrations.AddField(
            model_name='cv',
            name='habilidades',
            field=models.TextField(blank=True, verbose_name='Habilidades destacadas'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='activa',
            field=models.BooleanField(default=True, verbose_name='Activa'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='fecha_registro',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de registro'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='razon_social',
            field=models.CharField(max_length=100, null=True, verbose_name='Razón social'),
        ),
        migrations.AddField(
            model_name='experiencialaboral',
            name='actualmente',
            field=models.BooleanField(default=False, verbose_name='Actualmente trabajando aquí'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='activa',
            field=models.BooleanField(default=True, verbose_name='Activa'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='beneficios',
            field=models.TextField(blank=True, verbose_name='Beneficios'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='fecha_cierre',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de cierre'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='fecha_publicacion',
            field=models.DateField(auto_now_add=True, null=True, verbose_name='Fecha de publicación'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='requisitos',
            field=models.TextField(blank=True, verbose_name='Requisitos'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='salario',
            field=models.CharField(blank=True, max_length=100, verbose_name='Salario'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='tipo_contrato',
            field=models.CharField(blank=True, max_length=50, verbose_name='Tipo de contrato'),
        ),
        migrations.AddField(
            model_name='ofertatrabajo',
            name='ubicacion',
            field=models.CharField(blank=True, max_length=100, verbose_name='Ubicación'),
        ),
        migrations.AddField(
            model_name='postulacion',
            name='cv',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestionOfertas.cv', verbose_name='CV enviado'),
        ),
        migrations.AddField(
            model_name='postulacion',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('revisado', 'Revisado'), ('entrevista', 'Entrevista'), ('contratado', 'Contratado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=20, verbose_name='Estado'),
        ),
        migrations.AddField(
            model_name='postulacion',
            name='feedback',
            field=models.TextField(blank=True, verbose_name='Feedback'),
        ),
        migrations.AddField(
            model_name='postulacion',
            name='mensaje',
            field=models.TextField(blank=True, verbose_name='Mensaje del postulante'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='fecha_actualizacion',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='Fecha de actualización'),
        ),
        migrations.AddField(
            model_name='usuario',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='Fecha de creación'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='archivo_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='URL del archivo'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='correo',
            field=models.EmailField(max_length=254, verbose_name='Correo de contacto'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='experiencia',
            field=models.TextField(blank=True, verbose_name='Resumen de experiencia'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='fecha_subida',
            field=models.DateField(auto_now_add=True, null=True, verbose_name='Fecha de subida'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='nombre',
            field=models.CharField(max_length=100, verbose_name='Título del CV'),
        ),
        migrations.AlterField(
            model_name='cv',
            name='persona',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cv', to='gestionOfertas.personanatural', verbose_name='Persona'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='giro',
            field=models.CharField(max_length=100, verbose_name='Giro comercial'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='nombre_empresa',
            field=models.CharField(max_length=100, verbose_name='Nombre de la empresa'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='rut_empresa',
            field=models.CharField(help_text='Formato: 12345678-9', max_length=12, unique=True, verbose_name='RUT Empresa'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='usuario',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='empresa', serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='Usuario asociado'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='cv',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='experiencias', to='gestionOfertas.cv', verbose_name='CV asociado'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='descripcion',
            field=models.TextField(blank=True, verbose_name='Descripción de funciones'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='fecha_inicio',
            field=models.DateField(verbose_name='Fecha de inicio'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='fecha_termino',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de término'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='nombre_empresa',
            field=models.CharField(max_length=100, verbose_name='Nombre de la empresa'),
        ),
        migrations.AlterField(
            model_name='experiencialaboral',
            name='puesto',
            field=models.CharField(max_length=100, verbose_name='Puesto ocupado'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='categoria',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ofertas', to='gestionOfertas.categoria', verbose_name='Categoría'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='descripcion',
            field=models.TextField(verbose_name='Descripción del puesto'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ofertas', to='gestionOfertas.empresa', verbose_name='Empresa'),
        ),
        migrations.AlterField(
            model_name='ofertatrabajo',
            name='nombre',
            field=models.CharField(max_length=100, verbose_name='Título de la oferta'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='apellidos',
            field=models.CharField(max_length=100, verbose_name='Apellidos'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='direccion',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Dirección'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='fecha_nacimiento',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de nacimiento'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='nacionalidad',
            field=models.CharField(default='Chilena', max_length=50, verbose_name='Nacionalidad'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='nombres',
            field=models.CharField(max_length=100, verbose_name='Nombres'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='rut',
            field=models.CharField(help_text='Formato: 12345678-9', max_length=12, verbose_name='RUT'),
        ),
        migrations.AlterField(
            model_name='personanatural',
            name='usuario',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='personanatural', serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='Usuario asociado'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='fecha_postulacion',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Fecha de postulación'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='oferta',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postulaciones', to='gestionOfertas.ofertatrabajo', verbose_name='Oferta'),
        ),
        migrations.AlterField(
            model_name='postulacion',
            name='persona',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postulaciones', to='gestionOfertas.personanatural', verbose_name='Postulante'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='correo',
            field=models.EmailField(max_length=254, unique=True, verbose_name='Correo electrónico'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Activo'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='is_staff',
            field=models.BooleanField(default=False, verbose_name='Acceso administrador'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='telefono',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Teléfono'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='tipo_usuario',
            field=models.CharField(choices=[('persona', 'Persona Natural'), ('empresa', 'Empresa'), ('admin', 'Administrador')], default='persona', max_length=20, verbose_name='Tipo de usuario'),
        ),
        migrations.AlterField(
            model_name='usuario',
            name='username',
            field=models.CharField(help_text='RUT en formato 12345678-9', max_length=50, unique=True, verbose_name='RUT/Username'),
        ),
        migrations.AlterUniqueTogether(
            name='postulacion',
            unique_together={('persona', 'oferta')},
        ),
        migrations.AddIndex(
            model_name='empresa',
            index=models.Index(fields=['nombre_empresa'], name='gestionOfer_nombre__94ee61_idx'),
        ),
        migrations.AddIndex(
            model_name='empresa',
            index=models.Index(fields=['rut_empresa'], name='gestionOfer_rut_emp_7e3628_idx'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['nombre'], name='gestionOfer_nombre_d337d8_idx'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['empresa'], name='gestionOfer_empresa_7fd74b_idx'),
        ),
        migrations.AddIndex(
            model_name='ofertatrabajo',
            index=models.Index(fields=['categoria'], name='gestionOfer_categor_b8af3a_idx'),
        ),
        migrations.AddIndex(
            model_name='postulacion',
            index=models.Index(fields=['persona'], name='gestionOfer_persona_651824_idx'),
        ),
        migrations.AddIndex(
            model_name='postulacion',
            index=models.Index(fields=['oferta'], name='gestionOfer_oferta__84570d_idx'),
        ),
        migrations.AddIndex(
            model_name='postulacion',
            index=models.Index(fields=['estado'], name='gestionOfer_estado_33dea9_idx'),
        ),
        migrations.AddIndex(
            model_name='usuario',
            index=models.Index(fields=['username'], name='gestionOfer_usernam_b71b38_idx'),
        ),
        migrations.AddIndex(
            model_name='usuario',
            index=models.Index(fields=['correo'], name='gestionOfer_correo_296fbb_idx'),
        ),
        migrations.AddIndex(
            model_name='usuario',
            index=models.Index(fields=['tipo_usuario'], name='gestionOfer_tipo_us_718e14_idx'),
        ),
        migrations.AlterModelTable(
            name='empresa',
            table=None,
        ),
    ]
