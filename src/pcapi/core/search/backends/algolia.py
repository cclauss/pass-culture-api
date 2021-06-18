import logging
from typing import Iterable

import algoliasearch.search_client
from flask.app import current_app
import redis

from pcapi import settings
import pcapi.core.offers.models as offers_models
from pcapi.core.search.backends import base


logger = logging.getLogger(__name__)

REDIS_LIST_OFFER_IDS_NAME = "offer_ids"
REDIS_LIST_OFFER_IDS_IN_ERROR_NAME = "offer_ids_in_error"
REDIS_LIST_VENUE_IDS_NAME = "venue_ids"
REDIS_HASHMAP_INDEXED_OFFERS_NAME = "indexed_offers"


class AlgoliaBackend(base.SearchBackend):
    def __init__(self):
        super().__init__()
        self.algolia_client = algoliasearch.search_client.SearchClient.create(
            settings.ALGOLIA_APPLICATION_ID, settings.ALGOLIA_API_KEY
        )
        self.redis_client = current_app.redis_client

    def enqueue_offer_ids(self, offer_ids: Iterable[int]):
        try:
            for offer_id in offer_ids:
                self.redis_client.rpush(REDIS_LIST_OFFER_IDS_NAME, offer_id)
        except redis.exceptions.RedisError:
            logger.exception("Could not add offers to indexation queue", extra={"offers": offer_ids})

    def enqueue_offer_ids_in_error(self, offer_ids: Iterable[int]):
        try:
            for offer_id in offer_ids:
                self.redis_client.rpush(REDIS_LIST_OFFER_IDS_IN_ERROR_NAME, offer_id)
        except redis.exceptions.RedisError:
            logger.exception("Could not add offers to error queue", extra={"offers": offer_ids})

    def pop_offer_ids_from_queue(self, count: int, from_error_queue: bool = False) -> set[int]:
        # Here we should use `LPOP` but its `count` argument has been
        # added in Redis 6.2. GCP currently has an earlier version of
        # Redis (5.0), where we can pop only one item at once. As a
        # work around, we get and delete items within a pipeline,
        # which should be atomic.
        #
        # The error handling is minimal:
        # - if the get fails, the function returns an empty list. It's
        #   fine, the next run may have more chance and may work;
        # - if the delete fails, we'll process the same batch
        #   twice. It's not optimal, but it's ok.
        if from_error_queue:
            redis_list_name = REDIS_LIST_OFFER_IDS_IN_ERROR_NAME
        else:
            redis_list_name = REDIS_LIST_OFFER_IDS_NAME

        offer_ids = set()
        try:
            pipeline = self.redis_client.pipeline(transaction=True)
            pipeline.lrange(redis_list_name, 0, count - 1)
            pipeline.ltrim(redis_list_name, count, -1)
            results = pipeline.execute()
            offer_ids = {int(offer_id) for offer_id in results[0]}  # str -> int
        except redis.exceptions.RedisError:
            logger.exception("Could not pop offer ids to index from queue")
        finally:
            pipeline.reset()
        return offer_ids

    def get_venue_ids_from_queue(self, count: int) -> [int]:
        try:
            return self.redis_client.lrange(REDIS_LIST_VENUE_IDS_NAME, 0, count)
        except redis.exceptions.RedisError:
            logger.exception("Could not get venue ids to index from queue")
            return []

    def delete_venue_ids_from_queue(self, venue_ids: Iterable[int]) -> None:
        try:
            self.redis_client.ltrim(REDIS_LIST_VENUE_IDS_NAME, len(venue_ids), -1)
        except redis.exceptions.RedisError:
            logger.exception("Could not delete indexed venue ids from queue")

    def count_offers_to_index_from_queue(self):
        try:
            return self.redis_client.llen(REDIS_LIST_OFFER_IDS_NAME)
        except redis.exceptions.RedisError:
            logger.exception("Could not count offers left to index from queue")
            return 0

    def index_offers(self, offers: Iterable[offers_models.Offer]) -> None:
        objects = [self.serialize_offer(offer) for offer in offers]
        self.algolia_client.add_objects(objects)
        try:
            # We used to store a summary of each offer, which is why
            # we used hashmap and not a set. But since we don't need
            # the value anymore, we can store the lightest object
            # possible to make Redis use less memory. In the future,
            # we may even remove the hashmap if it's not proven useful
            # (see log n reindex_offer_ids)
            offer_ids = [offer.id for offer in offers]
            pipeline = self.redis_client.pipeline(transaction=True)
            for offer_id in offer_ids:
                pipeline.hset(REDIS_HASHMAP_INDEXED_OFFERS_NAME, offer_id, "")
            pipeline.execute()
        except:
            logger.exception("Could not add to list of indexed offers", extra={"offers": offer_ids})
        finally:
            pipeline.reset()

    def unindex_offer_ids(self, offer_ids: Iterable[int]) -> None:
        self.algolia_client.delete_objects(offer_ids)
        try:
            self.redis_client.hdel(REDIS_HASHMAP_INDEXED_OFFERS_NAME, *offer_ids)
        except redis.exceptions.RedisError:
            logger.exception("Could not remove offers from indexed offers set", extra={"offers": offer_ids})

    def serialize_offer(self, offer: offers_models.Offer) -> dict:
        return {}  # FIXME: that won't do, I am afraid
