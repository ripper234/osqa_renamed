from forum.models.question import Question, QuestionManager
from forum.modules.decorators import decorate

@decorate(QuestionManager.search, needs_origin=False)
def question_search(self, keywords):
    return self.extra(
                    tables=['forum_rootnode_doc'],
                    select={
                        'ranking': 'ts_rank_cd(\'{0.1, 0.2, 0.8, 1.0}\'::float4[], "forum_rootnode_doc"."document", plainto_tsquery(\'english\', %s), 32)',
                    },
                    where=['"forum_rootnode_doc"."node_id" = "forum_node"."id"', '"forum_rootnode_doc"."document" @@ plainto_tsquery(\'english\', %s)'],
                    params=[keywords],
                    select_params=[keywords],
                    order_by=['-ranking']
                )