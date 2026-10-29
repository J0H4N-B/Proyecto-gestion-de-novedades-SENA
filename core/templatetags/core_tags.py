from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def activo(context, *nombres):
    coincidencia = context["request"].resolver_match
    return "active" if coincidencia and coincidencia.url_name in nombres else ""
