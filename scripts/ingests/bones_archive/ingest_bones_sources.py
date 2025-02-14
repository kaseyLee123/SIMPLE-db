from simple.schema import *
from simple.schema import REFERENCE_TABLES
from astrodb_utils import (
    load_astrodb,
    find_source_in_db,
    AstroDBError,
    ingest_names,
    ingest_source,
    ingest_publication,
    find_publication,
    logger,
)

import sys

sys.path.append(".")
import logging
from astropy.io import ascii


def extractADS(link):
    start = link.find("abs/") + 4
    end = link.find("/abstract")
    ads = link[start:end]
    ads = ads.replace("%26", "&")
    logger.debug(f"ads: {ads}")
    return ads


logger.setLevel(logging.INFO)

names_ingested = 0
sources_ingested = 0
skipped = 0
total = 0
already_exists = 0
multiple_sources = 0
no_sources = 0
inside_if = 0


DB_SAVE = False
RECREATE_DB = True
db = load_astrodb("SIMPLE.sqlite", recreatedb=RECREATE_DB, reference_tables=REFERENCE_TABLES)

ingest_publication(db, bibcode="2018MNRAS.479.1383Z", reference="Zhan18.1352")
ingest_publication(db, bibcode="2018MNRAS.480.5447Z", reference="Zhan18.2054")

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


for source in bones_sheet_table:
    bones_name = source["NAME"]
    match = None

    if len(bones_name) > 0 and bones_name != "null":
        match = find_source_in_db(
            db,
            source["NAME"],
            ra=source["RA"],
            dec=source["DEC"],
            ra_col_name="ra",
            dec_col_name="dec",
        )
        if len(match) == 1:
            try:
                ingest_names(
                    db, match[0], bones_name
                )  # ingest new names while were at it
                names_ingested += 1
            except AstroDBError as e:
                raise e  # only error is if there is a preexisting name anyways.

    if match is None:
        match = find_source_in_db(
            db,
            source["NAME"],
            ra=source["RA"],
            dec=source["DEC"],
            ra_col_name="ra",
            dec_col_name="dec",
        )

    if len(match) == 0:
        # ingest_publications for the ADS link
        ads = extractADS(source["ADS_Link"])
        adsMatch = None
        adsRef = source["Discovery Ref."]
        adsMatch = find_publication(
            db,
            bibcode = ads
        )
        logger.debug(f"adsMatch: {adsMatch}")

        if not adsMatch[0]:
            logger.debug(f"ingesting publication {ads}")
            ingest_publication(
                db,
                bibcode=ads,
            )

        try:
            source_reference = find_publication(db, bibcode=ads)

            ingest_source(
                db,
                source=source["NAME"],
                reference=source_reference[1],
                ra=source["RA"],
                dec=source["DEC"],
                raise_error=True,
                search_db=True,
                ra_col_name="ra",
                dec_col_name="dec",
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
