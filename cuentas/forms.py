from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from catalogo.models import Ficha
from core.forms import EstiloBootstrapMixin

from .models import Usuario


class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    pass


class CambioClaveForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class FichaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, ficha):
        return f"{ficha.codigo} · {ficha.programa} ({ficha.sede})"


class RegistroForm(EstiloBootstrapMixin, UserCreationForm):
    email = forms.EmailField(label="Correo electrónico")
    ficha = FichaChoiceField(
        queryset=Ficha.objects.select_related("programa", "sede"),
        label="Tu ficha",
        empty_label="Selecciona tu ficha",
    )

    campos_anchos = ["ficha", "username"]
    field_order = [
        "first_name", "last_name", "tipo_doc", "numero_documento", "ficha",
        "email", "telefono", "username", "password1", "password2",
    ]

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "tipo_doc", "numero_documento", "email", "telefono", "username", "ficha"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre in ("first_name", "last_name"):
            self.fields[nombre].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Usuario.Rol.APRENDIZ
        if commit:
            usuario.save()
        return usuario


class PerfilForm(EstiloBootstrapMixin, forms.ModelForm):
    quitar_foto = forms.BooleanField(required=False, label="Quitar mi foto actual")

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefono", "foto"]
        widgets = {"foto": forms.FileInput(attrs={"accept": "image/png,image/jpeg,image/webp"})}

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data["quitar_foto"] and "foto" not in self.files:
            usuario.foto = ""
        if commit:
            usuario.save()
        return usuario
