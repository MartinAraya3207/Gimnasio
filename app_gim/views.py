from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from app_gim.forms import PerfilForm, RegistroForm, RutinaForm

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
    rutina = get_object_or_404(Rutina, pk=pk, entrenador=request.user)
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
    rutina = get_object_or_404(Rutina, pk=pk, entrenador=request.user)
    rutina.delete()
    messages.success(request, 'Rutina eliminada.')
    return redirect('app_gim:listado')