import sys

if not (sys.version_info[0] >= 3 and sys.version_info[1] >= 6):
    PY3STATEMENT = "The minimal Python requirement is Python 3.6"
    raise Exception(PY3STATEMENT)
