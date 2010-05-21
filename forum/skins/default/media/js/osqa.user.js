$().ready(function() {
    var $dropdown = $('#user-menu-dropdown');

    $('#user-menu').click(function(){
        $('.dialog').fadeOut('fast', function() {
            $dialog.remove();
        });
        $dropdown.slideToggle('fast', function() {
            if ($dropdown.is(':visible')) {
               $dropdown.one('clickoutside', function() {
                    $dropdown.slideUp('fast')
                });
            }
        });
    });

    $('.confirm').each(function() {
        var $link = $(this);

        $link.click(function(e) {
            $dropdown.slideUp('fast');

            show_dialog({
                html: messages.confirm,
                extra_class: 'confirm',
                event: e,
                yes_callback: function() {
                    window.location = $link.attr('href');
                },
                yes_text: messages.yes,
                show_no: true,
                no_text: messages.no
            });

            return false;
        });
    });

    $('#award-rep-points').click(function(e) {
        $dropdown.slideUp('fast');

        var table = '<table><tr><th>' + messages.points + '</th><td><input type="text" id="points-to-award" value="1" /></td></tr>'
                + '<tr><th>' + messages.message + '</th><td><textarea id="award-message"></textarea></td></tr></table>';

        show_dialog({
                html: table,
                extra_class: 'award-rep-points',
                event: e,
                yes_callback: function($dialog) {
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
                },
                show_no: true
            });

        return false;
    });
});