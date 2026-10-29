from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db import transaction
from django.http import Http404

from app_gim.forms import DisciplinaForm, PerfilForm, RegistroForm, RutinaForm

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

# ---------- Cuentas ----------

def registro(request):
    if request.user.is_authenticated:
        return redirect('app_gim:portada')
    form = RegistroForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'¡Bienvenido, {user.username}! Tu cuenta fue creada.')
        return redirect('app_gim:portada')
    if request.method == 'POST':
        messages.error(request, 'Revisa los errores del formulario.')
    return render(request, 'app_gim/registro.html', {'form': form})


class IngresoView(LoginView):
    template_name = 'app_gim/ingreso.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f'Hola de nuevo, {form.get_user().username}.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)


@login_required
def mi_cuenta(request):
    perfil_form = PerfilForm(instance=request.user)
    clave_form = PasswordChangeForm(request.user)

    if request.method == 'POST':
        if 'guardar_datos' in request.POST:
            perfil_form = PerfilForm(request.POST, instance=request.user)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Tus datos fueron actualizados.')
                return redirect('app_gim:mi_cuenta')
        elif 'cambiar_clave' in request.POST:
            clave_form = PasswordChangeForm(request.user, request.POST)
            if clave_form.is_valid():
                user = clave_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Tu contraseña fue cambiada.')
                return redirect('app_gim:mi_cuenta')
        messages.error(request, 'No se pudo guardar. Revisa los errores.')

    return render(request, 'app_gim/mi_cuenta.html',
                  {'perfil_form': perfil_form, 'clave_form': clave_form})


# ---------- CRUD de rutinas ----------
def _rutina_del_dueno(request, pk):
    """Devuelve la rutina solo si el usuario con sesión es su dueño.

    - La rutina no existe                -> 404 (no encontrada)
    - Existe pero es de otro entrenador  -> 403 (sin permiso)
    """
    rutina = get_object_or_404(Rutina, pk=pk)
    if rutina.entrenador_id != request.user.id:
        raise PermissionDenied
    return rutina

@login_required
def rutina_crear(request):
    form = RutinaForm(request.POST or None, entrenador=request.user)
    if form.is_valid():
        rutina = form.save(commit=False)
        rutina.entrenador = request.user
        rutina.save()
        form.save_m2m()
        messages.success(request, 'Rutina creada correctamente.')
        return redirect('app_gim:detalle', pk=rutina.pk)
    if request.method == 'POST':
        messages.error(request, 'No se pudo crear la rutina. Revisa los errores.')
    return render(request, 'app_gim/rutina_form.html', {'form': form, 'titulo': 'Nueva rutina'})


@login_required
def rutina_editar(request, pk):
    rutina = _rutina_del_dueno(request, pk)
    form = RutinaForm(request.POST or None, instance=rutina, entrenador=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Rutina actualizada.')
        return redirect('app_gim:detalle', pk=rutina.pk)
    if request.method == 'POST':
        messages.error(request, 'No se pudo guardar. Revisa los errores.')
    return render(request, 'app_gim/rutina_form.html', {'form': form, 'titulo': 'Editar rutina'})


@login_required
@require_POST
def rutina_eliminar(request, pk):
    rutina = _rutina_del_dueno(request, pk)
    rutina.delete()
    messages.success(request, 'Rutina eliminada.')
    return redirect('app_gim:listado')


@login_required
def mis_rutinas(request):
    rutinas = Rutina.objects.filter(entrenador=request.user).select_related('disciplina')
    return render(request, 'app_gim/mis_rutinas.html', {'rutinas': rutinas})


# ---------- Inscripciones y solicitudes ----------

@login_required
@require_POST
def inscribirse(request, pk):
    with transaction.atomic():
        rutina = get_object_or_404(Rutina.objects.select_for_update(), pk=pk)

        if rutina.entrenador_id == request.user.id:
            messages.error(request, 'No puedes inscribirte en tu propia rutina.')
        elif Inscripcion.objects.filter(rutina=rutina, socio=request.user).exists():
            messages.error(request, 'Ya tienes una solicitud para esta rutina. Revisa "Mis solicitudes".')
        elif rutina.cupos_libres() <= 0:
            messages.error(request, 'Esta rutina ya no tiene cupos disponibles.')
        else:
            Inscripcion.objects.create(
                rutina=rutina,
                socio=request.user,
                comentario=request.POST.get('comentario', '').strip(),
            )
            messages.success(request, 'Solicitud enviada. Quedó pendiente hasta que el entrenador responda.')
    return redirect('app_gim:detalle', pk=pk)


@login_required
def mis_solicitudes(request):
    solicitudes = (Inscripcion.objects
                   .filter(socio=request.user)
                   .select_related('rutina', 'rutina__entrenador'))
    return render(request, 'app_gim/mis_solicitudes.html', {'solicitudes': solicitudes})


@login_required
@require_POST
def solicitud_cancelar(request, pk):
    insc = get_object_or_404(Inscripcion, pk=pk)
    if insc.socio_id != request.user.id:
        raise PermissionDenied
    if insc.estado != Inscripcion.Estado.PENDIENTE:
        messages.error(request, 'Solo puedes cancelar solicitudes pendientes.')
    else:
        insc.delete()
        messages.success(request, 'Solicitud cancelada.')
    return redirect('app_gim:mis_solicitudes')


@login_required
def solicitudes_recibidas(request):
    todas = (Inscripcion.objects
             .filter(rutina__entrenador=request.user)
             .select_related('rutina', 'socio'))
    return render(request, 'app_gim/solicitudes_recibidas.html', {
        'pendientes': todas.filter(estado=Inscripcion.Estado.PENDIENTE),
        'resueltas': todas.exclude(estado=Inscripcion.Estado.PENDIENTE),
    })


@login_required
@require_POST
def solicitud_resolver(request, pk, accion):
    if accion not in ('confirmar', 'rechazar'):
        raise Http404
    with transaction.atomic():
        insc = get_object_or_404(Inscripcion.objects.select_related('rutina'), pk=pk)
        if insc.rutina.entrenador_id != request.user.id:
            raise PermissionDenied
        rutina = Rutina.objects.select_for_update().get(pk=insc.rutina_id)

        if insc.estado != Inscripcion.Estado.PENDIENTE:
            messages.error(request, 'Esta solicitud ya fue resuelta.')
        elif accion == 'confirmar':
            if rutina.cupos_libres() <= 0:
                messages.error(request, 'No quedan cupos para confirmar esta solicitud.')
            else:
                insc.estado = Inscripcion.Estado.CONFIRMADA
                insc.save()
                messages.success(request, f'Confirmaste a {insc.socio.username}.')
        else:
            insc.estado = Inscripcion.Estado.RECHAZADA
            insc.save()
            messages.success(request, f'Rechazaste a {insc.socio.username}.')
    return redirect('app_gim:solicitudes_recibidas')


# ---------- Catálogo de disciplinas ----------

@login_required
def disciplinas(request):
    form = DisciplinaForm(request.POST or None)
    if form.is_valid():
        disciplina = form.save()
        messages.success(request, f'Disciplina "{disciplina.nombre}" creada. Ya puedes elegirla en tus rutinas.')
        return redirect('app_gim:disciplinas')
    if request.method == 'POST':
        messages.error(request, 'No se pudo crear la disciplina. Revisa los errores.')
    lista = Disciplina.objects.annotate(total_rutinas=Count('rutinas'))
    return render(request, 'app_gim/disciplinas.html', {'form': form, 'disciplinas': lista})