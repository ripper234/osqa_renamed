from django import forms
from django.utils.translation import ugettext as _

class ExporterForm(forms.Form):
    anon_data = forms.BooleanField(label=_('Anonymized data'), help_text=_('Don\'t export user data and make all content anonymous'), required=False)
    