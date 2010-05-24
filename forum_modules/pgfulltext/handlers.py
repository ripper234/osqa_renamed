from django.db.models import Q
from forum.models.question import Question, QuestionManager
from forum.modules.decorators import decorate

@decorate(QuestionManager.search, needs_origin=False)
def question_search(self, keywords):
    tsquery = " | ".join(keywords.split(' '))
    
    return self.extra(
                    tables = ['forum_rootnode_doc'],
                    select={
                        'ranking': """
                                rank_exact_matches(ts_rank_cd('{0.1, 0.2, 0.8, 1.0}'::float4[], "forum_rootnode_doc"."document", to_tsquery('english', %s), 32))
                                """,
                    },
                    where=["""
                           "forum_rootnode_doc"."node_id" = "forum_node"."id" AND ("forum_rootnode_doc"."document" @@ to_tsquery('english', %s) OR
                           "forum_node"."title" ILIKE '""" + keywords + """%%')
                           """],
                    params=[tsquery],
                    select_params=[tsquery],
                    order_by=['-ranking']
                )

