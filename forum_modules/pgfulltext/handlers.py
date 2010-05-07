from forum.models import Question
from forum.modules.decorators import decorate
from forum.views.readers import do_question_search

@decorate(do_question_search, needs_origin=False)
def question_search(keywords):
    return Question.objects.all().extra(
                    select={
                        'ranking': 'node_ranking("forum_node"."id", %s)',
                    },
                    where=['node_ranking("forum_node"."id", %s) > 0'],
                    params=[keywords],
                    select_params=[keywords],
                    order_by=['-ranking']
                )