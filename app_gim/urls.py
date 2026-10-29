from django.urls import path
from django.contrib.auth.views import LogoutView   # arriba, con los otros imports
from . import views

app_name = 'app_gim'

urlpatterns = [
    path('', views.portada, name='portada'),
    path('rutinas/', views.listado, name='listado'),
    path('rutinas/<int:pk>/', views.detalle, name='detalle'),
    # Hito 3 en adelante: aquí se agregan crear/editar/eliminar, cuentas, etc.
    path('registro/', views.registro, name='registro'),
    path('ingreso/', views.IngresoView.as_view(), name='ingreso'),
    path('salida/', LogoutView.as_view(), name='salida'),
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('rutinas/nueva/', views.rutina_crear, name='rutina_crear'),
    path('rutinas/<int:pk>/editar/', views.rutina_editar, name='rutina_editar'),
    path('rutinas/<int:pk>/eliminar/', views.rutina_eliminar, name='rutina_eliminar'),
]


