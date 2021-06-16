from datetime import MINYEAR
from datetime import datetime
from datetime import timedelta

import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.offers.factories as offers_factories
import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import create_beneficiary_import
from pcapi.model_creators.generic_creators import create_user
from pcapi.models import BeneficiaryImportSources
from pcapi.models import ImportStatus
from pcapi.repository import repository
from pcapi.repository.user_queries import find_by_civility
from pcapi.repository.user_queries import find_most_recent_beneficiary_creation_date_for_source
from pcapi.repository.user_queries import find_pro_users_by_email_provider
from pcapi.repository.user_queries import get_all_users_wallet_balances


class GetAllUsersWalletBalancesTest:
    def test_users_are_sorted_by_user_id(self):
        # given
        user1 = users_factories.UserFactory()
        user2 = users_factories.UserFactory()

        # when
        balances = get_all_users_wallet_balances()

        # then
        assert len(balances) == 2
        assert [b.user_id for b in balances] == [user1.id, user2.id]

    def test_users_with_no_deposits_are_ignored(self):
        # given
        user1 = users_factories.UserFactory()
        user2 = users_factories.UserFactory()
        repository.delete(user2.deposit)

        # when
        balances = get_all_users_wallet_balances()

        # then
        assert len(balances) == 1
        assert balances[0].user_id == user1.id

    def test_returns_both_current_and_real_balances(self):
        # given
        offer = offers_factories.OfferFactory()
        stock1 = offers_factories.StockFactory(offer=offer, price=20)
        stock2 = offers_factories.StockFactory(offer=offer, price=30)
        stock3 = offers_factories.StockFactory(offer=offer, price=40)
        user = users_factories.UserFactory(deposit__version=1)

        bookings_factories.BookingFactory(user=user, stock=stock1)
        bookings_factories.BookingFactory(user=user, stock=stock2, isCancelled=True)
        bookings_factories.BookingFactory(user=user, stock=stock3, isUsed=True, quantity=2)

        # when
        balances = get_all_users_wallet_balances()

        # then
        balance = balances[0]
        assert balance.current_balance == 500 - (20 + 40 * 2)
        assert balance.real_balance == 500 - (40 * 2)


class FindProUsersByEmailProviderTest:
    def test_returns_pro_users_with_matching_email_provider(self):
        pro_user_with_matching_email = users_factories.UserFactory(
            email="pro_user@suspect.com", isBeneficiary=False, isActive=True
        )
        offerer = offers_factories.OffererFactory()
        offers_factories.UserOffererFactory(user=pro_user_with_matching_email, offerer=offerer)

        pro_user_with_not_matching_email = users_factories.UserFactory(
            email="pro_user@example.com", isBeneficiary=False, isActive=True
        )
        offerer2 = offers_factories.OffererFactory()
        offers_factories.UserOffererFactory(user=pro_user_with_not_matching_email, offerer=offerer2)

        users = find_pro_users_by_email_provider("suspect.com")

        assert len(users) == 1
        assert users[0] == pro_user_with_matching_email

    def test_returns_only_pro_users_with_matching_email_provider(self):
        pro_user_with_matching_email = users_factories.UserFactory(
            email="pro_user_with_matching_email@suspect.com", isBeneficiary=False, isActive=True
        )
        offerer = offers_factories.OffererFactory()
        offers_factories.UserOffererFactory(user=pro_user_with_matching_email, offerer=offerer)

        users_factories.UserFactory(email="not_pro_with_matching_email@suspect.com", isBeneficiary=False, isActive=True)

        users = find_pro_users_by_email_provider("suspect.com")

        assert len(users) == 1
        assert users[0] == pro_user_with_matching_email


class FindByCivilityTest:
    def test_returns_users_with_matching_criteria_ignoring_case(self, app):
        # given
        user1 = create_user(
            date_of_birth=datetime(2000, 5, 1), email="john@example.com", first_name="john", last_name="DOe"
        )
        user2 = create_user(
            date_of_birth=datetime(2000, 3, 20), email="jane@example.com", first_name="jaNE", last_name="DOe"
        )
        repository.save(user1, user2)

        # when
        users = find_by_civility("john", "doe", datetime(2000, 5, 1))

        # then
        assert len(users) == 1
        assert users[0].email == "john@example.com"

    def test_returns_users_with_matching_criteria_ignoring_dash(self, app):
        # given
        user2 = create_user(
            date_of_birth=datetime(2000, 3, 20), email="jane@example.com", first_name="jaNE", last_name="DOe"
        )
        user1 = create_user(
            date_of_birth=datetime(2000, 5, 1), email="john.b@example.com", first_name="john-bob", last_name="doe"
        )
        repository.save(user1, user2)

        # when
        users = find_by_civility("johnbob", "doe", datetime(2000, 5, 1))

        # then
        assert len(users) == 1
        assert users[0].email == "john.b@example.com"

    def test_returns_users_with_matching_criteria_ignoring_spaces(self, app):
        # given
        user2 = create_user(
            date_of_birth=datetime(2000, 3, 20), email="jane@example.com", first_name="jaNE", last_name="DOe"
        )
        user1 = create_user(
            date_of_birth=datetime(2000, 5, 1), email="john.b@example.com", first_name="john bob", last_name="doe"
        )
        repository.save(user1, user2)

        # when
        users = find_by_civility("johnbob", "doe", datetime(2000, 5, 1))

        # then
        assert len(users) == 1
        assert users[0].email == "john.b@example.com"

    def test_returns_users_with_matching_criteria_ignoring_accents(self, app):
        # given
        user2 = create_user(
            date_of_birth=datetime(2000, 3, 20), email="jane@example.com", first_name="jaNE", last_name="DOe"
        )
        user1 = create_user(
            date_of_birth=datetime(2000, 5, 1), email="john.b@example.com", first_name="john bob", last_name="doe"
        )
        repository.save(user1, user2)

        # when
        users = find_by_civility("jöhn bób", "doe", datetime(2000, 5, 1))

        # then
        assert len(users) == 1
        assert users[0].email == "john.b@example.com"

    def test_returns_nothing_if_one_criteria_does_not_match(self, app):
        # given
        user = create_user(date_of_birth=datetime(2000, 5, 1), first_name="Jean", last_name="DOe")
        repository.save(user)

        # when
        users = find_by_civility("john", "doe", datetime(2000, 5, 1))

        # then
        assert not users

    def test_returns_users_with_matching_criteria_first_and_last_names_and_birthdate_and_invalid_email(self, app):
        # given
        user1 = create_user(
            date_of_birth=datetime(2000, 5, 1), email="john@example.com", first_name="john", last_name="DOe"
        )
        user2 = create_user(
            date_of_birth=datetime(2000, 3, 20), email="jane@example.com", first_name="jaNE", last_name="DOe"
        )
        repository.save(user1, user2)

        # when
        users = find_by_civility("john", "doe", datetime(2000, 5, 1))

        # then
        assert len(users) == 1
        assert users[0].email == "john@example.com"


class FindMostRecentBeneficiaryCreationDateByProcedureIdTest:
    def test_returns_created_at_date_of_most_recent_beneficiary_import_with_created_status_for_one_procedure(self, app):
        # given
        source_id = 1
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)
        three_days_ago = now - timedelta(days=3)

        user1 = create_user(date_created=yesterday, email="user1@example.com")
        user2 = create_user(date_created=two_days_ago, email="user2@example.com")
        user3 = create_user(date_created=three_days_ago, email="user3@example.com")
        beneficiary_import = [
            create_beneficiary_import(
                user=user2, status=ImportStatus.ERROR, date=two_days_ago, application_id=1, source_id=source_id
            ),
            create_beneficiary_import(
                user=user3, status=ImportStatus.CREATED, date=three_days_ago, application_id=3, source_id=source_id
            ),
        ]

        repository.save(user1, *beneficiary_import)

        # when
        most_recent_creation_date = find_most_recent_beneficiary_creation_date_for_source(
            BeneficiaryImportSources.demarches_simplifiees, source_id
        )

        # then
        assert most_recent_creation_date == three_days_ago

    def test_returns_min_year_if_no_beneficiary_import_exist_for_given_source_id(self, app):
        # given
        old_source_id = 1
        new_source_id = 2
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        user = create_user(date_created=yesterday, email="user@example.com")
        beneficiary_import = create_beneficiary_import(
            user=user, status=ImportStatus.CREATED, date=yesterday, application_id=3, source_id=old_source_id
        )

        repository.save(beneficiary_import)

        # when
        most_recent_creation_date = find_most_recent_beneficiary_creation_date_for_source(
            BeneficiaryImportSources.demarches_simplifiees, new_source_id
        )

        # then
        assert most_recent_creation_date == datetime(MINYEAR, 1, 1)

    def test_returns_min_year_if_no_beneficiary_import_exist(self, app):
        # given
        yesterday = datetime.utcnow() - timedelta(days=1)
        user = create_user(date_created=yesterday)
        repository.save(user)

        # when
        most_recent_creation_date = find_most_recent_beneficiary_creation_date_for_source(
            BeneficiaryImportSources.demarches_simplifiees, 1
        )

        # then
        assert most_recent_creation_date == datetime(MINYEAR, 1, 1)
