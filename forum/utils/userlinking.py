import re

from forum.models.user import User

def auto_user_link(node, content):
    patern = r'@\w+'
    appeals = re.findall(patern, content)

    for appeal in appeals:
        # Try to find the profile URL
        username = appeal[1:]
        profile_url = None

        try:
            user = User.objects.get(username__iexact=username)
            profile_url = user.get_absolute_url()
        except User.DoesNotExist:
            """If we don't find the user from the first time, the interesting part
               begins. We look through all the authors (looking through question,
               comments, answers, and if it matches some of the -- we link him."""
            
            # We should find the root of the node tree (question) the current node belongs to.
            if node.node_type == "question":
                question = node
            elif node.node_type == "answer":
                question = node.question
            elif node.node_type == "comment":
                if not node.question:
                    question = node
                else:
                    question = node.question
            
            # Now we've got the root question. Let's get the list of active users.
            active_users = question.get_active_users()
            
            for active_user in active_users:
                if active_user.username.lower().startswith(username.lower()):
                    profile_url = active_user.get_absolute_url()
        
        if (profile_url is not None) and (appeal is not None):
            auto_link = '<a href="%s">%s</a>' % (profile_url, appeal)
            content = content.replace(appeal, auto_link)
    
    return content