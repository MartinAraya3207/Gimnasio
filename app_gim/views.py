from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Disciplina, Inscripcion, Rutina

RUTINAS_POR_PAGINA = 5


def _rutinas_con_relaciones():
    """Rutinas con todo lo que las páginas necesitan, en pocas consultas.

    - select_related (JOIN) para las relaciones "hacia uno": entrenador y disciplina.
    - prefetch_related (consulta aparte) para la "hacia muchos": equipamientos.
    Sin esto, cada tarjeta haría 1-3 consultas extra (problema N+1).
    """
    return (
        Rutina.objects
        .select_related('entrenador', 'disciplina')
        .prefetch_related('equipamientos')
    )


def portada(request):
    contexto = {
        # El orden viene de Meta.ordering del modelo (más recientes primero)
        'ultimas': _rutinas_con_relaciones()[:4],
        'total_rutinas': Rutina.objects.count(),
        'total_disciplinas': Disciplina.objects.count(),
        'total_confirmadas': Inscripcion.objects.filter(
            estado=Inscripcion.Estado.CONFIRMADA
        ).count(),
    }
    return render(request, 'app_gim/portada.html', contexto)


def listado(request):
    rutinas = _rutinas_con_relaciones()

    # Búsqueda en dos campos: título OR descripción
    q = request.GET.get('q', '').strip()
    if q:
        rutinas = rutinas.filter(
            Q(titulo__icontains=q) | Q(descripcion__icontains=q)
        )

    # Filtro por disciplina (si el valor no es un número, se ignora)
    disciplina_id = request.GET.get('disciplina', '')
    if disciplina_id.isdecimal():
        rutinas = rutinas.filter(disciplina_id=disciplina_id)

    # Páginas de a cinco. get_page() nunca falla: si la página no existe,
    # entrega la primera (valor inválido) o la última (fuera de rango).
    pagina = Paginator(rutinas, RUTINAS_POR_PAGINA).get_page(request.GET.get('page'))

    # Los filtros actuales sin "page", para conservarlos al cambiar de página
    params = request.GET.copy()
    params.pop('page', None)

    contexto = {
        'pagina': pagina,
        'q': q,
        'disciplinas': Disciplina.objects.all(),
        'disciplina_id': disciplina_id,
        'querystring': params.urlencode(),
    }
    return render(request, 'app_gim/listado.html', contexto)


def detalle(request, pk):
    rutina = get_object_or_404(_rutinas_con_relaciones(), pk=pk)
    return render(request, 'app_gim/detalle.html', {'rutina': rutina})