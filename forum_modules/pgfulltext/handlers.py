from forum.models import Question
from forum.modules.decorators import decorate
from forum.views.readers import do_question_search

@decorate(do_question_search, needs_origin=False)
def question_search(keywords):
    return Question.objects.all().extra(
                    tables=['forum_rootnode_doc'],
                    select={
                        'ranking': 'ts_rank_cd("forum_rootnode_doc"."document", plainto_tsquery(\'english\', %s), 32)',
                    },
                    where=['"forum_rootnode_doc"."node_id" = "forum_node"."id"', '"forum_rootnode_doc"."document" @@ plainto_tsquery(\'english\', %s)'],
                    params=[keywords],
                    select_params=[keywords],
                    order_by=['-ranking']
                )