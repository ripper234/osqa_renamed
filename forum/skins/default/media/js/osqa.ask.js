var currentSideBar = 'div#title_side_bar';
function changeSideBar(enabled_bar) {
    $(currentSideBar).hide();
    currentSideBar = enabled_bar;
    $(currentSideBar).fadeIn('slow');

}
$(function () {
    $('div#editor_side_bar').hide();
    $('div#tags_side_bar').hide();

    $('#id_title').focus(function(){changeSideBar('div#title_side_bar')});
    $('#editor').focus(function(){changeSideBar('div#editor_side_bar')});
    $('#id_tags').focus(function(){changeSideBar('div#tags_side_bar')});
});

$(function() {
    var $input = $('#id_title');
    var $box = $('#ask-related-questions');
    var template = $('#question-summary-template').html();

    var results_cache = {};

    function reload_suggestions_box(e) {
        var q = $input.val().replace(/^\s+|\s+$/g,"");

        if (q.length == 0) {
            $('#ask-related-questions').html('');
            return false;
        }

        if (results_cache[q] && results_cache[q] != '') {
            $('#ask-related-questions').html(results_cache[q]);
            return false;
        }

        $.post(related_questions_url, {title: q}, function(data) {
            if (data) {
                var c = $input.val().replace(/^\s+|\s+$/g,"");

                if (c != q) {
                    return;
                }

                var html = '';
                for (var i = 0; i < data.length; i++) {
                    var item = template.replace(new RegExp('%URL%', 'g'), data[i].url)
                                       .replace(new RegExp('%SCORE%', 'g'), data[i].score)
                                       .replace(new RegExp('%TITLE%', 'g'), data[i].title)
                                       .replace(new RegExp('%SUMMARY%', 'g'), data[i].summary);

                    html += item;

                }

                results_cache[q] = html;

                $('#ask-related-questions').html(html);
            }
        }, 'json');

        return false;
    }

    $input.keyup(reload_suggestions_box);
});