from datetime import datetime
from datetime import timezone
from unittest.mock import patch

from dateutil.tz import tz
import pytest

from pcapi.core import testing
import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.offers.factories as offers_factories
from pcapi.core.offers.factories import VenueFactory
from pcapi.core.testing import assert_num_queries
from pcapi.core.testing import override_features
import pcapi.core.users.factories as users_factories
from pcapi.utils.date import format_into_timezoned_date
from pcapi.utils.date import utc_datetime_to_department_timezone
from pcapi.utils.human_ids import humanize

from tests.conftest import TestClient


class GetAllBookingsTest:
    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.core.bookings.repository.find_by_pro_user_id")
    def test_call_repository_with_user_and_page(self, find_by_pro_user_id, app):
        user = users_factories.UserFactory()
        TestClient(app.test_client()).with_auth(user.email).get("/bookings/pro?page=3")
        find_by_pro_user_id.assert_called_once_with(
            user_id=user.id,
            event_date=None,
            venue_id=None,
            booking_period_beginning_date=None,
            booking_period_ending_date=None,
            page=3,
        )

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.core.bookings.repository.find_by_pro_user_id")
    def test_call_repository_with_page_1(self, find_by_pro_user_id, app):
        user = users_factories.UserFactory()
        TestClient(app.test_client()).with_auth(user.email).get("/bookings/pro")
        find_by_pro_user_id.assert_called_once_with(
            user_id=user.id,
            event_date=None,
            venue_id=None,
            booking_period_beginning_date=None,
            booking_period_ending_date=None,
            page=1,
        )

    @pytest.mark.usefixtures("db_session")
    @patch("pcapi.core.bookings.repository.find_by_pro_user_id")
    def test_call_repository_with_venue_id(self, find_by_pro_user_id, app):
        # Given
        user = users_factories.UserFactory()
        venue = VenueFactory()

        # When
        TestClient(app.test_client()).with_auth(user.email).get(f"/bookings/pro?venueId={humanize(venue.id)}")

        # Then
        find_by_pro_user_id.assert_called_once_with(
            user_id=user.id,
            event_date=None,
            venue_id=venue.id,
            booking_period_beginning_date=None,
            booking_period_ending_date=None,
            page=1,
        )


@pytest.mark.usefixtures("db_session")
class Returns200Test:
    def when_user_is_linked_to_a_valid_offerer(self, app):
        booking = bookings_factories.BookingFactory(
            dateCreated=datetime(2020, 4, 3, 12, 0, 0),
            isUsed=True,
            dateUsed=datetime(2020, 5, 3, 12, 0, 0),
            token="ABCDEF",
            user__email="beneficiary@example.com",
            user__firstName="Hermione",
            user__lastName="Granger",
            user__phoneNumber="0100000000",
        )
        pro_user = users_factories.UserFactory(email="pro@example.com")
        offerer = booking.stock.offer.venue.managingOfferer
        offers_factories.UserOffererFactory(user=pro_user, offerer=offerer)

        client = TestClient(app.test_client()).with_auth(pro_user.email)
        with assert_num_queries(testing.AUTHENTICATION_QUERIES + 3):
            response = client.get("/bookings/pro")

        expected_bookings_recap = [
            {
                "stock": {
                    "type": "thing",
                    "offer_name": booking.stock.offer.name,
                    "offer_identifier": humanize(booking.stock.offer.id),
                },
                "beneficiary": {
                    "email": "beneficiary@example.com",
                    "firstname": "Hermione",
                    "lastname": "Granger",
                    "phonenumber": "0100000000",
                },
                "booking_date": format_into_timezoned_date(
                    booking.dateCreated.astimezone(tz.gettz("Europe/Paris")),
                ),
                "booking_amount": 10.0,
                "booking_token": "ABCDEF",
                "booking_status": "validated",
                "booking_is_duo": False,
                "booking_status_history": [
                    {
                        "status": "booked",
                        "date": format_into_timezoned_date(
                            booking.dateCreated.astimezone(tz.gettz("Europe/Paris")),
                        ),
                    },
                    {
                        "status": "validated",
                        "date": format_into_timezoned_date(
                            booking.dateUsed.astimezone(tz.gettz("Europe/Paris")),
                        ),
                    },
                ],
                "offerer": {
                    "name": offerer.name,
                },
                "venue": {
                    "identifier": humanize(booking.stock.offer.venue.id),
                    "is_virtual": booking.stock.offer.venue.isVirtual,
                    "name": booking.stock.offer.venue.name,
                },
            }
        ]
        assert response.status_code == 200
        assert response.json["bookings_recap"] == expected_bookings_recap
        assert response.json["page"] == 1
        assert response.json["pages"] == 1
        assert response.json["total"] == 1

    def when_requested_event_date_is_iso_format(self, app):
        requested_date = datetime(2020, 8, 12, 20, 00)
        requested_date_iso_format = "2020-08-12T00:00:00Z"
        stock = offers_factories.EventStockFactory(beginningDatetime=requested_date)
        booking = bookings_factories.BookingFactory(stock=stock, token="AAAAAA")
        bookings_factories.BookingFactory(stock=offers_factories.EventStockFactory(), token="BBBBBB")
        pro_user = users_factories.UserFactory(email="pro@example.com")
        offerer = stock.offer.venue.managingOfferer
        offers_factories.UserOffererFactory(user=pro_user, offerer=offerer)

        client = TestClient(app.test_client()).with_auth(pro_user.email)
        with assert_num_queries(testing.AUTHENTICATION_QUERIES + 3):
            response = client.get("/bookings/pro?eventDate=%s" % requested_date_iso_format)

        assert response.status_code == 200
        assert len(response.json["bookings_recap"]) == 1
        assert response.json["bookings_recap"][0]["booking_token"] == booking.token
        assert response.json["page"] == 1
        assert response.json["pages"] == 1
        assert response.json["total"] == 1

    def when_requested_booking_period_dates_are_iso_format(self, app):
        booking_date = datetime(2020, 8, 12, 20, 00, tzinfo=timezone.utc)
        booking_period_beginning_date_iso = "2020-08-10T00:00:00Z"
        booking_period_ending_date_iso = "2020-08-12T00:00:00Z"
        booking = bookings_factories.BookingFactory(dateCreated=booking_date, token="AAAAAA")
        bookings_factories.BookingFactory(token="BBBBBB")
        pro_user = users_factories.UserFactory(email="pro@example.com")
        offerer = booking.stock.offer.venue.managingOfferer
        offers_factories.UserOffererFactory(user=pro_user, offerer=offerer)

        client = TestClient(app.test_client()).with_auth(pro_user.email)
        with assert_num_queries(testing.AUTHENTICATION_QUERIES + 3):
            response = client.get(
                "/bookings/pro?bookingPeriodBeginningDate=%s&bookingPeriodEndingDate=%s"
                % (booking_period_beginning_date_iso, booking_period_ending_date_iso)
            )

        assert response.status_code == 200
        assert len(response.json["bookings_recap"]) == 1
        assert response.json["bookings_recap"][0]["booking_date"] == datetime.isoformat(
            utc_datetime_to_department_timezone(booking.dateCreated, booking.stock.offer.venue.departementCode)
        )
        assert response.json["page"] == 1
        assert response.json["pages"] == 1
        assert response.json["total"] == 1


@pytest.mark.usefixtures("db_session")
class Returns400Test:
    def when_page_number_is_not_a_number(self, app):
        user = users_factories.UserFactory()

        client = TestClient(app.test_client()).with_auth(user.email)
        response = client.get("/bookings/pro?page=not-a-number")

        assert response.status_code == 400
        assert response.json["global"] == ["L'argument 'page' not-a-number n'est pas valide"]


@pytest.mark.usefixtures("db_session")
class Returns401Test:
    def when_user_is_admin(self, app):
        user = users_factories.UserFactory(isAdmin=True)

        client = TestClient(app.test_client()).with_auth(user.email)
        response = client.get("/bookings/pro")

        assert response.status_code == 401
        assert response.json == {
            "global": ["Le statut d'administrateur ne permet pas d'accéder au suivi des réservations"]
        }

    @override_features(DISABLE_BOOKINGS_RECAP_FOR_SOME_PROS=True)
    def when_user_is_blacklisted(self, app):
        user = users_factories.UserFactory(offerers=[offers_factories.OffererFactory(siren="334473352")])

        client = TestClient(app.test_client()).with_auth(user.email)
        response = client.get("/bookings/pro")

        assert response.status_code == 401
        assert response.json == {
            "global": ["Le statut d'administrateur ne permet pas d'accéder au suivi des réservations"]
        }
