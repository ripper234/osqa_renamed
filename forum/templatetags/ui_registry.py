from django import template
from forum.modules import ui

register = template.Library()


class LoadRegistryNode(template.Node):
    def __init__(self, registry, separator):
        self.registry = registry
        self.separator = separator

    def render(self, context):
        separator = self.separator.render(context)
        result = ''

        for ui_object in self.registry:
            if ui_object.can_render(context):
                if result:
                    result += separator
                result += ui_object.render(context)

        return result


@register.tag
def loadregistry(parser, token):
    try:
        tag_name, registry = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]

    registry = ui.get_registry_by_name(registry)
    separator = parser.parse(('endloadregistry',))
    parser.delete_first_token()
    return LoadRegistryNode(registry, separator)


class LoopRegistryNode(template.Node):
    def __init__(self, registry, nodelist):
        self.registry = registry
        self.nodelist = nodelist

    def render(self, context):
        result = ''

        for ui_object in self.registry:
            if ui_object.can_render(context):
                ui_object.update_context(context)
                result += self.nodelist.render(context)

        return result

@register.tag
def loopregistry(parser, token):
    try:
        tag_name, registry = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]

    registry = ui.get_registry_by_name(registry)
    nodelist = parser.parse(('endloopregistry',))
    parser.delete_first_token()

    return LoopRegistryNode(registry, nodelist)