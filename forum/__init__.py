
# Attempt to update mysql tables

#from django.dispatch import dispatcher
#from django.db.models import signals
#
#def modify_MySQL_storage(sender, app, created_models, verbosity, interactive):
#    from django.db import connection
#    cursor = connection.cursor()
#
#    print "[debug] Modifying MySQL storage..."
#
##    for model in created_models:
##        db_table=model._meta.db_table
##        if db_table not in skip:
##            skip.add(db_table)
##            engine = storage.get(model._meta.db_table,default_storage)
##            stmt = 'ALTER TABLE %s ENGINE=%s' % (db_table,engine)
##            if verbosity > 1: print '  ',stmt
##            cursor.execute(stmt)
#
## Modify SQL storage after any app installs
#dispatcher.connect(modify_MySQL_storage,signal=signals.post_syncdb)

print "[DEBUG] init called."

try:
    from south.signals import post_migrate

    def post_migrate_callback(sender, **kwargs):
        print "[DEBUG] post_migrate_callback called!"

        # Import the needed libraries to use the database and detect the
        # DB engine/sever type being currently employed.
        from django.db import connection, connections

        # Get the DB engine being used for persistence for this app.
        current_db_engine = connections.databases[connection.alias]['ENGINE']
        print "[DEBUG] Current DB engine: %(engine)s" % {"engine":current_db_engine}

        # Make sure the updates are only executed for a MySQL DB.
        if current_db_engine.find("mysql") > 0:
            # Ok, mysql was found in the engine description.  Go ahead
            # and attempt to execute the alter table statements.
            cursor = connection.cursor()

            # Pair the table names with the columns that need to be updated.
            updatable_table_columns = {
                "forum_tag":"name",
                "auth_user":"username"
            }

            # Update each column in turn.
            for table_name, column_name in updatable_table_columns.iteritems():
                alter_table_statement = "ALTER TABLE %(table_name)s MODIFY %(column_name)s varchar(255) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL;" % {"table_name":table_name,"column_name":column_name}
                #print "[DEBUG] Executing statement: " + alter_table_statement
                cursor.execute(alter_table_statement)

    print "[DEBUG] Connecting to post_migrate signal."
    post_migrate.connect(post_migrate_callback)
except:
    pass

print "[DEBUG] init finished."