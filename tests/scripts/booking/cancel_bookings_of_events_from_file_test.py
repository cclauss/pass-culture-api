from datetime import datetime

import pytest

from pcapi.core.bookings.models import Booking
from pcapi.core.bookings.models import BookingCancellationReasons
import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import create_booking
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_stock
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_event_product
from pcapi.repository import repository
from pcapi.scripts.booking.cancel_bookings_of_events_from_file import _cancel_bookings_of_offers_from_rows


@pytest.mark.usefixtures("db_session")
class CancelBookingsOfEventsFromFileTest:
    def test_cancel_bookings_of_offers_from_rows(self):
        beneficiary = users_factories.UserFactory()
        offerer_to_cancel = create_offerer(name="Librairie les petits parapluies gris", siren="123456789")
        offerer_to_not_cancel = create_offerer(name="L'amicale du club de combat", siren="987654321")
        venue_to_cancel = create_venue(offerer=offerer_to_cancel, siret="12345678912345")
        venue_to_not_cancel = create_venue(offerer=offerer_to_not_cancel, siret="54321987654321")
        offer_to_cancel = create_offer_with_event_product(
            venue=venue_to_cancel, event_name="Dédicace de la Joie des Visiteurs"
        )
        offer_to_not_cancel = create_offer_with_event_product(
            venue=venue_to_not_cancel, event_name="Règle numéro une, ne pas du club de combat"
        )
        stock_to_cancel = create_stock(offer=offer_to_cancel)
        stock_to_not_cancel = create_stock(offer=offer_to_not_cancel)
        self.booking_to_cancel = create_booking(
            stock=stock_to_cancel, user=beneficiary, is_used=True, date_used=datetime.utcnow()
        )
        self.booking_to_not_cancel = create_booking(stock=stock_to_not_cancel, user=beneficiary)
        self.booking_2QLYYA_not_to_cancel = create_booking(stock=stock_to_cancel, user=beneficiary, token="2QLYYA")
        self.booking_BMTUME_not_to_cancel = create_booking(stock=stock_to_cancel, user=beneficiary, token="BMTUME")
        self.booking_LUJ9AM_not_to_cancel = create_booking(stock=stock_to_cancel, user=beneficiary, token="LUJ9AM")
        self.booking_DA8YLU_not_to_cancel = create_booking(stock=stock_to_cancel, user=beneficiary, token="DA8YLU")
        self.booking_Q46YHM_not_to_cancel = create_booking(stock=stock_to_cancel, user=beneficiary, token="Q46YHM")
        repository.save(self.booking_to_cancel, self.booking_to_not_cancel)

        self.csv_rows = [
            [
                "id offre",
                "Structure",
                "Département",
                "Offre",
                "Date de l'évènement",
                "Nb Réservations",
                "A annuler ?",
                "Commentaire",
            ],
            [
                offer_to_cancel.id,
                offer_to_cancel.name,
                "75000",
                offer_to_cancel.name,
                "2020-06-19 18:00:48",
                1,
                "Oui",
                "",
            ],
            [
                offer_to_not_cancel.id,
                offerer_to_not_cancel.name,
                offer_to_not_cancel.name,
                "93000",
                "2020-06-20 18:00:12",
                1,
                "Non",
                "",
            ],
        ]

        _cancel_bookings_of_offers_from_rows(self.csv_rows, BookingCancellationReasons.OFFERER)

        # Then
        saved_booking = Booking.query.get(self.booking_to_cancel.id)
        assert saved_booking.isCancelled is True
        assert saved_booking.cancellationReason == BookingCancellationReasons.OFFERER
        assert saved_booking.cancellationDate is not None
        assert saved_booking.isUsed is False
        assert saved_booking.dateUsed is None

        saved_booking = Booking.query.get(self.booking_to_not_cancel.id)
        assert saved_booking.isCancelled is False
        assert saved_booking.cancellationDate is None

        saved_2QLYYA_booking = Booking.query.get(self.booking_2QLYYA_not_to_cancel.id)
        assert saved_2QLYYA_booking.isCancelled is False
        assert saved_2QLYYA_booking.cancellationDate is None

        saved_BMTUME_booking = Booking.query.get(self.booking_BMTUME_not_to_cancel.id)
        assert saved_BMTUME_booking.isCancelled is False
        assert saved_BMTUME_booking.cancellationDate is None

        saved_LUJ9AM_booking = Booking.query.get(self.booking_LUJ9AM_not_to_cancel.id)
        assert saved_LUJ9AM_booking.isCancelled is False
        assert saved_LUJ9AM_booking.cancellationDate is None

        saved_DA8YLU_booking = Booking.query.get(self.booking_DA8YLU_not_to_cancel.id)
        assert saved_DA8YLU_booking.isCancelled is False
        assert saved_DA8YLU_booking.cancellationDate is None

        saved_Q46YHM_booking = Booking.query.get(self.booking_Q46YHM_not_to_cancel.id)
        assert saved_Q46YHM_booking.isCancelled is False
        assert saved_Q46YHM_booking.cancellationDate is None
