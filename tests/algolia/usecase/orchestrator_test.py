from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

from algoliasearch.exceptions import AlgoliaException
import pytest

from pcapi.algolia.usecase.orchestrator import delete_expired_offers
from pcapi.algolia.usecase.orchestrator import process_eligible_offers
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_stock
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_thing_product
from pcapi.repository import repository


TOMORROW = datetime.now() + timedelta(days=1)


class ProcessEligibleOffersTest:
    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.algolia.usecase.orchestrator.add_offer_ids_in_error")
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.build_object", return_value={"fake": "test"})
    def test_should_add_objects_when_objects_are_eligible_and_not_already_indexed(
        self,
        mock_build_object,
        mock_check_offer_exists,
        mock_add_objects,
        mock_delete_objects,
        mock_add_to_indexed_offers,
        mock_delete_indexed_offers,
        mock_add_offer_ids_in_error,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=10)
        offer2 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=10)
        offer3 = create_offer_with_thing_product(venue=venue, is_active=False)
        stock3 = create_stock(booking_limit_datetime=TOMORROW, offer=offer3, quantity=10)
        repository.save(stock1, stock2, stock3)
        mock_check_offer_exists.side_effect = [False, False, False]

        # When
        process_eligible_offers(client=client, offer_ids=[offer1.id, offer2.id])

        # Then
        assert mock_build_object.call_count == 2
        mock_add_objects.assert_called_once_with(objects=[{"fake": "test"}, {"fake": "test"}])
        assert mock_add_to_indexed_offers.call_count == 2
        assert mock_add_to_indexed_offers.call_args_list == [
            call(
                pipeline=mock_pipeline,
                offer_id=offer1.id,
            ),
            call(
                pipeline=mock_pipeline,
                offer_id=offer2.id,
            ),
        ]
        mock_delete_indexed_offers.assert_not_called()
        mock_delete_objects.assert_not_called()
        mock_pipeline.execute.assert_called_once()
        mock_pipeline.reset.assert_called_once()
        mock_add_offer_ids_in_error.assert_not_called()

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.algolia.usecase.orchestrator.add_offer_ids_in_error")
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @patch("pcapi.algolia.usecase.orchestrator.build_object", return_value={"fake": "test"})
    def test_should_delete_objects_when_objects_are_not_eligible_and_were_already_indexed(
        self,
        mock_build_object,
        mock_add_objects,
        mock_delete_objects,
        mock_add_to_indexed_offers,
        mock_check_offer_exists,
        mock_delete_indexed_offers,
        mock_add_offer_ids_in_error,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=0)
        offer2 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=0)
        repository.save(stock1, stock2)
        mock_check_offer_exists.side_effect = [True, True]

        # When
        process_eligible_offers(client=client, offer_ids=[offer1.id, offer2.id])

        # Then
        mock_build_object.assert_not_called()
        mock_add_objects.assert_not_called()
        mock_add_to_indexed_offers.assert_not_called()
        mock_delete_objects.assert_called_once()
        assert mock_delete_objects.call_args_list == [call(object_ids=[offer1.id, offer2.id])]
        mock_delete_indexed_offers.assert_called_once()
        assert mock_delete_indexed_offers.call_args_list == [call(client=client, offer_ids=[offer1.id, offer2.id])]
        mock_pipeline.execute.assert_not_called()
        mock_pipeline.reset.assert_not_called()
        mock_add_offer_ids_in_error.assert_not_called()

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @patch("pcapi.algolia.usecase.orchestrator.build_object", return_value={"fake": "test"})
    def test_should_not_delete_objects_when_objects_are_not_eligible_and_were_not_indexed(
        self,
        mock_build_object,
        mock_add_objects,
        mock_delete_objects,
        mock_add_to_indexed_offers,
        mock_check_offer_exists,
        mock_delete_indexed_offers,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=0)
        offer2 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=0)
        repository.save(stock1, stock2)
        mock_check_offer_exists.side_effect = [False, False]

        # When
        process_eligible_offers(client=client, offer_ids=[offer1.id, offer2.id])

        # Then
        mock_build_object.assert_not_called()
        mock_add_objects.assert_not_called()
        mock_add_to_indexed_offers.assert_not_called()
        mock_delete_objects.assert_not_called()
        mock_delete_indexed_offers.assert_not_called()
        mock_pipeline.execute.assert_not_called()
        mock_pipeline.reset.assert_not_called()

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.algolia.usecase.orchestrator.add_offer_ids_in_error")
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @patch("pcapi.algolia.usecase.orchestrator.build_object", return_value={"fake": "test"})
    def test_should_add_offer_ids_in_error_when_deleting_objects_failed(
        self,
        mock_build_object,
        mock_add_objects,
        mock_delete_objects,
        mock_add_to_indexed_offers,
        mock_check_offer_exists,
        mock_delete_indexed_offers,
        mock_add_offer_ids_in_error,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=0)
        offer2 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=0)
        repository.save(stock1, stock2)
        mock_check_offer_exists.side_effect = [True, True]
        mock_delete_objects.side_effect = [AlgoliaException]

        # When
        process_eligible_offers(client=client, offer_ids=[offer1.id, offer2.id])

        # Then
        mock_build_object.assert_not_called()
        mock_add_objects.assert_not_called()
        mock_add_to_indexed_offers.assert_not_called()
        mock_delete_objects.assert_called_once()
        assert mock_delete_objects.call_args_list == [call(object_ids=[offer1.id, offer2.id])]
        mock_delete_indexed_offers.assert_not_called()
        mock_add_offer_ids_in_error.assert_called_once_with(client=client, offer_ids=[offer1.id, offer2.id])
        mock_pipeline.execute.assert_not_called()
        mock_pipeline.reset.assert_not_called()

    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.build_object")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @pytest.mark.usefixtures("db_session")
    def test_should_delete_offers_that_are_already_indexed(
        self,
        mock_add_objects,
        mock_build_object,
        mock_delete_objects,
        mock_check_offer_exists,
        mock_add_to_indexed_offers,
        mock_delete_indexed_offers,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(thing_name="super offre 1", venue=venue, is_active=False)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=1)
        offer2 = create_offer_with_thing_product(thing_name="super offre 2", venue=venue, is_active=False)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=1)
        offer3 = create_offer_with_thing_product(thing_name="super offre 3", venue=venue, is_active=False)
        stock3 = create_stock(booking_limit_datetime=TOMORROW, offer=offer3, quantity=1)
        repository.save(stock1, stock2, stock3)
        offer_ids = [offer1.id, offer2.id, offer3.id]
        mock_check_offer_exists.side_effect = [True, True, True]

        # When
        process_eligible_offers(client=client, offer_ids=offer_ids)

        # Then
        assert mock_check_offer_exists.call_count == 3
        assert mock_build_object.call_count == 0
        assert mock_add_objects.call_count == 0
        assert mock_add_to_indexed_offers.call_count == 0
        assert mock_delete_objects.call_count == 1
        assert mock_delete_objects.call_args_list == [call(object_ids=[offer1.id, offer2.id, offer3.id])]
        assert mock_delete_indexed_offers.call_count == 1
        assert mock_delete_indexed_offers.call_args_list == [
            call(client=client, offer_ids=[offer1.id, offer2.id, offer3.id])
        ]
        assert mock_pipeline.execute.call_count == 0
        assert mock_pipeline.reset.call_count == 0

    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @pytest.mark.usefixtures("db_session")
    def test_should_not_delete_offers_that_are_not_already_indexed(
        self, mock_delete_objects, mock_check_offer_exists, mock_delete_indexed_offers, app
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(thing_name="super offre 1", venue=venue, is_active=False)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=1)
        offer2 = create_offer_with_thing_product(thing_name="super offre 2", venue=venue, is_active=False)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=1)
        repository.save(stock1, stock2)
        offer_ids = [offer1.id, offer2.id]
        mock_check_offer_exists.side_effect = [False, False]

        # When
        process_eligible_offers(client=client, offer_ids=offer_ids)

        # Then
        assert mock_check_offer_exists.call_count == 2
        assert mock_delete_objects.call_count == 0
        assert mock_delete_indexed_offers.call_count == 0

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.algolia.usecase.orchestrator.add_offer_ids_in_error")
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.add_to_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    @patch("pcapi.algolia.usecase.orchestrator.add_objects")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.build_object", return_value={"fake": "test"})
    def test_should_add_offer_ids_in_error_when_adding_objects_failed(
        self,
        mock_build_object,
        mock_check_offer_exists,
        mock_add_objects,
        mock_delete_objects,
        mock_add_to_indexed_offers,
        mock_delete_indexed_offers,
        mock_add_offer_ids_in_error,
        app,
    ):
        # Given
        client = MagicMock()
        client.pipeline = MagicMock()
        client.pipeline.return_value = MagicMock()
        mock_pipeline = client.pipeline()
        mock_pipeline.execute = MagicMock()
        mock_pipeline.reset = MagicMock()
        offerer = create_offerer(is_active=True, validation_token=None)
        venue = create_venue(offerer=offerer, validation_token=None)
        offer1 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock1 = create_stock(booking_limit_datetime=TOMORROW, offer=offer1, quantity=10)
        offer2 = create_offer_with_thing_product(venue=venue, is_active=True)
        stock2 = create_stock(booking_limit_datetime=TOMORROW, offer=offer2, quantity=10)
        repository.save(stock1, stock2)
        mock_check_offer_exists.side_effect = [False, False]
        mock_add_objects.side_effect = [AlgoliaException]

        # When
        process_eligible_offers(client=client, offer_ids=[offer1.id, offer2.id])

        # Then
        assert mock_build_object.call_count == 2
        mock_add_objects.assert_called_once_with(objects=[{"fake": "test"}, {"fake": "test"}])
        assert mock_add_to_indexed_offers.call_count == 2
        assert mock_add_to_indexed_offers.call_args_list == [
            call(
                pipeline=mock_pipeline,
                offer_id=offer1.id,
            ),
            call(
                pipeline=mock_pipeline,
                offer_id=offer2.id,
            ),
        ]
        mock_delete_indexed_offers.assert_not_called()
        mock_delete_objects.assert_not_called()
        mock_pipeline.execute.assert_not_called()
        mock_pipeline.reset.assert_called_once()
        assert mock_add_offer_ids_in_error.call_args_list == [call(client=client, offer_ids=[offer1.id, offer2.id])]


class DeleteExpiredOffersTest:
    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    def test_should_delete_expired_offers_from_algolia_when_at_least_one_offer_id_and_offers_were_indexed(
        self, mock_delete_objects, mock_check_offer_exists, mock_delete_indexed_offers, app
    ):
        # Given
        client = MagicMock()
        mock_check_offer_exists.side_effect = [True, True, True]

        # When
        delete_expired_offers(client=client, offer_ids=[1, 2, 3])

        # Then
        assert mock_delete_objects.call_count == 1
        assert mock_delete_objects.call_args_list == [call(object_ids=[1, 2, 3])]
        assert mock_delete_indexed_offers.call_count == 1
        assert mock_delete_indexed_offers.call_args_list == [call(client=client, offer_ids=[1, 2, 3])]

    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    def test_should_not_delete_expired_offers_from_algolia_when_no_offer_id(
        self, mock_delete_objects, mock_delete_indexed_offers, app
    ):
        # Given
        client = MagicMock()

        # When
        delete_expired_offers(client=client, offer_ids=[])

        # Then
        assert mock_delete_objects.call_count == 0
        assert mock_delete_indexed_offers.call_count == 0

    @patch("pcapi.algolia.usecase.orchestrator.delete_indexed_offers")
    @patch("pcapi.algolia.usecase.orchestrator.check_offer_exists")
    @patch("pcapi.algolia.usecase.orchestrator.delete_objects")
    def test_should_not_delete_expired_offers_from_algolia_when_at_least_one_offer_id_but_offers_were_not_indexed(
        self, mock_delete_objects, mock_check_offer_exists, mock_delete_indexed_offers, app
    ):
        # Given
        client = MagicMock()
        mock_check_offer_exists.side_effect = [False, False, False]

        # When
        delete_expired_offers(client=client, offer_ids=[])

        # Then
        assert mock_delete_objects.call_count == 0
        assert mock_delete_indexed_offers.call_count == 0
