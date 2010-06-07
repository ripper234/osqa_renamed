$(function() {
    $('.string_list_widget_button').live('click', function() {
        $but = $(this);

        if ($but.is('.add')) {
            $new = $("<div style=\"display: none;\">" +
                    "<input style=\"width: 600px;\" type=\"text\" name=\"" + $but.attr('name') + "\" value=\"\" />" +
                    "<button class=\"string_list_widget_button\">-</button>" +
                    "</div>");

            $but.before($new);
            $new.slideDown('fast');
        } else {
            $but.parent().slideUp('fast', function() {
                $but.parent().remove();
            });
        }

        return false;
    })

    $('.fieldtool').each(function() {
        var $link = $(this);
        var $input = $link.parent().parent().find('input, textarea');
        var name = $input.attr('name')

        if ($link.is('.context')) {
            $link.click(function() {
                var $contextbox = $('<input type="text" value="' + name + '" />');
                $link.replaceWith($contextbox);
            });
        } else if ($link.is('.default')) {
            if ($input.length == 1 && ($input.is('[type=text]') || $input.is('textarea'))) {
                $link.click(function() {
                    $.post(name + '/', function(data) {
                        $input.val(data);
                    });
                });
            } else {
                $link.attr('href', name + '/');
            }
        }
    });

    $('.url_field').each(function() {
        var $input = $(this);
        var $anchor = $input.parent().find('.url_field_anchor');
        var app_url = $anchor.attr('href');

        function rewrite_anchor() {
            var val = app_url + $input.val();

            $anchor.attr('href', val);
            $anchor.html(val);

        }

        $input.keyup(rewrite_anchor);
        rewrite_anchor();        
    });
});