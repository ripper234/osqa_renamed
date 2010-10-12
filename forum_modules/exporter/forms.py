from django import forms
from django.utils.translation import ugettext as _

class ExporterForm(forms.Form):
    anon_data = forms.BooleanField(label=_('Anonymized data'), help_text=_('Don\'t export user data and make all content anonymous'), required=False)
    uplodaded_files = forms.BooleanField(label=_('Uploaded files'), help_text=_('Include uploaded files in the backup'), required=False, initial=True)
    import_skins_folder = forms.BooleanField(label=_('Skins folder'), help_text=_('Include skins folder in the backup'), required=False, initial=False)
    