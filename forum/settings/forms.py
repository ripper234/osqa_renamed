import os
import socket
from string import strip
from django import forms
from base import Setting
from django.utils.translation import ugettext as _
from django.core.files.storage import FileSystemStorage

class DummySetting:
    pass

class UnfilteredField(forms.CharField):
    def clean(self, value):
            return value


class SettingsSetForm(forms.Form):
    def __init__(self, set, data=None, *args, **kwargs):
        if data is None:
            data = dict([(setting.name, setting.value) for setting in set])

        super(SettingsSetForm, self).__init__(data, *args, **kwargs)

        for setting in set:
            if isinstance(setting, (Setting.emulators.get(str, DummySetting), Setting.emulators.get(unicode, DummySetting))):
                if not setting.field_context.get('widget', None):
                    setting.field_context['widget'] = forms.TextInput(attrs={'class': 'longstring'})
                field = forms.CharField(**setting.field_context)
            elif isinstance(setting, Setting.emulators.get(float, DummySetting)):
                field = forms.FloatField(**setting.field_context)
            elif isinstance(setting, Setting.emulators.get(int, DummySetting)):
                field = forms.IntegerField(**setting.field_context)
            elif isinstance(setting, Setting.emulators.get(bool, DummySetting)):
                field = forms.BooleanField(**setting.field_context)
            else:
                field = UnfilteredField(**setting.field_context)

            self.fields[setting.name] = field

        self.set = set

    def as_table(self):
        return self._html_output(
                u'<tr><th>%(label)s' + ('<br /><a class="fieldtool context" href="#">%s</a><span class="sep">|</span><a class="fieldtool default" href="#">%s</a></th>' % (
                    _('context'), _('default'))) + u'<td>%(errors)s%(field)s%(help_text)s</td>',
                u'<tr><td colspan="2">%s</td></tr>', '</td></tr>', u'<br />%s', False)

    def save(self):
        for setting in self.set:
            setting.set_value(self.cleaned_data[setting.name])

class ImageFormWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        return """
            <img src="%(value)s" /><br />
            %(change)s: <input type="file" name="%(name)s" />
            <input type="hidden" name="%(name)s_old" value="%(value)s" />
            """ % {'name': name, 'value': value, 'change': _('Change this:')}

    def value_from_datadict(self, data, files, name):
        if name in files:
            f = files[name]

            # check file type
            file_name_suffix = os.path.splitext(f.name)[1].lower()

            if not file_name_suffix in ('.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff', '.ico'):
                raise Exception('File type not allowed')

            from forum.settings import UPFILES_FOLDER, UPFILES_ALIAS

            storage = FileSystemStorage(str(UPFILES_FOLDER), str(UPFILES_ALIAS))
            new_file_name = storage.save(f.name, f)
            return str(UPFILES_ALIAS) + new_file_name
        else:
            if "%s_old" % name in data:
                return data["%s_old" % name]
            elif name in data:
                return data[name]

class StringListWidget(forms.Widget):
    def render(self, name, value, attrs=None):
        ret = ""
        for s in value:
            ret += """
            <div class="string-list-input">
                <input type="text" name="%(name)s" value="%(value)s" />
                <button class="string_list_widget_button">-</button>
            </div>
            """  % {'name': name, 'value': s}

        return """
            <div class="string_list_widgets">
                %(ret)s
                <div><button name="%(name)s" class="string_list_widget_button add">+</button></div>
            </div>
            """ % dict(name=name, ret=ret)

    def value_from_datadict(self, data, files, name):
        if 'submit' in data:
            return data.getlist(name)
        else:
            return data[name]

class CommaStringListWidget(forms.Textarea):
    def value_from_datadict(self, data, files, name):
        if 'submit' in data:
            return map(strip, data[name].split(','))
        else:
            return ', '.join(data[name])    


class IPListField(forms.CharField):
    def clean(self, value):
        ips = [ip.strip() for ip in value.strip().strip(',').split(',')]
        iplist = []

        if len(ips) < 1:
            raise forms.ValidationError(_('Please input at least one ip address'))    

        for ip in ips:
            try:
                socket.inet_aton(ip)
            except socket.error:
                raise forms.ValidationError(_('Invalid ip address: %s' % ip))

            if not len(ip.split('.')) == 4:
                raise forms.ValidationError(_('Please use the dotted quad notation for the ip addresses'))

            iplist.append(ip)

        return iplist

class MaintenanceModeForm(forms.Form):
    ips = IPListField(label=_('Allow ips'),
                      help_text=_('Comma separated list of ips allowed to access the site while in maintenance'),
                      required=True,
                      widget=forms.TextInput(attrs={'class': 'longstring'}))

    message = forms.CharField(label=_('Message'),
                              help_text=_('A message to display to your site visitors while in maintainance mode'),
                              widget=forms.Textarea)



