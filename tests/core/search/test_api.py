from unittest import mock

import pytest

from pcapi.core import search
import pcapi.core.offers.factories as offers_factories
from pcapi.core.testing import override_settings


pytestmark = pytest.mark.usefixtures("db_session")


@override_settings()
def test_async_index_offer_ids():
    pass


class ReindexOfferIdsTest:
    def test_basics(self):

        pass


# FIXME (dbaty, 2021-06-25): the lack of Redis in tests makes these
# tests painful to write and read.
@override_settings(REDIS_OFFER_IDS_CHUNK_SIZE=3)
@mock.patch("pcapi.core.search._reindex_offer_ids")
class IndexOffersInQueueTest:
    def test_cron_behaviour(self, mocked_reindex_offer_ids):
        queue = list(range(1, 9))  # 8 items: 1..8

        def fake_pop(self, count, from_error_queue):
            assert count == 3  # overriden REDIS_OFFER_IDS_CHUNK_SIZE
            assert not from_error_queue
            popped = set()
            for _i in range(count):
                try:
                    popped.add(queue.pop(0))
                except IndexError:  # queue is empty
                    break
            return popped

        def fake_len(self, queue_name):
            return len(queue)

        with mock.patch("pcapi.core.search.backends.testing.TestingBackend.pop_offer_ids_from_queue", fake_pop):
            with mock.patch("redis.Redis.llen", fake_len):
                search.index_offers_in_queue()

        # First run pops and indexes 1, 2, 3. Second run pops and
        # indexes 4, 5, 6. And stops because there are less than
        # REDIS_OFFER_IDS_CHUNK_SIZE items left in the queue.
        # fmt: off
        assert mocked_reindex_offer_ids.mock_calls == [
            mock.call(mock.ANY, {1, 2, 3}),
            mock.call(mock.ANY, {4, 5, 6})
        ]
        # fmt: on
        assert queue == [7, 8]

    def test_command_behaviour(self, mocked_reindex_offer_ids):
        queue = list(range(1, 9))  # 8 items: 1..8

        def fake_pop(self, count, from_error_queue):
            assert count == 3  # overriden REDIS_OFFER_IDS_CHUNK_SIZE
            assert not from_error_queue
            popped = set()
            for _i in range(count):
                try:
                    popped.add(queue.pop(0))
                except IndexError:  # queue is empty
                    break
            return popped

        def fake_len(self, queue_name):
            return len(queue)

        with mock.patch("pcapi.core.search.backends.testing.TestingBackend.pop_offer_ids_from_queue", fake_pop):
            with mock.patch("redis.Redis.llen", fake_len):
                search.index_offers_in_queue(stop_only_when_empty=True)

        # First run pops and indexes 1, 2, 3. Second run pops and
        # indexes 4, 5, 6. Third run pops 7, 8 and stops because the
        # queue is empty.
        assert mocked_reindex_offer_ids.mock_calls == [
            mock.call(mock.ANY, {1, 2, 3}),
            mock.call(mock.ANY, {4, 5, 6}),
            mock.call(mock.ANY, {7, 8}),
        ]
        assert queue == []


@override_settings(ALGOLIA_OFFERS_BY_VENUE_CHUNK_SIZE=2)
@mock.patch("pcapi.core.search.backends.testing.TestingBackend.get_venue_ids_from_queue")
@mock.patch("pcapi.core.search.backends.testing.TestingBackend.delete_venue_ids_from_queue")
@mock.patch("pcapi.core.search.reindex_offer_ids")
def test_index_venues_in_queue(
    mock_reindex_offer_ids,
    mock_delete_venue_ids_from_queue,
    mock_get_venue_ids_from_queue,
):
    venue1 = offers_factories.VenueFactory()
    offer1 = offers_factories.OfferFactory(venue=venue1)
    offer2 = offers_factories.OfferFactory(venue=venue1)
    offer3 = offers_factories.OfferFactory(venue=venue1)
    venue2 = offers_factories.VenueFactory()
    offer4 = offers_factories.OfferFactory(venue=venue2)
    mock_get_venue_ids_from_queue.return_value = [venue1.id, venue2.id]

    # When
    search.index_venues_in_queue()

    # Then
    assert mock_reindex_offer_ids.mock_calls == [
        mock.call([offer1.id, offer2.id]),
        mock.call([offer3.id]),
        mock.call([offer4.id]),
    ]
    mock_delete_venue_ids_from_queue.assert_called_with([venue1.id, venue2.id])
