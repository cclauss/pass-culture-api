from enum import Enum
import logging

import redis
from redis import Redis
from redis.client import Pipeline

from pcapi import settings


logger = logging.getLogger(__name__)


class RedisBucket(Enum):
    REDIS_LIST_OFFER_IDS_NAME = "offer_ids"
    REDIS_LIST_OFFER_IDS_IN_ERROR_NAME = "offer_ids_in_error"
    REDIS_LIST_VENUE_IDS_NAME = "venue_ids"
    REDIS_HASHMAP_INDEXED_OFFERS_NAME = "indexed_offers"


def add_offer_id(client: Redis, offer_id: int) -> None:
    try:
        client.rpush(RedisBucket.REDIS_LIST_OFFER_IDS_NAME.value, offer_id)
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)


def add_venue_id(client: Redis, venue_id: int) -> None:
    try:
        client.rpush(RedisBucket.REDIS_LIST_VENUE_IDS_NAME.value, venue_id)
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)


def check_offer_exists(client: Redis, offer_id: int) -> bool:
    try:
        offer_exist = client.hexists(RedisBucket.REDIS_HASHMAP_INDEXED_OFFERS_NAME.value, offer_id)
        return offer_exist
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)
        return False


def delete_all_indexed_offers(client: Redis) -> None:
    try:
        client.delete(RedisBucket.REDIS_HASHMAP_INDEXED_OFFERS_NAME.value)
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)


def add_offer_ids_in_error(client: Redis, offer_ids: list[int]) -> None:
    try:
        client.rpush(RedisBucket.REDIS_LIST_OFFER_IDS_IN_ERROR_NAME.value, *offer_ids)
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)


def get_offer_ids_in_error(client: Redis) -> list[int]:
    try:
        offer_ids = client.lrange(
            RedisBucket.REDIS_LIST_OFFER_IDS_IN_ERROR_NAME.value, 0, settings.REDIS_OFFER_IDS_CHUNK_SIZE
        )
        return offer_ids
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)
        return []


def delete_offer_ids_in_error(client: Redis) -> None:
    try:
        client.ltrim(
            RedisBucket.REDIS_LIST_OFFER_IDS_IN_ERROR_NAME.value, settings.REDIS_OFFER_IDS_IN_ERROR_CHUNK_SIZE, -1
        )
    except redis.exceptions.RedisError as error:
        logger.exception("[REDIS] %s", error)
