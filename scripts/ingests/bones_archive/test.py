from astrodb_utils import load_astrodb
from simple.schema import *
from simple.schema import REFERENCE_TABLES

db = load_astrodb("SIMPLE.sqlite", recreatedb=True, reference_tables=REFERENCE_TABLES)