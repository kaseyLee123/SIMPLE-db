from astrodb_utils import load_astrodb
from simple.schema import *
from simple.schema import REFERENCE_TABLES
from astrodb_utils import (
    load_astrodb,
    find_source_in_db,
    AstroDBError,
    ingest_names,
    ingest_source,
    ingest_publication,
    find_publication
)

import sys

sys.path.append(".")
import logging
from astropy.io import ascii
from simple.schema import Photometry
from simple.schema import REFERENCE_TABLES
from math import isnan
import sqlalchemy.exc
from simple.utils.astrometry import ingest_parallax

logger = logging.getLogger(__name__)
names_ingested = 0
sources_ingested = 0
skipped = 0
total = 0
already_exists = 0
multiple_sources = 0
no_sources = 0
inside_if = 0

# Logger setup
# This will stream all logger messages to the standard output and
# apply formatting for that
logger.propagate = False  # prevents duplicated logging messages
LOGFORMAT = logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S%p"
)
ch = logging.StreamHandler(stream=sys.stdout)
ch.setFormatter(LOGFORMAT)
# To prevent duplicate handlers, only add if they haven't been set previously
if len(logger.handlers) == 0:
    logger.addHandler(ch)
logger.setLevel(logging.INFO)

DB_SAVE = False
RECREATE_DB = True
db = load_astrodb("SIMPLE.sqlite", recreatedb=RECREATE_DB, reference_tables=REFERENCE_TABLES)

link = (
    "scripts/ingests/bones_archive/theBonesArchivePhotometryWithADS.csv"
)

# read the csv data into an astropy table
bones_sheet_table = ascii.read(
    link,
    format="csv",
    data_start=1,
    header_start=0,
    guess=False,
    fast_reader=False,
    delimiter=",",
)

def extractADS(link):
    start = link.find('abs/') + 4
    end = link.find('/abstract')
    ads = link[start:end]
    return ads


for source in bones_sheet_table:
    bones_name = source["NAME"]
    match = None

    if len(bones_name) > 0 and bones_name != "null":
        match = find_source_in_db(
            db,
            source["NAME"],
            ra=source["RA"],
            dec=source["DEC"],
        )
        if len(match) == 1:
            try:
                ingest_names(
                    db, match[0], bones_name
                )  # ingest new names while were at it
                names_ingested += 1
            except AstroDBError as e:
                None  # only error is if there is a preexisting name anyways.

    if match == None:
         match = find_source_in_db(
            db,
            source["NAME"],
            ra=source["RA"],
            dec=source["DEC"],
        )
        
      

    if len(match) == 0:
        #ingest_publications for the ADS link
        ads = extractADS(source["ADS_Link"])
        adsMatch = None
        adsRef = source["Discovery Ref."]
        adsMatch = find_publication(
            db,
            bibcode = ads
        )

        if adsMatch[0] == False:
            ingest_publication(
                db,
                bibcode = ads,
                reference = adsRef
            )

        try:
            source_reference = find_publication(db, bibcode=ads)
            source_name = source["NAME"]
            source_ra=source["RA"]
            source_dec=source["DEC"]

            ingest_source(
                db,
                source = source_name,
                reference = source_reference[1],
                ra = source_ra,
                dec = source_dec,
                raise_error = True,
                search_db = True

               
                
            )
            sources_ingested +=1
        except AstroDBError as e:
            msg = "ingest failed with error " + str(e)
            logger.warning(msg)
            skipped += 1
            if "Already in database" in str(e):
                already_exists += 1
            else: 
                raise AstroDBError(msg) from e
        
    elif len(match) == 1:
        skipped+=1
        already_exists += 1

    else:
        skipped+=1
        a = AstroDBError
        logger.warning("ingest failed with error: " + str(a))
        raise AstroDBError(msg) from a

            

total = len(bones_sheet_table)
logger.info(f"skipped:{skipped}") # 92 skipped
logger.info(f"sources_ingested:{sources_ingested}") # 117 ingsted 
logger.info(f"total: {total}") # 209 total
logger.info(f"already_exists: {already_exists}") # 92 already exists

logger.info(f"names_ingested:{names_ingested}")
if DB_SAVE:
    db.save_database(directory="data/")



