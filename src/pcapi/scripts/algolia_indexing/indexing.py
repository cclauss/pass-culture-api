import datetime
import logging

from redis import Redis

from pcapi import settings
from pcapi.algolia.usecase.orchestrator import process_eligible_offers
from pcapi.core import search
from pcapi.core.offers.models import Offer
import pcapi.core.offers.repository as offers_repository
from pcapi.repository import offer_queries
from pcapi.utils.converter import from_tuple_to_int


logger = logging.getLogger(__name__)


def batch_indexing_offers_in_algolia_from_database(
    client: Redis, ending_page: int = None, limit: int = 10000, starting_page: int = 0
) -> None:
    page_number = starting_page
    has_still_offers = True

    while has_still_offers:
        if ending_page:
            if ending_page == page_number:
                break

        offer_ids_as_tuple = offer_queries.get_paginated_active_offer_ids(limit=limit, page=page_number)
        offer_ids_as_int = from_tuple_to_int(offer_ids=offer_ids_as_tuple)

        if len(offer_ids_as_int) > 0:
            logger.info("[ALGOLIA] processing offers of database from page %s...", page_number)
            process_eligible_offers(client=client, offer_ids=offer_ids_as_int)
            logger.info("[ALGOLIA] offers of database from page %s processed!", page_number)
        else:
            has_still_offers = False
            logger.info("[ALGOLIA] processing of offers from database finished!")
        page_number += 1


def batch_deleting_expired_offers_in_algolia(client: Redis, process_all_expired: bool = False) -> None:
    """Request an asynchronous unindex of offers that have expired within
    the last 2 days.

    For example, if run on Thursday (whatever the time), this function
    handles offers that have expired between Tuesday 00:00 and
    Wednesday 23:59 (included).
    """
    start_of_day = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    interval = [start_of_day - datetime.timedelta(days=2), start_of_day]
    if process_all_expired:
        interval[0] = datetime.datetime(2000, 1, 1)  # arbitrary old date

    page = 0
    limit = settings.ALGOLIA_DELETING_OFFERS_CHUNK_SIZE
    while True:
        offers = offers_repository.get_expired_offers(interval)
        offers = offers.offset(page * limit).limit(limit)
        offer_ids = [offer_id for offer_id, in offers.with_entities(Offer.id)]

        if not offer_ids:
            break

        logger.info("[ALGOLIA] Found %d expired offers to unindex", len(offer_ids))
        search.delete_offer_ids(offer_ids=offer_ids)
        page += 1
