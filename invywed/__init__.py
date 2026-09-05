# PyMySQL Configuration untuk MariaDB/MySQL
import pymysql

# Install PyMySQL sebagai MySQLdb
pymysql.install_as_MySQLdb()

# Set versi minimum untuk MariaDB (opsional, untuk menghindari warning)
pymysql.version_info = (1, 4, 6, "final", 0)

# Workaround untuk MariaDB 10.4 compatibility dengan Django 4.2
# Bypass version check untuk MariaDB 10.4
import django.db.backends.mysql.base
from django.db.backends.base.base import BaseDatabaseWrapper

# Override check_database_version_supported untuk bypass version check
_original_check = BaseDatabaseWrapper.check_database_version_supported

def patched_check_database_version_supported(self):
    try:
        return _original_check(self)
    except Exception as e:
        # Jika error karena versi MariaDB, bypass saja
        if 'MariaDB' in str(e) or '10.4' in str(e):
            return
        raise

BaseDatabaseWrapper.check_database_version_supported = patched_check_database_version_supported

# Disable RETURNING clause untuk MariaDB 10.4 (tidak support RETURNING)
from django.db.models.sql.compiler import SQLInsertCompiler

_original_execute_sql = SQLInsertCompiler.execute_sql

def patched_execute_sql(self, returning_fields=None):
    # MariaDB 10.4 tidak support RETURNING, set ke None
    return _original_execute_sql(self, returning_fields=None)

SQLInsertCompiler.execute_sql = patched_execute_sql

