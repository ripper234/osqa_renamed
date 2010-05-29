from django import template

register = template.Library()

class MultiUserMailMessage(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        recipients = context['recipients']
        messages = list()

        for recipient in recipients:
            context['recipient'] = recipient
            self.nodelist.render(context)
            messages.append((recipient, context['subject'], context['html_content'], context['text_content']))

        print messages

@register.tag
def email(parser, token):
    nodelist = parser.parse(('endemail',))
    parser.delete_first_token()
    return MultiUserMailMessage(nodelist)



class EmailPartNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        context[self.varname] = self.nodelist.render(context).strip()

@register.tag
def subject(parser, token):
    nodelist = parser.parse(('endsubject',))
    parser.delete_first_token()
    return EmailPartNode(nodelist, 'subject')

@register.tag
def htmlcontent(parser, token):
    nodelist = parser.parse(('endhtmlcontent',))
    parser.delete_first_token()
    return EmailPartNode(nodelist, 'html_content')

@register.tag
def textcontent(parser, token):
    nodelist = parser.parse(('endtextcontent',))
    parser.delete_first_token()
    return EmailPartNode(nodelist, 'text_content')


