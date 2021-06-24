import datetime
import logging
import typing
from typing import List
from typing import Optional

import sqlalchemy

from pcapi.core.users.models import User
from pcapi.models.db import db
from pcapi.models.feature import FeatureToggle
from pcapi.repository import feature_queries
from pcapi.repository import repository
from pcapi.repository.user_queries import matching

from . import exceptions
from . import models


logger = logging.getLogger(__name__)


def on_jouve_result(user: User, jouve_content: models.JouveContent):
    if (
        models.BeneficiaryFraudCheck.query.filter(
            models.BeneficiaryFraudCheck.user == user,
            models.BeneficiaryFraudCheck.type.in_([models.FraudCheckType.JOUVE, models.FraudCheckType.DMS]),
        ).count()
        > 0
    ):
        # TODO: raise error and do not allow 2 DMS/Jouve FraudChecks
        return

    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=models.FraudCheckType.JOUVE,
        thirdPartyId=str(jouve_content.id),
        resultContent=jouve_content.dict(),
    )
    repository.save(fraud_check)

    # TODO: save user fields from jouve_content

    on_identity_fraud_check_result(user, fraud_check)


def on_identity_fraud_check_result(user: User, beneficiary_fraud_check: models.BeneficiaryFraudCheck):
    if user.isBeneficiary:
        raise exceptions.UserAlreadyBeneficiary()
    if not user.isEmailValidated:
        raise exceptions.UserEmailNotValidated()
    if feature_queries.is_active(FeatureToggle.FORCE_PHONE_VALIDATION) and not user.is_phone_validated:
        raise exceptions.UserPhoneNotValidated()

    jouve_content = models.JouveContent(**beneficiary_fraud_check.resultContent)

    fraud_items = []
    fraud_items.append(
        _duplicate_user_fraud_item(
            first_name=jouve_content.firstName,
            last_name=jouve_content.lastName,
            birth_date=datetime.datetime.strptime(jouve_content.birthDate, "%m/%d/%Y"),
        )
    )

    fraud_items.append(_duplicate_id_piece_number_fraud_item(jouve_content.bodyPieceNumber))
    fraud_items.extend(_id_check_fraud_items(jouve_content))

    if all(fraud_item.status == models.FraudStatus.OK for fraud_item in fraud_items):
        status = models.FraudStatus.OK
    elif any(fraud_item.status == models.FraudStatus.KO for fraud_item in fraud_items):
        status = models.FraudStatus.KO
    else:
        status = models.FraudStatus.SUSPICIOUS

    fraud_result = models.BeneficiaryFraudResult(
        user=user,
        status=status,
        reason=" ; ".join(
            fraud_item.detail for fraud_item in fraud_items if fraud_item.status != models.FraudStatus.OK
        ),
    )
    repository.save(fraud_result)


def _duplicate_user_fraud_item(first_name: str, last_name: str, birth_date: datetime.date) -> models.FraudItem:
    duplicate_user = User.query.filter(
        matching(User.firstName, first_name)
        & (matching(User.lastName, last_name))
        & (sqlalchemy.func.DATE(User.dateOfBirth) == birth_date)
        & (User.isBeneficiary == True)
    ).first()

    return models.FraudItem(
        status=models.FraudStatus.SUSPICIOUS if duplicate_user else models.FraudStatus.OK,
        detail=f"Duplicat de l'utilisateur {duplicate_user.id}" if duplicate_user else None,
    )


def _duplicate_id_piece_number_fraud_item(document_id_number: str) -> models.FraudItem:
    duplicate_user = User.query.filter(User.idPieceNumber == document_id_number).first()
    return models.FraudItem(
        status=models.FraudStatus.SUSPICIOUS if duplicate_user else models.FraudStatus.OK,
        detail=f"Le n° de cni {document_id_number} est déjà pris par l'utilisateur {duplicate_user.id}"
        if duplicate_user
        else None,
    )


def _id_check_fraud_items(content: models.JouveContent) -> List[models.FraudItem]:
    if not feature_queries.is_active(FeatureToggle.ENABLE_IDCHECK_FRAUD_CONTROLS):
        return []

    fraud_items = []

    fraud_items.append(_get_boolean_id_fraud_item(content.posteCodeCtrl, "posteCodeCtrl", True))
    fraud_items.append(_get_boolean_id_fraud_item(content.serviceCodeCtrl, "serviceCodeCtrl", True))
    fraud_items.append(_get_boolean_id_fraud_item(content.birthLocationCtrl, "birthLocationCtrl", True))
    fraud_items.append(_get_boolean_id_fraud_item(content.bodyBirthDateCtrl, "bodyBirthDateCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.bodyFirstNameCtrl, "bodyFirstNameCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.bodyNameCtrl, "bodyNameCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.bodyPieceNumberCtrl, "bodyPieceNumberCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.creatorCtrl, "creatorCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.initialNumberCtrl, "initialNumberCtrl", False))
    fraud_items.append(_get_boolean_id_fraud_item(content.initialSizeCtrl, "initialSizeCtrl", False))

    fraud_items.append(_get_threshold_id_fraud_item(content.bodyBirthDateLevel, "bodyBirthDateLevel", 100, False))
    fraud_items.append(_get_threshold_id_fraud_item(content.bodyNameLevel, "bodyNameLevel", 50, False))
    fraud_items.append(_get_threshold_id_fraud_item(content.bodyFirstNameLevel, "bodyFirstNameLevel", 50, False))
    fraud_items.append(_get_threshold_id_fraud_item(content.bodyPieceNumberLevel, "bodyPieceNumberLevel", 50, False))

    return fraud_items


def _get_boolean_id_fraud_item(value: Optional[str], key: str, is_strict_ko: bool) -> models.FraudItem:
    is_valid = value.upper() != "KO" if value else True
    if is_valid:
        status = models.FraudStatus.OK
    elif is_strict_ko:
        status = models.FraudStatus.KO
    else:
        status = models.FraudStatus.SUSPICIOUS

    return models.FraudItem(status=status, detail=f"Le champ {key} est {value}")


def _get_threshold_id_fraud_item(
    value: Optional[int], key: str, threshold: int, is_strict_ko: bool
) -> models.FraudItem:
    try:
        is_valid = int(value) >= threshold if value else True
    except ValueError:
        is_valid = True
    if is_valid:
        status = models.FraudStatus.OK
    elif is_strict_ko:
        status = models.FraudStatus.KO
    else:
        status = models.FraudStatus.SUSPICIOUS

    return models.FraudItem(status=status, detail=f"Le champ {key} a le score {value} (minimum {threshold})")


def dms_fraud_check(
    user: User,
    dms_content: typing.Union[models.DemarchesSimplifieesContent, dict],
):
    if isinstance(dms_content, dict):
        dms_content = models.DemarchesSimplifieesContent(**dms_content)

    fraud_check = models.BeneficiaryFraudCheck(
        user=user,
        type=models.FraudCheckType.DMS,
        thirdPartyId=str(dms_content.application_id),
        resultContent=dms_content,
    )

    db.session.add(fraud_check)
    db.session.commit()
