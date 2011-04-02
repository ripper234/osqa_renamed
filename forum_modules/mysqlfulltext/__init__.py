NAME = 'Mysql Full Text Search'
DESCRIPTION = "Enables Mysql full text search functionality."

try:
    import MySQLdb
    from django.conf import settings
    CAN_USE = settings.DATABASE_ENGINE == 'mysql'
except:
    CAN_USE = False
  