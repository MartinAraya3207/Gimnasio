from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Disciplina, Rutina


def _email_en_uso(email, excluir_pk=None):
    qs = User.objects.filter(email__iexact=email)
    if excluir_pk:
        qs = qs.exclude(pk=excluir_pk)
    return qs.exists()

class RegistroForm(UserCreationForm):
    email = forms.EmailField(label='Correo')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if _email_en_uso(email):
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False        # no puede entrar al admin
        user.is_superuser = False    # no tiene permisos de administrador
        if commit:
            user.save()
        return user


class PerfilForm(forms.ModelForm):
    email = forms.EmailField(label='Correo')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if _email_en_uso(email, excluir_pk=self.instance.pk):
            raise forms.ValidationError('Ese correo ya lo usa otra cuenta.')
        return email


class RutinaForm(forms.ModelForm):
    class Meta:
        model = Rutina
        fields = ('titulo', 'descripcion', 'duracion_minutos', 'cupos',
                  'nivel', 'disciplina', 'equipamientos')
        widgets = {'equipamientos': forms.CheckboxSelectMultiple}

    def __init__(self, *args, entrenador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.entrenador = entrenador

        # Regla del caso: hasta cinco etiquetas (equipamientos) por rutina
    def clean_equipamientos(self):
        equipamientos = self.cleaned_data['equipamientos']
        if len(equipamientos) > 5:
            raise forms.ValidationError('Puedes elegir como máximo 5 equipamientos.')
        return equipamientos

    # Validación propia 1: título de al menos 5 caracteres
    def clean_titulo(self):
        titulo = self.cleaned_data['titulo'].strip()
        if len(titulo) < 5:
            raise forms.ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo

    # Validación propia 2: el mismo entrenador no repite títulos
    # Validación propia 3: una rutina avanzada no puede durar menos de 30 min
    def clean(self):
        datos = super().clean()
        titulo = datos.get('titulo')
        if titulo and self.entrenador:
            repetida = (Rutina.objects
                        .filter(entrenador=self.entrenador, titulo__iexact=titulo)
                        .exclude(pk=self.instance.pk))
            if repetida.exists():
                self.add_error('titulo', 'Ya tienes una rutina con ese título.')
        if datos.get('nivel') == Rutina.Nivel.AVANZADO and (datos.get('duracion_minutos') or 99) < 30:
            self.add_error('duracion_minutos', 'Una rutina avanzada debe durar al menos 30 minutos.')
        return datos
    

class DisciplinaForm(forms.ModelForm):
    class Meta:
        model = Disciplina
        fields = ('nombre',)
        labels = {'nombre': 'Nombre de la disciplina'}

    def clean_nombre(self):
        # Quita espacios sobrantes: "  Yoga   suave " -> "Yoga suave"
        nombre = ' '.join(self.cleaned_data['nombre'].split())
        if len(nombre) < 3:
            raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
        # iexact: "yoga" y "Yoga" cuentan como la misma disciplina
        repetida = Disciplina.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise forms.ValidationError('Ya existe una disciplina con ese nombre.')
        return nombre