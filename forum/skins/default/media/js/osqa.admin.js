$(function() {
    $('.string_list_widget_button').live('click', function() {
        $but = $(this);

        if ($but.is('.add')) {
            $new = $("<div style=\"display: none\">" +
                    "<input type=\"text\" name=\"" + $but.attr('name') + "\" value=\"\" />" +
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
});