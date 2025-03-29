from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def percentage(value, total):
    """
    Calculate the percentage of value relative to total
    """
    if total == 0:
        return 0
    return floatformat((value / total) * 100, 0)