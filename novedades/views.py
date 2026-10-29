from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.html import conditional_escape, format_html
from django.utils.timezone import localtime
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, TemplateView, UpdateView

from core.archivos import respuesta_archivo

from .forms import NovedadForm
from .models import Novedad
from .permisos import novedades_visibles


class VisiblesMixin(LoginRequiredMixin):
    def get_queryset(self):
        return novedades_visibles(self.request.user)


class GestorMixin(VisiblesMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.es_gestor


class FormularioMixin(GestorMixin, SuccessMessageMixin):
    form_class = NovedadForm
    template_name = "novedades/novedad_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs


class NovedadListView(LoginRequiredMixin, TemplateView):
    template_name = "novedades/novedad_list.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        conteos = novedades_visibles(self.request.user).aggregate(
            total=Count("pk"),
            **{tipo: Count("pk", filter=Q(tipo=tipo)) for tipo in Novedad.Tipo.values},
        )
        contexto["indicadores"] = [
            {"valor": "", "nombre": "Todas", "icono": "bx-folder-open", "color": "secondary", "cantidad": conteos["total"]},
            *[
                {
                    "valor": valor,
                    "nombre": nombre,
                    "icono": Novedad.ESTILOS[valor][0],
                    "color": Novedad.ESTILOS[valor][1],
                    "cantidad": conteos[valor],
                }
                for valor, nombre in Novedad.Tipo.choices
            ],
        ]
        return contexto


def entero(valor, defecto, minimo=0, maximo=None):
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return defecto
    numero = max(numero, minimo)
    return min(numero, maximo) if maximo is not None else numero


class NovedadTablaView(LoginRequiredMixin, View):
    ordenables = [
        "creado_en", "tipo", "aprendiz__first_name", "aprendiz__ficha__codigo",
        "ambiente__codigo", "creado_por__first_name",
    ]

    def get(self, request):
        base = novedades_visibles(request.user)
        filtradas = self.ordenar(self.filtrar(base, request.GET), request.GET)
        inicio = entero(request.GET.get("start"), 0)
        largo = entero(request.GET.get("length"), 15, minimo=1, maximo=100)
        return JsonResponse({
            "draw": entero(request.GET.get("draw"), 0),
            "recordsTotal": base.count(),
            "recordsFiltered": filtradas.count(),
            "data": [self.fila(novedad) for novedad in filtradas[inicio:inicio + largo]],
        })

    def filtrar(self, novedades, parametros):
        tipo = parametros.get("tipo", "")
        busqueda = parametros.get("search[value]", "").strip()
        if tipo in Novedad.Tipo.values:
            novedades = novedades.filter(tipo=tipo)
        if busqueda:
            novedades = novedades.filter(
                Q(aprendiz__first_name__icontains=busqueda)
                | Q(aprendiz__last_name__icontains=busqueda)
                | Q(aprendiz__username__icontains=busqueda)
                | Q(aprendiz__numero_documento__icontains=busqueda)
                | Q(descripcion__icontains=busqueda)
            )
        return novedades

    def ordenar(self, novedades, parametros):
        if "order[0][column]" not in parametros:
            return novedades
        columna = entero(parametros["order[0][column]"], 0)
        campo = self.ordenables[columna] if columna < len(self.ordenables) else "creado_en"
        prefijo = "-" if parametros.get("order[0][dir]") == "desc" else ""
        return novedades.order_by(f"{prefijo}{campo}", "-pk")

    def fila(self, novedad):
        aprendiz = novedad.aprendiz
        return [
            format_html(
                '<time datetime="{}">{}</time>',
                novedad.creado_en.isoformat(),
                localtime(novedad.creado_en).strftime("%d/%m/%Y"),
            ),
            render_to_string("novedades/_tipo.html", {"novedad": novedad}),
            format_html(
                '<a class="fw-semibold text-decoration-none" href="{}">{}</a>'
                '<div class="small text-body-secondary">{} {}</div>',
                novedad.get_absolute_url(), aprendiz, aprendiz.tipo_doc, aprendiz.numero_documento,
            ),
            conditional_escape(aprendiz.ficha or "—"),
            conditional_escape(novedad.ambiente.codigo if novedad.ambiente else "—"),
            conditional_escape(novedad.creado_por or "—"),
            render_to_string("novedades/_archivo.html", {"novedad": novedad}),
            format_html(
                '<a class="btn btn-sm btn-outline-primary" href="{}"><i class="bx bx-show" aria-hidden="true"></i> Ver</a>',
                novedad.get_absolute_url(),
            ),
        ]


class NovedadDetailView(VisiblesMixin, DetailView):
    template_name = "novedades/novedad_detail.html"
    context_object_name = "novedad"


class NovedadCreateView(FormularioMixin, CreateView):
    model = Novedad
    success_message = "Novedad registrada."

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)


class NovedadUpdateView(FormularioMixin, UpdateView):
    success_message = "Cambios guardados."


class NovedadDeleteView(GestorMixin, SuccessMessageMixin, DeleteView):
    template_name = "novedades/novedad_confirm_delete.html"
    context_object_name = "novedad"
    success_url = reverse_lazy("novedades:lista")
    success_message = "Novedad eliminada."


class EvidenciaView(LoginRequiredMixin, View):
    def get(self, request, pk):
        novedad = get_object_or_404(novedades_visibles(request.user), pk=pk)
        if not novedad.archivo:
            raise Http404
        vista_previa = "ver" in request.GET and novedad.tipo_archivo["es_imagen"]
        return respuesta_archivo(novedad.archivo, novedad.nombre_descarga, inline=vista_previa)
