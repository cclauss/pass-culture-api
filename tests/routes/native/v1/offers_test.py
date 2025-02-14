from datetime import datetime
from datetime import timedelta

from freezegun import freeze_time
import pytest

from pcapi.core.bookings.factories import BookingFactory
import pcapi.core.mails.testing as mails_testing
from pcapi.core.offers.factories import EventStockFactory
from pcapi.core.offers.factories import MediationFactory
from pcapi.core.offers.factories import OfferFactory
from pcapi.core.offers.factories import ProductFactory
from pcapi.core.offers.factories import StockWithActivationCodesFactory
from pcapi.core.offers.factories import ThingStockFactory
from pcapi.core.testing import assert_num_queries
from pcapi.models.db import db
from pcapi.models.offer_type import EventType
from pcapi.models.offer_type import ThingType
import pcapi.notifications.push.testing as notifications_testing

from tests.conftest import TestClient

from .utils import create_user_and_test_client


pytestmark = pytest.mark.usefixtures("db_session")


class OffersTest:
    @freeze_time("2020-01-01")
    def test_get_event_offer(self, app):
        offer_type = EventType.CINEMA
        extra_data = {
            "author": "mandibule",
            "isbn": "3838",
            "musicSubType": "502",
            "musicType": "501",
            "performer": "interprète",
            "showSubType": "101",
            "showType": "100",
            "stageDirector": "metteur en scène",
            "speaker": "intervenant",
            "visa": "vasi",
        }
        offer = OfferFactory(
            type=str(offer_type),
            isDuo=True,
            description="desk cryption",
            name="l'offre du siècle",
            withdrawalDetails="modalité de retrait",
            extraData=extra_data,
            durationMinutes=33,
            visualDisabilityCompliant=True,
            externalTicketOfficeUrl="https://url.com",
            venue__name="il est venu le temps des names",
        )
        MediationFactory(id=111, offer=offer, thumbCount=1, credit="street credit")

        bookableStock = EventStockFactory(offer=offer, price=12.34, quantity=2)
        expiredStock = EventStockFactory(
            offer=offer, price=45.68, beginningDatetime=datetime.utcnow() - timedelta(days=1)
        )
        exhaustedStock = EventStockFactory(offer=offer, price=12.34, quantity=1)

        BookingFactory(stock=bookableStock)
        BookingFactory(stock=exhaustedStock)

        offer_id = offer.id
        with assert_num_queries(1):
            response = TestClient(app.test_client()).get(f"/native/v1/offer/{offer_id}")

        assert response.status_code == 200
        response_content = response.json
        response_content["stocks"].sort(key=lambda stock: stock["id"])
        assert response.json == {
            "id": offer.id,
            "accessibility": {
                "audioDisability": False,
                "mentalDisability": False,
                "motorDisability": False,
                "visualDisability": True,
            },
            "stocks": [
                {
                    "id": bookableStock.id,
                    "price": 1234,
                    "beginningDatetime": "2020-01-06T00:00:00Z",
                    "bookingLimitDatetime": "2020-01-05T23:00:00Z",
                    "cancellationLimitDatetime": "2020-01-03T00:00:00Z",
                    "isBookable": True,
                    "isSoldOut": False,
                    "isExpired": False,
                    "activationCode": None,
                },
                {
                    "id": expiredStock.id,
                    "price": 4568,
                    "beginningDatetime": "2019-12-31T00:00:00Z",
                    "bookingLimitDatetime": "2019-12-30T23:00:00Z",
                    "cancellationLimitDatetime": "2020-01-01T00:00:00Z",
                    "isBookable": False,
                    "isSoldOut": True,
                    "isExpired": True,
                    "activationCode": None,
                },
                {
                    "id": exhaustedStock.id,
                    "price": 1234,
                    "beginningDatetime": "2020-01-06T00:00:00Z",
                    "bookingLimitDatetime": "2020-01-05T23:00:00Z",
                    "cancellationLimitDatetime": "2020-01-03T00:00:00Z",
                    "isBookable": False,
                    "isSoldOut": True,
                    "isExpired": False,
                    "activationCode": None,
                },
            ],
            "category": {"categoryType": "Event", "label": "Cinéma", "name": "CINEMA"},
            "description": "desk cryption",
            "externalTicketOfficeUrl": "https://url.com",
            "expenseDomains": ["all"],
            "extraData": {
                "author": "mandibule",
                "isbn": "3838",
                "durationMinutes": 33,
                "musicSubType": "Acid Jazz",
                "musicType": "Jazz",
                "performer": "interprète",
                "showSubType": "Carnaval",
                "showType": "Arts de la rue",
                "speaker": "intervenant",
                "stageDirector": "metteur en scène",
                "visa": "vasi",
            },
            "image": {"url": "http://localhost/storage/thumbs/mediations/N4", "credit": "street credit"},
            "isActive": True,
            "isExpired": False,
            "isSoldOut": False,
            "isDuo": True,
            "isDigital": False,
            "isReleased": True,
            "name": "l'offre du siècle",
            "venue": {
                "id": offer.venue.id,
                "address": "1 boulevard Poissonnière",
                "city": "Paris",
                "coordinates": {
                    "latitude": 48.87004,
                    "longitude": 2.3785,
                },
                "name": "il est venu le temps des names",
                "offerer": {"name": offer.venue.managingOfferer.name},
                "postalCode": "75000",
                "publicName": "il est venu le temps des names",
            },
            "withdrawalDetails": "modalité de retrait",
        }

    def test_get_thing_offer(self, app):
        product = ProductFactory(thumbCount=1)
        offer_type = ThingType.MUSEES_PATRIMOINE_ABO
        offer = OfferFactory(type=str(offer_type), product=product)
        ThingStockFactory(offer=offer, price=12.34)

        offer_id = offer.id
        with assert_num_queries(1):
            response = TestClient(app.test_client()).get(f"/native/v1/offer/{offer_id}")

        assert response.status_code == 200
        assert not response.json["stocks"][0]["beginningDatetime"]
        assert response.json["stocks"][0]["price"] == 1234
        assert response.json["category"] == {
            "categoryType": "Thing",
            "label": "Musée, arts visuels et patrimoine",
            "name": "VISITE",
        }
        assert not response.json["isExpired"]

    def test_get_digital_offer_without_activation_code_expiration_date(self, app):
        stock = StockWithActivationCodesFactory()
        offer_id = stock.offer.id
        with assert_num_queries(1):
            response = TestClient(app.test_client()).get(f"/native/v1/offer/{offer_id}")

        assert response.status_code == 200
        assert response.json["stocks"][0]["activationCode"] is None

    def test_get_digital_offer_with_activation_code_expiration_date(self, app):
        stock = StockWithActivationCodesFactory()
        for activation_code in stock.activationCodes:
            activation_code.expirationDate = datetime(2050, 1, 1)
        db.session.commit()

        offer_id = stock.offer.id
        with assert_num_queries(1):
            response = TestClient(app.test_client()).get(f"/native/v1/offer/{offer_id}")

        assert response.status_code == 200
        assert response.json["stocks"][0]["activationCode"] == {"expirationDate": "2050-01-01T00:00:00Z"}

    @freeze_time("2020-01-01")
    def test_get_expired_offer(self, app):
        stock = EventStockFactory(beginningDatetime=datetime.utcnow() - timedelta(days=1))

        offer_id = stock.offer.id
        with assert_num_queries(1):
            response = TestClient(app.test_client()).get(f"/native/v1/offer/{offer_id}")

        assert response.json["isExpired"]

    def test_get_offer_not_found(self, app):
        response = TestClient(app.test_client()).get("/native/v1/offer/1")

        assert response.status_code == 404


class SendOfferWebAppLinkTest:
    def test_send_offer_webapp_link_by_email(self, app):
        offer_id = OfferFactory().id
        user, test_client = create_user_and_test_client(app)

        # expected queries:
        #   * get User
        #   * find Offer
        #   * save email to DB (testing backend)
        #   * release savepoint after saving email
        with assert_num_queries(4):
            response = test_client.post(f"/native/v1/send_offer_webapp_link_by_email/{offer_id}")
            assert response.status_code == 204

        assert len(mails_testing.outbox) == 1

        mail = mails_testing.outbox[0]
        assert mail.sent_data["To"] == user.email

    def test_send_offer_webapp_link_by_email_not_found(self, app):
        _, test_client = create_user_and_test_client(app)

        # expected queries:
        #   * get User
        #   * try to find Offer
        with assert_num_queries(2):
            response = test_client.post("/native/v1/send_offer_webapp_link_by_email/98765432123456789")
            assert response.status_code == 404
        assert not mails_testing.outbox


class SendOfferLinkNotificationTest:
    def test_send_offer_link_notification(self, app):
        """
        Test that a push notification to the user is send with a link to the
        offer.
        """
        # offer.id must be used before the assert_num_queries context manager
        # because it triggers a SQL query.
        offer = OfferFactory()
        offer_id = offer.id

        user, test_client = create_user_and_test_client(app)

        # expected queries:
        #   * get user
        #   * get offer
        with assert_num_queries(2):
            response = test_client.post(f"/native/v1/send_offer_link_by_push/{offer_id}")
            assert response.status_code == 204

        assert len(notifications_testing.requests) == 1

        notification = notifications_testing.requests[0]
        assert notification["user_ids"] == [user.id]

        assert offer.name in notification["message"]["title"]
        assert "deeplink" in notification

    def test_send_offer_link_notification_not_found(self, app):
        """Test that no push notification is sent when offer is not found"""
        _, test_client = create_user_and_test_client(app)

        # expected queries:
        #   * get user
        #   * search for offer
        with assert_num_queries(2):
            response = test_client.post("/native/v1/send_offer_link_by_push/9999999999")
            assert response.status_code == 404

        assert len(notifications_testing.requests) == 0
