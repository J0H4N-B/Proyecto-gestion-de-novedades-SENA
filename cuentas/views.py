from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, UpdateView

from core.archivos import respuesta_archivo

from .forms import CambioClaveForm, LoginForm, PerfilForm, RegistroForm
from .models import Usuario


class IngresarView(auth.LoginView):
    template_name = "cuentas/ingresar.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class RegistroView(CreateView):
    form_class = RegistroForm
    template_name = "cuentas/registro.html"
    success_url = reverse_lazy("novedades:lista")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, "Tu cuenta fue creada. Ya puedes consultar tus novedades.")
        return respuesta


class PerfilView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = PerfilForm
    template_name = "cuentas/perfil.html"
    success_url = reverse_lazy("cuentas:perfil")
    success_message = "Tu perfil fue actualizado."

    def get_object(self):
        return self.request.user


class ClaveView(auth.PasswordChangeView):
    form_class = CambioClaveForm
    template_name = "cuentas/clave_form.html"
    success_url = reverse_lazy("cuentas:clave_lista")


class ClaveListaView(auth.PasswordChangeDoneView):
    template_name = "cuentas/clave_lista.html"


class FotoView(LoginRequiredMixin, View):
    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if not usuario.foto or not (usuario == request.user or request.user.es_gestor):
            raise Http404
        return respuesta_archivo(usuario.foto, f"foto-{pk}.jpg", inline=True)
