# Cómo ejecutarlo (desde la carpeta donde está manage.py):
#   python manage.py shell -c "exec(open('cargar_datos.py', encoding='utf-8').read())"

from django.contrib.auth.models import User
from app_gim.models import Disciplina, Equipamiento, Rutina, Inscripcion


def usuario(nombre):
    u, _ = User.objects.get_or_create(username=nombre)
    u.set_password('1234')
    u.save()
    return u


# Usuarios
ent1 = usuario('entrenador1')
ent2 = usuario('entrenador2')
socio1 = usuario('socio1')

# Catálogo y etiquetas
disciplinas = [Disciplina.objects.get_or_create(nombre=n)[0]
               for n in ['Yoga', 'Funcional', 'Spinning']]
equipos = [Equipamiento.objects.get_or_create(nombre=n)[0]
           for n in ['Mancuernas', 'Banco', 'Colchoneta',
                     'Bandas elásticas', 'Bicicleta']]

# (título, duración, cupos, nivel, índice de disciplina, entrenador)
datos = [
    ('Yoga matutino', 45, 10, 'basico', 0, ent1),
    ('Yoga avanzado', 60, 8, 'avanzado', 0, ent1),
    ('Funcional express', 30, 15, 'basico', 1, ent1),
    ('Fuerza con mancuernas', 50, 12, 'intermedio', 1, ent1),
    ('Spinning suave', 40, 20, 'basico', 2, ent1),
    ('Spinning intenso', 55, 18, 'avanzado', 2, ent2),
    ('Funcional power', 45, 12, 'intermedio', 1, ent2),
    ('Yoga restaurativo', 60, 10, 'basico', 0, ent2),
    ('Circuito total', 35, 14, 'intermedio', 1, ent2),
    ('Movilidad y estiramiento', 25, 20, 'basico', 0, ent2),
]

rutinas = []
for i, (titulo, dur, cupos, nivel, d, ent) in enumerate(datos):
    r, _ = Rutina.objects.get_or_create(
        titulo=titulo, entrenador=ent,
        defaults={'descripcion': f'Descripción de {titulo}.',
                  'duracion_minutos': dur, 'cupos': cupos,
                  'nivel': nivel, 'disciplina': disciplinas[d]},
    )
    r.equipamientos.set([equipos[i % 5], equipos[(i + 1) % 5]])
    rutinas.append(r)

# (rutina, socio, estado)
inscripciones = [
    (rutinas[0], socio1, 'pendiente'),
    (rutinas[1], socio1, 'confirmada'),
    (rutinas[5], socio1, 'rechazada'),
    (rutinas[6], ent1, 'confirmada'),
    (rutinas[7], ent1, 'pendiente'),
]
for rutina, socio, estado in inscripciones:
    Inscripcion.objects.get_or_create(
        rutina=rutina, socio=socio, defaults={'estado': estado})

print('Datos cargados correctamente')

# Verificación de permisos: (usuario, is_staff, is_superuser)
# Los usuarios de prueba y los registrados por la web deben salir con False, False.
# Solo el superusuario (creado con createsuperuser) debe salir con True, True.
print(list(User.objects.values_list('username', 'is_staff', 'is_superuser')))