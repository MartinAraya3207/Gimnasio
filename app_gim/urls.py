from django.urls import path

from . import views

app_name = 'app_gim'

urlpatterns = [
    path('', views.portada, name='portada'),
    path('rutinas/', views.listado, name='listado'),
    path('rutinas/<int:pk>/', views.detalle, name='detalle'),
    # Hito 3 en adelante: aquí se agregan crear/editar/eliminar, cuentas, etc.
]