from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Disciplina(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Equipamiento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Rutina(models.Model):
    class Nivel(models.TextChoices):
        BASICO = 'basico', 'Básico'
        INTERMEDIO = 'intermedio', 'Intermedio'
        AVANZADO = 'avanzado', 'Avanzado'

    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    duracion_minutos = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(120)]
    )
    cupos = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(30)]
    )
    nivel = models.CharField(
        max_length=12, choices=Nivel.choices, default=Nivel.BASICO
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Dueño de la rutina
    entrenador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rutinas',
    )
    # Catálogo opcional.
    # Si se elimina una disciplina, las rutinas NO se borran: quedan "sin disciplina".
    # Justificación (req. 12): el catálogo es opcional en el caso, así que una rutina
    # puede existir sin él. CASCADE borraría rutinas (y sus inscripciones) de otros
    # entrenadores por eliminar un dato de catálogo. PROTECT impediría borrar una
    # disciplina mientras alguna rutina la use, incluso si está mal escrita.
    # SET_NULL conserva el trabajo de los entrenadores y respeta la regla del caso.
    disciplina = models.ForeignKey(
        Disciplina,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rutinas',
    )
    # Etiquetas (crea la tabla intermedia sola)
    equipamientos = models.ManyToManyField(
        Equipamiento, blank=True, related_name='rutinas'
    )

    class Meta:
        ordering = ['-fecha_creacion', '-id']

    def __str__(self):
        return self.titulo


class Inscripcion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        CONFIRMADA = 'confirmada', 'Confirmada'
        RECHAZADA = 'rechazada', 'Rechazada'

    rutina = models.ForeignKey(
        Rutina, on_delete=models.CASCADE, related_name='inscripciones'
    )
    socio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscripciones',
    )
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )

    class Meta:
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['rutina', 'socio'],
                name='inscripcion_unica_por_socio_y_rutina',
            )
        ]

    def clean(self):
        if self.rutina_id and self.socio_id and self.rutina.entrenador_id == self.socio_id:
            raise ValidationError('No puedes inscribirte en tu propia rutina.')

    def __str__(self):
        return f'{self.socio} → {self.rutina} ({self.estado})'