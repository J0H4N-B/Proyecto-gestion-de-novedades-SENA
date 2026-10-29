from django import forms


class EstiloBootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()

    def is_valid(self):
        valido = super().is_valid()
        for nombre in self.errors:
            atributos = self.fields[nombre].widget.attrs if nombre in self.fields else {}
            if atributos and "is-invalid" not in atributos["class"]:
                atributos["class"] += " is-invalid"
        return valido
