from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def floatval(value):
    try:
        return float(value)
    except:
        return 0.0


@register.filter
def variacao_percentual(preco_atual, preco_unitario):
    try:
        return (
            (float(preco_atual) - float(preco_unitario)) / float(preco_unitario)
        ) * 100
    except (ZeroDivisionError, ValueError, TypeError):
        return 0

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})
