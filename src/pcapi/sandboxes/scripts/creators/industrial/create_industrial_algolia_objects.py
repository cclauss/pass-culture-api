import logging

from flask import current_app as app

from pcapi import settings
from pcapi.algolia.infrastructure.api import clear_index
from pcapi.connectors.redis import delete_all_indexed_offers
from pcapi.core import search
from pcapi.models import Offer


logger = logging.getLogger(__name__)


def create_industrial_algolia_indexed_objects() -> None:
    if settings.ALGOLIA_TRIGGER_INDEXATION:
        logger.info("create_industrial_algolia_objects")
        offer_ids = Offer.query.with_entities(Offer.id).all()
        clear_index()
        delete_all_indexed_offers(client=app.redis_client)
        search.reindex_offer_ids(offer_ids)
