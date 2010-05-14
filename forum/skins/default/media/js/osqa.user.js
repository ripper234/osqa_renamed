
function show_dialog (html, extra_class, pos, dim, yes, no_text) {
    $dialog = $('<div class="dialog ' + extra_class + '" style="width: 1px; height: 1px;">'
             + '<div class="dialog-content">' + html + '</div><div class="dialog-buttons">'
            + '<button class="dialog-no">' + no_text + '</button>'
            + '<button class="dialog-yes">' + yes.text + '</button>'
            + '</div></div>');

    $('body').append($dialog);

    $dialog.css({
        top: pos.y,
        left: pos.x
    });

    $dialog.animate({
        top: "-=" + (dim.h / 2),
        left: "-=" + (dim.w / 2),
        width: dim.w,
        height: dim.h
    }, 200, function() {
        $dialog.find('.dialog-no').click(function() {
            $dialog.fadeOut('fast');
        });
        $dialog.find('.dialog-yes').click(function() {
            yes.callback($dialog);
        });
    });

}


$().ready(function() {
    var $dropdown = $('#user-menu-dropdown');

    $('#user-menu').click(function(){
        $('.dialog').fadeOut('fast');
        $dropdown.slideToggle('fast');        
    });

    $('.confirm').each(function() {
        var $link = $(this);

        $link.click(function(e) {
            $dropdown.slideUp('fast');
            var html = messages.confirm;

            show_dialog(html, 'confirm', {x: e.pageX, y: e.pageY}, {w: 200, h: 100}, {
                text: messages.yes,
                callback: function() {
                    window.location = $link.attr('href');
                }
            }, messages.no);

            return false;
        });
    });

    $('#award-rep-points').click(function(e) {
        $dropdown.slideUp('fast');

        var html = '<table><tr><th>' + messages.points + '</th><td><input type="text" id="points-to-award" value="1" /></td></tr>'
                + '<tr><th>' + messages.message + '</th><td><textarea id="award-message"></textarea></td></tr></table>';

        show_dialog(html, 'award-rep-points', {x: e.pageX, y: e.pageY}, {w: 300, h: 125}, {
            text: messages.award,
            callback: function($dialog) {
                var $points_input = $('#points-to-award');
                var _points = parseInt($points_input.val());

                if(!isNaN(_points)) {
                    $dialog.fadeOut('fast');
                    var _message = $('#award-message').val();
                    $.post($('#award-rep-points').attr('href'), {points: _points, message: _message}, function(data) {
                        if (data.success) {
                            $('#user-reputation').css('background', 'yellow');
                            $('#user-reputation').html(data.reputation);

                            $('#user-reputation').animate({ backgroundColor: "transparent" }, 1000);
                            
                        }
                    }, 'json')
                }
            }
        }, messages.cancel);


        return false;
    });
});