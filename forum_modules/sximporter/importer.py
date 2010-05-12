# -*- coding: utf-8 -*-

from xml.dom import minidom
from datetime import datetime, timedelta
import time
import re
from django.utils.translation import ugettext as _
from django.template.defaultfilters import slugify
from forum.models.utils import dbsafe_encode
from orm import orm

def getText(el):
    rc = ""
    for node in el.childNodes:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc.strip()

msstrip = re.compile(r'^(.*)\.\d+')
def readTime(ts):
    noms = msstrip.match(ts)
    if noms:
        ts = noms.group(1)

    return datetime(*time.strptime(ts, '%Y-%m-%dT%H:%M:%S')[0:6])

def readEl(el):
    return dict([(n.tagName.lower(), getText(n)) for n in el.childNodes if n.nodeType == el.ELEMENT_NODE])

def readTable(dump, name):
    return [readEl(e) for e in minidom.parseString(dump.read("%s.xml" % name)).getElementsByTagName('row')]

google_accounts_lookup = re.compile(r'^https?://www.google.com/accounts/')
yahoo_accounts_lookup = re.compile(r'^https?://me.yahoo.com/a/')

openid_lookups = [
    re.compile(r'^https?://www.google.com/profiles/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://me.yahoo.com/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://openid.aol.com/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://(?P<uname>\w+(\.\w+)*).myopenid.com/?$'),
    re.compile(r'^https?://flickr.com/(\w+/)*(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://technorati.com/people/technorati/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://(?P<uname>\w+(\.\w+)*).wordpress.com/?$'),
    re.compile(r'^https?://(?P<uname>\w+(\.\w+)*).blogspot.com/?$'),
    re.compile(r'^https?://(?P<uname>\w+(\.\w+)*).livejournal.com/?$'),
    re.compile(r'^https?://claimid.com/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://(?P<uname>\w+(\.\w+)*).pip.verisignlabs.com/?$'),
    re.compile(r'^https?://getopenid.com/(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://[\w\.]+/(\w+/)*(?P<uname>\w+(\.\w+)*)/?$'),
    re.compile(r'^https?://(?P<uname>[\w\.]+)/?$'),
]

def final_username_attempt(sxu):
    openid = sxu.get('openid', None)

    if openid:
        if google_accounts_lookup.search(openid):
            return UnknownGoogleUser(sxu.get('id'))
        if yahoo_accounts_lookup.search(openid):
            return UnknownYahooUser(sxu.get('id'))

        for lookup in openid_lookups:
            if lookup.search(openid):
                return lookup.search(openid).group('uname')

    return UnknownUser(sxu.get('id'))

class UnknownUser(object):
    def __init__(self, id):
        self._id = id

    def __str__(self):
        return _("user-%(id)d") % {'id': self._id}

    def __unicode__(self):
        return self.__str__()

    def encode(self, *args):
        return self.__str__()

class UnknownGoogleUser(UnknownUser):
    def __str__(self):
        return _("user-%(id)d (google)") % {'id': self._id}

class UnknownYahooUser(UnknownUser):
    def __str__(self):
        return _("user-%(id)d (yahoo)") % {'id': self._id}


class IdMapper(dict):
    def __getitem__(self, key):
        key = int(key)
        return super(IdMapper, self).get(key, 1)

    def __setitem__(self, key, value):
        super(IdMapper, self).__setitem__(int(key), int(value))

openidre = re.compile('^https?\:\/\/')
def userimport(dump, options):
    users = readTable(dump, "Users")

    user_by_name = {}
    uidmapper = IdMapper()
    merged_users = []

    owneruid = options.get('owneruid', None)
    #check for empty values
    if not owneruid:
        owneruid = None

    for sxu in users:
        create = True

        if sxu.get('id') == '-1':
            continue

        if int(sxu.get('id')) == int(owneruid):
            osqau = orm.User.objects.get(id=1)
            uidmapper[owneruid] = 1
            uidmapper[-1] = 1
            create = False
        else:
            username = sxu.get('displayname', sxu.get('displaynamecleaned', sxu.get('realname', final_username_attempt(sxu))))

            if not isinstance(username, UnknownUser) and username in user_by_name:
                #if options.get('mergesimilar', False) and sxu.get('email', 'INVALID') == user_by_name[username].email:
                #    osqau = user_by_name[username]
                #    create = False
                #    uidmapper[sxu.get('id')] = osqau.id
                #else:
                inc = 1
                while ("%s %d" % (username, inc)) in user_by_name:
                    inc += 1

                username = "%s %d" % (username, inc)

        sxbadges = sxu.get('badgesummary', None)
        badges = {'1':'0','2':'0','3':'0'}

        if sxbadges:
            badges.update(dict([b.split('=') for b in sxbadges.split()]))

        if create:
            osqau = orm.User(
                id           = sxu.get('id'),
                username     = unicode(username),
                password     = '!',
                email        = sxu.get('email', ''),
                is_superuser = sxu.get('usertypeid') == '5',
                is_staff     = sxu.get('usertypeid') == '4',
                is_active    = True,
                date_joined  = readTime(sxu.get('creationdate')),
                last_seen    = readTime(sxu.get('lastaccessdate')),
                about         = sxu.get('aboutme', ''),
                date_of_birth = sxu.get('birthday', None) and readTime(sxu['birthday']) or None,
                email_isvalid = int(sxu.get('usertypeid')) > 2,
                website       = sxu.get('websiteurl', ''),
                reputation    = int(sxu.get('reputation')),
                gold          = int(badges['1']),
                silver        = int(badges['2']),
                bronze        = int(badges['3']),
                real_name     = sxu.get('realname', ''),
            )

            osqau.save()

            user_joins = orm.Action(
                action_type = "userjoins",
                action_date = osqau.date_joined,
                user = osqau
            )
            user_joins.save()

            rep = orm.ActionRepute(
                value = 1,
                user = osqau,
                date = osqau.date_joined,
                action = user_joins
            )
            rep.save()            

            try:
                orm.SubscriptionSettings.objects.get(user=osqau)
            except:
                s = orm.SubscriptionSettings(user=osqau)
                s.save()

            uidmapper[osqau.id] = osqau.id
        else:
            new_about = sxu.get('aboutme', None)
            if new_about and osqau.about != new_about:
                if osqau.about:
                    osqau.about = "%s\n|\n%s" % (osqau.about, new_about)
                else:
                    osqau.about = new_about

            osqau.username = sxu.get('displayname', sxu.get('displaynamecleaned', sxu.get('realname', UnknownUser())))
            osqau.email = sxu.get('email', '')
            osqau.reputation += int(sxu.get('reputation'))
            osqau.gold += int(badges['1'])
            osqau.silver += int(badges['2'])
            osqau.bronze += int(badges['3'])

            merged_users.append(osqau.id)
            osqau.save()

        user_by_name[osqau.username] = osqau

        openid = sxu.get('openid', None)
        if openid and openidre.match(openid):
            assoc = orm.AuthKeyUserAssociation(user=osqau, key=openid, provider="openidurl")
            assoc.save()

    if uidmapper[-1] == -1:
        uidmapper[-1] = 1

    return (uidmapper, merged_users)

def tagsimport(dump, uidmap):
    tags = readTable(dump, "Tags")

    tagmap = {}

    for sxtag in tags:
        otag = orm.Tag(
            id = int(sxtag['id']),
            name = sxtag['name'],
            used_count = int(sxtag['count']),
            created_by_id = uidmap[sxtag.get('userid', 1)],
        )
        otag.save()

        tagmap[otag.name] = otag

    return tagmap

def postimport(dump, uidmap, tagmap):
    history = {}
    accepted = {}
    all = {}

    for h in readTable(dump, "PostHistory"):
        if not history.get(h.get('postid'), None):
            history[h.get('postid')] = []

        history[h.get('postid')].append(h)

    posts = readTable(dump, "Posts")

    for sxpost in posts:
        nodetype = (sxpost.get('posttypeid') == '1') and "nodetype" or "answer"

        post = orm.Node(
            node_type = nodetype,
            id = sxpost['id'],
            added_at = readTime(sxpost['creationdate']),
            body = sxpost['body'],
            score = sxpost.get('score', 0),
            author_id = sxpost.get('deletiondate', None) and 1 or uidmap[sxpost['owneruserid']]
        )

        post.save()

        create_action = orm.Action(
            action_type = (nodetype == "nodetype") and "ask" or "answer",
            user_id = post.author_id,
            node = post,
            action_date = post.added_at
        )

        create_action.save()

        #if sxpost.get('deletiondate', None):
        #    delete_action = orm.Action(
        #        action_type = "delete",
        #        user_id = 1,
        #        node = post,
        #        action_date = readTime(sxpost['deletiondate'])
        #    )

        #    delete_action.save()
        #    post.deleted = delete_action

        if sxpost.get('lasteditoruserid', None):
            revise_action = orm.Action(
                action_type = "revise",
                user_id = uidmap[sxpost.get('lasteditoruserid')],
                node = post,
                action_date = readTime(sxpost['lasteditdate']),
            )

            revise_action.save()
            post.last_edited = revise_action

        if sxpost.get('communityowneddate', None):
            post.wiki = True

            wikify_action = orm.Action(
                action_type = "wikify",
                user_id = 1,
                node = post,
                action_date = readTime(sxpost['communityowneddate'])
            )

            wikify_action.save()


        if sxpost.get('lastactivityuserid', None):
            post.last_activity_by_id = uidmap[sxpost['lastactivityuserid']]
            post.last_activity_at = readTime(sxpost['lastactivitydate'])

            
        if sxpost.get('posttypeid') == '1': #question
            post.node_type = "question"
            post.title = sxpost['title']

            tagnames = sxpost['tags'].replace(u'ö', '-').replace(u'é', '').replace(u'à', '')
            post.tagnames = tagnames

            post.extra_count = sxpost.get('viewcount', 0)

            #if sxpost.get('closeddate', None):
            #    post.marked = True
            #
            #    close_action = orm.Action(
            #        action_type = "close",
            #        user_id = 1,
            #        node = post,
            #        action_date = datetime.now() - timedelta(days=7)
            #    )
            #
            #    close_action.save()
            #    post.extra_action = close_action

            #if sxpost.get('acceptedanswerid', None):
            #    accepted[int(sxpost.get('acceptedanswerid'))] = post

            #post.save()

        else:
            post.parent_id = sxpost['parentid']

            #if int(post.id) in accepted:
                #post.marked = True

                #accept_action = orm.Action(
                #    action_type = "acceptanswer",
                #    user_id = accepted[int(post.id)].author_id,
                #    node = post,
                #    action_date = datetime.now() - timedelta(days=7)
                #)

                #accept_action.save()


                #post.accepted_at = datetime.now()
                #post.accepted_by_id = accepted[int(post.id)].author_id

                #accepted[int(post.id)].extra_ref = post
                #accepted[int(post.id)].save()

        post.save()

        all[int(post.id)] = post

    return all

def comment_import(dump, uidmap, posts):
    comments = readTable(dump, "PostComments")
    currid = max(posts.keys())
    mapping = {}

    for sxc in comments:
        currid += 1
        oc = orm.Node(
            id = currid,
            node_type = "comment",
            added_at = readTime(sxc['creationdate']),
            author_id = uidmap[sxc.get('userid', 1)],
            body = sxc['text'],
            parent_id = sxc.get('postid'),
        )

        if sxc.get('deletiondate', None):
            delete_action = orm.Action(
                action_type = "delete",
                user_id = uidmap[sxc['deletionuserid']],
                action_date = readTime(sxc['deletiondate'])
            )

            oc.author_id = uidmap[sxc['deletionuserid']]
            oc.save()

            delete_action.node = oc
            delete_action.save()

            oc.deleted = delete_action
        else:
            oc.author_id = uidmap[sxc.get('userid', 1)]
            oc.save()

        create_action = orm.Action(
            action_type = "comment",
            user_id = oc.author_id,
            node = oc,
            action_date = oc.added_at
        )

        create_action.save()
        oc.save()

        posts[oc.id] = oc
        mapping[int(sxc['id'])] = int(oc.id)

    return posts, mapping


def add_tags_to_posts(posts, tagmap):
    for post in posts.values():
        if post.node_type == "question":
            tags = [tag for tag in [tagmap.get(name.strip()) for name in post.tagnames.split(u' ') if name] if tag]
            post.tagnames = " ".join([t.name for t in tags]).strip()
            post.tags = tags

        create_and_activate_revision(post)


def create_and_activate_revision(post):
    rev = orm.NodeRevision(
        author_id = post.author_id,
        body = post.body,
        node_id = post.id,
        revised_at = post.added_at,
        revision = 1,
        summary = 'Initial revision',
        tagnames = post.tagnames,
        title = post.title,
    )

    rev.save()
    post.active_revision_id = rev.id
    post.save()

def post_vote_import(dump, uidmap, posts):
    votes = readTable(dump, "Posts2Votes")
    close_reasons = dict([(r['id'], r['name']) for r in readTable(dump, "CloseReasons")])

    user2vote = []

    for sxv in votes:
        action = orm.Action(
            user_id=uidmap[sxv['userid']],
            action_date = readTime(sxv['creationdate']),
        )

        node = posts.get(int(sxv['postid']), None)
        if not node: continue
        action.node = node

        if sxv['votetypeid'] == '1':
            answer = node
            question = posts.get(int(answer.parent_id), None)

            action.action_type = "acceptanswer"
            action.save()

            answer.marked = True
            answer.extra_action = action

            question.extra_ref_id = answer.id

            answer.save()
            question.save()

        elif sxv['votetypeid'] in ('2', '3'):
            if not (action.node.id, action.user_id) in user2vote:
                user2vote.append((action.node.id, action.user_id))

                action.action_type = (sxv['votetypeid'] == '2') and "voteup" or "votedown"
                action.save()

                ov = orm.Vote(
                    node_id = action.node.id,
                    user_id = action.user_id,
                    voted_at = action.action_date,
                    value = sxv['votetypeid'] == '2' and 1 or -1,
                    action = action
                )
                ov.save()
            else:
                action.action_type = "unknown"
                action.save()

        elif sxv['votetypeid'] in ('4', '12', '13'):
            action.action_type = "flag"
            action.save()

            of = orm.Flag(
                node = action.node,
                user_id = action.user_id,
                flagged_at = action.action_date,
                reason = '',
                action = action
            )

            of.save()

        elif sxv['votetypeid'] == '5':
            action.action_type = "favorite"
            action.save()

        elif sxv['votetypeid'] == '6':
            action.action_type = "close"
            action.extra = dbsafe_encode(close_reasons[sxv['comment']])
            action.save()

            node.marked = True
            node.extra_action = action
            node.save()

        elif sxv['votetypeid'] == '7':
            action.action_type = "unknown"
            action.save()
            
            node.marked = False
            node.extra_action = None
            node.save()

        elif sxv['votetypeid'] == '10':
            action.action_type = "delete"
            action.save()

            node.deleted = action
            node.save()

        elif sxv['votetypeid'] == '11':
            action.action_type = "unknown"
            action.save()

            node.deleted = None
            node.save()

        else:
            action.action_type = "unknown"
            action.save()


        if sxv.get('targetrepchange', None):
            rep = orm.ActionRepute(
                action = action,
                date = action.action_date,
                user_id = uidmap[sxv['targetuserid']],
                value = int(sxv['targetrepchange'])
            )

            rep.save()

        if sxv.get('voterrepchange', None):
            rep = orm.ActionRepute(
                action = action,
                date = action.action_date,
                user_id = uidmap[sxv['userid']],
                value = int(sxv['voterrepchange'])
            )

            rep.save()


def comment_vote_import(dump, uidmap, comments, posts):
    votes = readTable(dump, "Comments2Votes")
    user2vote = []

    for sxv in votes:
        if sxv['votetypeid'] == "2":
            comment_id = comments[int(sxv['postcommentid'])]
            user_id = uidmap[sxv['userid']]

            if not (comment_id, user_id) in user2vote:
                user2vote.append((comment_id, user_id))

                action = orm.Action(
                    action_type = "voteupcomment",
                    user_id = user_id,
                    action_date = readTime(sxv['creationdate']),
                    node_id = comment_id
                )
                action.save()

                ov = orm.Vote(
                    node_id = comment_id,
                    user_id = user_id,
                    voted_at = action.action_date,
                    value = 1,
                    action = action
                )

                ov.save()

                posts[int(action.node_id)].score += 1
                posts[int(action.node_id)].save()



def badges_import(dump, uidmap, post_list):
    node_ctype = orm['contenttypes.contenttype'].objects.get(name='node')
    obadges = dict([(b.cls, b) for b in orm.Badge.objects.all()])
    sxbadges = dict([(int(b['id']), b) for b in readTable(dump, "Badges")])
    user_badge_count = {}

    sx_to_osqa = {}

    for id, sxb in sxbadges.items():
        cls = "".join(sxb['name'].replace('&', 'And').split(' '))

        if cls in obadges:
            sx_to_osqa[id] = obadges[cls]
        else:
            osqab = orm.Badge(
                cls = cls,
                awarded_count = 0,
                type = sxb['class']                
            )
            osqab.save()
            sx_to_osqa[id] = osqab

    sxawards = readTable(dump, "Users2Badges")
    osqaawards = []

    for sxa in sxawards:
        badge = sx_to_osqa[int(sxa['badgeid'])]

        user_id = uidmap[sxa['userid']]
        if not user_badge_count.get(user_id, None):
            user_badge_count[user_id] = 0

        action = orm.Action(
            action_type = "award",
            user_id = user_id,
            action_date = readTime(sxa['date'])
        )

        action.save()

        osqaa = orm.Award(
            user_id = uidmap[sxa['userid']],
            badge = badge,
            node = post_list[user_badge_count[user_id]],
            awarded_at = action.action_date,
            action = action
        )

        osqaa.save()
        badge.awarded_count += 1
        user_badge_count[user_id] += 1

    for badge in obadges.values():
        badge.save()


def reset_sequences():
    from south.db import db
    if db.backend_name == "postgres":
        db.start_transaction()
        db.execute_many(PG_SEQUENCE_RESETS)
        db.commit_transaction()

def sximport(dump, options):
    uidmap, merged_users = userimport(dump, options)
    tagmap = tagsimport(dump, uidmap)
    posts = postimport(dump, uidmap, tagmap)
    posts, comments = comment_import(dump, uidmap, posts)
    add_tags_to_posts(posts, tagmap)
    post_vote_import(dump, uidmap, posts)
    comment_vote_import(dump, uidmap, comments, posts)
    badges_import(dump, uidmap, posts.values())

    from south.db import db
    db.commit_transaction()

    reset_sequences()

    
    
PG_SEQUENCE_RESETS = """
SELECT setval('"auth_user_id_seq"', coalesce(max("id"), 1) + 2, max("id") IS NOT null) FROM "auth_user";
SELECT setval('"auth_user_groups_id_seq"', coalesce(max("id"), 1) + 2, max("id") IS NOT null) FROM "auth_user_groups";
SELECT setval('"auth_user_user_permissions_id_seq"', coalesce(max("id"), 1) + 2, max("id") IS NOT null) FROM "auth_user_user_permissions";
SELECT setval('"forum_keyvalue_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_keyvalue";
SELECT setval('"forum_action_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_action";
SELECT setval('"forum_actionrepute_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_actionrepute";
SELECT setval('"forum_subscriptionsettings_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_subscriptionsettings";
SELECT setval('"forum_validationhash_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_validationhash";
SELECT setval('"forum_authkeyuserassociation_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_authkeyuserassociation";
SELECT setval('"forum_tag_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_tag";
SELECT setval('"forum_markedtag_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_markedtag";
SELECT setval('"forum_node_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_node";
SELECT setval('"forum_node_tags_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_node_tags";
SELECT setval('"forum_noderevision_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_noderevision";
SELECT setval('"forum_node_tags_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_node_tags";
SELECT setval('"forum_questionsubscription_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_questionsubscription";
SELECT setval('"forum_node_tags_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_node_tags";
SELECT setval('"forum_node_tags_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_node_tags";
SELECT setval('"forum_vote_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_vote";
SELECT setval('"forum_flag_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_flag";
SELECT setval('"forum_badge_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_badge";
SELECT setval('"forum_award_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_award";
SELECT setval('"forum_openidnonce_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_openidnonce";
SELECT setval('"forum_openidassociation_id_seq"', coalesce(max("id"), 1), max("id") IS NOT null) FROM "forum_openidassociation";
"""


    
    