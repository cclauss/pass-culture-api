import datetime
from unittest.mock import patch

import pytest

import pcapi.core.fraud.api as fraud_api
import pcapi.core.fraud.factories as fraud_factories
import pcapi.core.fraud.models as fraud_models
import pcapi.core.users.factories as users_factories
import pcapi.core.users.models as users_models
from pcapi.flask_app import db


pytestmark = pytest.mark.usefixtures("db_session")


class JouveFraudCheckTest:
    application_id = 35
    user_email = "tour.de.passpass@example.com"

    JOUVE_CONTENT = {
        "activity": "Etudiant",
        "address": "",
        "birthDate": "06/08/2002",
        "birthDateTxt": "06/08/2002",
        "birthLocation": "STRASBOURG I67)",
        "birthLocationCtrl": "OK",
        "bodyBirthDate": "06 06 2002",
        "bodyBirthDateCtrl": "OK",
        "bodyBirthDateLevel": "100",
        "bodyFirstnameCtrl": "",
        "bodyFirstnameLevel": "100",
        "bodyName": "DUPO",
        "bodyNameCtrl": "OK",
        "bodyNameLevel": "100",
        "bodyPieceNumber": "140767100016",
        "bodyPieceNumberCtrl": "OK",
        "bodyPieceNumberLevel": "100",
        "city": "",
        "creatorCtrl": "NOT_APPLICABLE",
        "docFileID": 535,
        "docObjectID": 535,
        "email": user_email,
        "firstName": "CHRISTOPHE",
        "gender": "M",
        "id": application_id,
        "initial": "",
        "initialNumberCtrl": "",
        "initialSizeCtrl": "",
        "lastName": "DUPO",
        "phoneNumber": "",
        "postalCode": "",
        "posteCode": "678083",
        "posteCodeCtrl": "OK",
        "registrationDate": "10/06/2021 21:00",
        "serviceCode": "1",
        "serviceCodeCtrl": "",
    }

    @patch("pcapi.connectors.beneficiaries.jouve_backend._get_raw_content")
    @pytest.mark.parametrize("body_name_level", [None, "", "100"])
    def test_jouve_update(self, _get_raw_content, client, body_name_level):
        user = users_factories.UserFactory(
            hasCompletedIdCheck=True,
            isBeneficiary=False,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
            dateOfBirth=datetime.datetime(2002, 6, 8),
            email=self.user_email,
        )
        _get_raw_content.return_value = self.JOUVE_CONTENT | {"bodyNameLevel": body_name_level}

        response = client.post("/beneficiaries/application_update", json={"id": self.application_id})
        assert response.status_code == 200

        fraud_check = fraud_models.BeneficiaryFraudCheck.query.filter_by(
            user=user, type=fraud_models.FraudCheckType.JOUVE
        ).first()
        fraud_result = fraud_models.BeneficiaryFraudResult.query.filter_by(user=user).first()
        jouve_fraud_content = fraud_models.JouveContent(**fraud_check.resultContent)

        assert jouve_fraud_content.bodyPieceNumber == "140767100016"
        assert fraud_check.dateCreated
        assert fraud_check.thirdPartyId == "35"
        assert fraud_result.status == fraud_models.FraudStatus.OK

        db.session.refresh(user)
        assert user.isBeneficiary

    @patch("pcapi.connectors.beneficiaries.jouve_backend._get_raw_content")
    def test_jouve_update_duplicate_user(self, _get_raw_content, client):
        existing_user = users_factories.UserFactory(
            firstName="Christophe",
            lastName="Dupo",
            isBeneficiary=True,
            dateOfBirth=datetime.datetime(2002, 6, 8),
            idPieceNumber="140767100016",
        )
        user = users_factories.UserFactory(
            hasCompletedIdCheck=True,
            isBeneficiary=False,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
            dateOfBirth=datetime.datetime(2002, 6, 8),
            email=self.user_email,
        )
        _get_raw_content.return_value = self.JOUVE_CONTENT

        response = client.post("/beneficiaries/application_update", json={"id": self.application_id})
        assert response.status_code == 200

        fraud_result = fraud_models.BeneficiaryFraudResult.query.filter_by(user=user).first()

        assert fraud_result.status == fraud_models.FraudStatus.SUSPICIOUS
        assert (
            fraud_result.reason
            == f"Duplicat de l'utilisateur {existing_user.id} ; Le n° de cni 140767100016 est déjà pris par l'utilisateur {existing_user.id}"
        )

        db.session.refresh(user)
        assert not user.isBeneficiary

    @patch("pcapi.connectors.beneficiaries.jouve_backend._get_raw_content")
    def test_jouve_update_id_fraud(self, _get_raw_content, client):

        user = users_factories.UserFactory(
            hasCompletedIdCheck=True,
            isBeneficiary=False,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
            dateOfBirth=datetime.datetime(2002, 6, 8),
            email=self.user_email,
        )
        _get_raw_content.return_value = self.JOUVE_CONTENT | {"serviceCodeCtrl": "KO", "bodyFirstNameLevel": "30"}

        response = client.post("/beneficiaries/application_update", json={"id": self.application_id})
        assert response.status_code == 200

        fraud_result = fraud_models.BeneficiaryFraudResult.query.filter_by(user=user).first()

        assert fraud_result.status == fraud_models.FraudStatus.KO
        assert (
            fraud_result.reason
            == "Le champ serviceCodeCtrl est KO ; Le champ bodyFirstNameLevel a le score 30 (minimum 50)"
        )

        db.session.refresh(user)
        assert not user.isBeneficiary


class CommonFraudCheckTest:
    def test_duplicate_id_piece_number_ok(self):
        fraud_item = fraud_api._duplicate_id_piece_number_fraud_item("random_id")
        assert fraud_item.status == fraud_models.FraudStatus.OK

    def test_duplicate_id_piece_number_suspicious(self):
        user = users_factories.UserFactory(isBeneficiary=True)

        fraud_item = fraud_api._duplicate_id_piece_number_fraud_item(user.idPieceNumber)
        assert fraud_item.status == fraud_models.FraudStatus.SUSPICIOUS

    def test_duplicate_user_fraud_ok(self):
        fraud_item = fraud_api._duplicate_user_fraud_item(
            first_name="Jean", last_name="Michel", birth_date=datetime.date.today()
        )

        assert fraud_item.status == fraud_models.FraudStatus.OK

    def test_duplicate_user_fraud_suspicious(self):
        user = users_factories.UserFactory(isBeneficiary=True)
        fraud_item = fraud_api._duplicate_user_fraud_item(
            first_name=user.firstName, last_name=user.lastName, birth_date=user.dateOfBirth.date()
        )

        assert fraud_item.status == fraud_models.FraudStatus.SUSPICIOUS
