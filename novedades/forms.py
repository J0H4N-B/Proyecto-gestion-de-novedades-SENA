from django import forms
from django.db.models import Q

from catalogo.models import Ambiente
from core.forms import EstiloBootstrapMixin
from cuentas.models import Usuario

from .models import Novedad
from .permisos import aprendices_asignables


class NovedadForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Novedad
        fields = ["tipo", "aprendiz", "ambiente", "descripcion", "archivo"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 5}),
            "archivo": forms.FileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg"}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        aprendices = Usuario.objects.filter(
            Q(pk__in=aprendices_asignables(usuario)) | Q(pk=self.instance.aprendiz_id)
        )
        self.fields["aprendiz"].queryset = aprendices.order_by("first_name", "last_name")
        ambientes = Ambiente.objects.filter(Q(estado=Ambiente.Estado.ACTIVO) | Q(pk=self.instance.ambiente_id))
        self.fields["ambiente"].queryset = ambientes.select_related("sede")
