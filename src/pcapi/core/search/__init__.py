import logging
from typing import Iterable

from pcapi import settings
import pcapi.core.offers.models as offers_models
from pcapi.repository import offer_queries
from pcapi.utils.module_loading import import_string


logger = logging.getLogger(__name__)


def _get_backend():
    return import_string(settings.EMAIL_BACKEND)


def async_index_offer_ids(offer_ids: Iterable[int]) -> None:
    """Ask for an asynchronous reindexation of the given list of
    ``Offer.id``.

    This function returns quickly. The "real" reindexation will be
    done later through a cron job.
    """
    backend = _get_backend()
    backend.enqueue_offer_ids(offer_ids)


def index_offers_in_queue(stop_only_when_empty: bool = False, from_error_queue: bool = False) -> None:
    """Pop offers from indexation queue and reindex them.

    If ``from_error_queue`` is True, pop offers from the error queue
    instead of the "standard" indexation queue.

    If ``stop_only_when_empty`` is False (i.e. if called as a cron
    command), we pop from the queue at least once, and stop when there
    is less than REDIS_OFFER_IDS_CHUNK_SIZE in the queue (otherwise
    the cron job may never stop). It means that a cron job may run for
    a long time if the queue has many items. In fact, a subsequent
    cron job may run in parallel if the previous one has not finished.
    It's fine because they both pop from the queue.

    If ``stop_only_when_empty`` is True (i.e. if called from the
    ``process_offers`` Flask command), we pop from the queue and stop
    only when the queue is empty.
    """
    backend = _get_backend()

    while True:
        # We must pop and not get-and-delete. Otherwise two concurrent
        # cron jobs could delete the wrong offers from the queue:
        # 1. Cron job 1 gets the first 1.000 offers from the queue.
        # 2. Cron job 2 gets the same 1.000 offers from the queue.
        # 3. Cron job 1 finishes processing the batch and deletes the
        #    first 1.000 offers from the queue. OK.
        # 4. Cron job 2 finishes processing the batch and also deletes
        #    the first 1.000 offers from the queue. Not OK, these are
        #    not the same offers it just processed!
        offer_ids = backend.pop_offer_ids_from_queue(
            count=settings.REDIS_OFFER_IDS_CHUNK_SIZE, from_error_queue=from_error_queue
        )
        if not offer_ids:
            break

        logger.info("Fetched offers from indexation queue", extra={"count": len(offer_ids)})
        try:
            reindex_offer_ids(offer_ids)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Exception while reindexing offers, must fix manually",
                extra={
                    "exc": str(exc),
                    "offers": offer_ids,
                },
            )
        else:
            logger.info(
                "Reindexed offers from queue", extra={"count": len(offer_ids), "from_error_queue": from_error_queue}
            )

        left_to_process = backend.count_offers_to_index_from_queue()
        if not stop_only_when_empty and left_to_process < settings.REDIS_OFFER_IDS_CHUNK_SIZE:
            break


def index_venues_in_queue():
    """Pop venues from indexation queue and reindex their offers."""
    backend = _get_backend()

    venue_ids = backend.get_venue_ids_from_queue(count=settings.REDIS_VENUE_IDS_CHUNK_SIZE)
    for venue_id in venue_ids:
        page = 0
        logger.info("Starting to index offers of venue", extra={"venue": venue_id})
        while True:
            offer_ids = offer_queries.get_paginated_offer_ids_by_venue_id(
                limit=settings.ALGOLIA_OFFERS_BY_VENUE_CHUNK_SIZE, page=page, venue_id=venue_id
            )
            if not offer_ids:
                break
            reindex_offer_ids(offer_ids)
            page += 1
        logger.info("Finished indexing offers of venue", extra={"venue": venue_id})

    # FIXME (dbaty, 2021-06-18): despite the name, this function does
    # not delete all items from the queue. With the Algolia backend,
    # it LTRIM on a list. Since we RPUSH to add, we would not lose any
    # venue if it was added during the loop above. Still, that looks
    # odd. The App Search backend should rather use a set and remove
    # only processed venues.
    backend.delete_venue_ids_from_queue(venue_ids)


def reindex_offer_ids(offer_ids):
    """Given a list of `Offer.id`, reindex or unindex each offer
    (i.e. request the external indexation service an update or a
    removal).

    This function calls the external indexation service and may thus
    be slow. It should not be called by usual code. You should rather
    call `async_index_offer_ids()` instead to return quickly.
    """
    backend = _get_backend()

    to_add = []
    to_delete = []
    # FIXME (dbaty, 2021-06-16): join-load Stock, Venue and Offerer to
    # avoid N+1 queries on each offer.
    offers = offers_models.Offer.query(offers_models.Offer.id.in_(offer_ids))
    for offer in offers:
        if offer and offer.isBookable:
            to_add.append(offer)
        elif backend.check_offer_is_indexed(offer):
            to_delete.append(offer)
        else:
            # FIXME (dbaty, 2021-06-24). I think we could safely do
            # without the hashmap in Redis. Check the logs and see if
            # I am right!
            logger.info(
                "Redis 'indexed_offers' set saved use from an unnecessary request to indexation service",
                extra={"source": "reindex_offer_ids", "offer": offer.id},
            )

    # Handle new or updated available offers
    try:
        backend.index_offers(to_add)
    except Exception as exc:
        logger.warning(
            "Could not reindex offers, will automatically retry",
            extra={"exc": str(exc), "offers": [offer.id for offer in to_add]},
            exc_info=True,
        )
        backend.enqueue_offers_in_error(to_add)

    # Handle unavailable offers (deleted, expired, sold out, etc.)
    try:
        backend.unindex_offer_ids([offer.id for offer in to_delete])
    except Exception as exc:
        logger.warning(
            "Could not unindex offers, will automatically retry",
            extra={"exc": str(exc), "offers": [offer.id for offer in to_add]},
            exc_info=True,
        )
        backend.enqueue_offers_in_error(to_delete)


def delete_offer_ids(offer_ids: Iterable[int]):
    backend = _get_backend()
    backend.unindex_offer_ids(offer_ids)
