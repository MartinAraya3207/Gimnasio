from django.contrib import admin
from .models import Disciplina, Equipamiento, Rutina, Inscripcion


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Equipamiento)
class EquipamientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)


@admin.register(Rutina)
class RutinaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'entrenador', 'disciplina', 'nivel',
                    'duracion_minutos', 'cupos', 'fecha_creacion')
    list_filter = ('nivel', 'disciplina', 'entrenador')
    search_fields = ('titulo', 'descripcion', 'entrenador__username')
    filter_horizontal = ('equipamientos',)
    list_select_related = ('entrenador', 'disciplina')


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('rutina', 'socio', 'estado', 'fecha')
    list_filter = ('estado', 'fecha')
    search_fields = ('rutina__titulo', 'socio__username', 'comentario')
    list_select_related = ('rutina', 'socio')