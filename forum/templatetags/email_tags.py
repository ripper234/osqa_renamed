from django import template
from forum import settings

register = template.Library()

class MultiUserMailMessage(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        recipients = context['recipients']
        messages = list()

        for recipient in recipients:
            context['embeddedmedia'] = {}
            context['recipient'] = recipient
            self.nodelist.render(context)
            messages.append((recipient, context['subject'], context['htmlcontent'], context['textcontent'], context['embeddedmedia']))

        create_mail_messages(messages)

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

def content(parser, token):
    try:
        tag_name, base = token.split_contents()
    except ValueError:
        try:
            tag_name = token.split_contents()[0]
            base = None
        except:
            raise template.TemplateSyntaxError, "%r tag requires at least two arguments" % token.contents.split()[0]

    nodelist = parser.parse(('end%s' % tag_name,))

    if base:
        base = template.loader.get_template(base)

        basenodes = base.nodelist
        content = [i for i,n in enumerate(basenodes) if isinstance(n, template.loader_tags.BlockNode) and n.name == "content"]
        if len(content):
            index = content[0]
            nodelist = template.NodeList(basenodes[0:index] + nodelist + basenodes[index:])
        

    parser.delete_first_token()
    return EmailPartNode(nodelist, tag_name)


register.tag('htmlcontent', content)
register.tag('textcontent', content)


class EmbedMediaNode(template.Node):
    def __init__(self, location, alias):
        self.location = template.Variable(location)
        self.alias = alias

    def render(self, context):
        context['embeddedmedia'][self.alias] = self.location.resolve(context)
        pass


@register.tag
def embedmedia(parser, token):
    try:
        tag_name, location, _, alias = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly four arguments" % token.contents.split()[0]

    return EmbedMediaNode(location, alias)

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from django.core.mail import DNS_NAME
from smtplib import SMTP
import email.Charset
import socket


def create_mail_messages(messages):
    sender = '%s <%s>' % (unicode(settings.APP_SHORT_NAME), unicode(settings.DEFAULT_FROM_EMAIL))

    connection = SMTP(str(settings.EMAIL_HOST), str(settings.EMAIL_PORT),
                local_hostname=DNS_NAME.get_fqdn())

    try:
        if (bool(settings.EMAIL_USE_TLS)):
            connection.ehlo()
            connection.starttls()
            connection.ehlo()

        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            connection.login(str(settings.EMAIL_HOST_USER), str(settings.EMAIL_HOST_PASSWORD))

        if sender is None:
            sender = str(settings.DEFAULT_FROM_EMAIL)

        for recipient, subject, html, text, media in messages:
            msgRoot = MIMEMultipart('related')
            msgRoot['Subject'] = subject
            msgRoot['From'] = sender
            msgRoot['To'] =  '%s <%s>' % (recipient.username, recipient.email)
            msgRoot.preamble = 'This is a multi-part message from %s.' % unicode(settings.APP_SHORT_NAME).encode('utf8')

            msgAlternative = MIMEMultipart('alternative')
            msgRoot.attach(msgAlternative)

            msgAlternative.attach(MIMEText(text, _charset='utf-8'))
            msgAlternative.attach(MIMEText(html, 'html', _charset='utf-8'))

            for alias, location in media.items():
                fp = open(location, 'rb')
                msgImage = MIMEImage(fp.read())
                fp.close()
                msgImage.add_header('Content-ID', '<'+alias+'>')
                msgRoot.attach(msgImage)

            try:
                connection.sendmail(sender, [recipient.email], msgRoot.as_string())
            except Exception, e:
                pass

        try:
            connection.quit()
        except socket.sslerror:
            connection.close()
    except Exception, e:
        print e

    
    


