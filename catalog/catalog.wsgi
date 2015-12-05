#!/user/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/var/www/FSND-P3-Catalog-App/catalog/")
from catalog import app as application#
application.secret_key = "really_lame_key"