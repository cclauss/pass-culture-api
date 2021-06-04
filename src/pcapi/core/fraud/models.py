import enum

import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

from pcapi.models.db import Model
from pcapi.models.pc_object import PcObject


class FraudCheckerThirdParty(enum.Enum):
    JOUVE = "jouve"
    THREATMETRIX = "threatmetrix"
    DMS = "dms"


class FraudStatus(enum.Enum):
    OK = "OK"
    KO = "KO"
    SUSPICIOUS = "SUSPICIOUS"


class BeneficiaryFraudCheck(PcObject, Model):
    __tablename__ = "beneficiary_fraud_check"

    id = sqlalchemy.Column(sqlalchemy.BigInteger, primary_key=True, autoincrement=True)

    dateCreated = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now())

    userId = sqlalchemy.Column(sqlalchemy.BigInteger, sqlalchemy.ForeignKey("user.id"), index=True, nullable=False)

    user = sqlalchemy.orm.relationship("User", foreign_keys=[userId], backref="beneficiaryFraudChecks")

    type = sqlalchemy.Column(sqlalchemy.Enum(FraudCheckerThirdParty), nullable=False)

    resultContent = sqlalchemy.Column(sqlalchemy.dialects.postgresql.JSONB)

    reason = sqlalchemy.Column(sqlalchemy.Text)


class BeneficiaryFraudResult(PcObject, Model):
    __tablename__ = "beneficiary_fraud_result"

    id = sqlalchemy.Column(sqlalchemy.BigInteger, primary_key=True, autoincrement=True)

    userId = sqlalchemy.Column(sqlalchemy.BigInteger, sqlalchemy.ForeignKey("user.id"), index=True, nullable=False)

    user = sqlalchemy.orm.relationship("User", foreign_keys=[userId], backref="beneficiaryFraudResult")

    score = sqlalchemy.Column(sqlalchemy.Integer)

    status = sqlalchemy.Column(sqlalchemy.Enum(FraudStatus))

    reason = sqlalchemy.Column(sqlalchemy.Text)


class BeneficiaryFraudReview(PcObject, Model):
    __tablename__ = "beneficiary_fraud_review"

    authorId = sqlalchemy.Column(sqlalchemy.BigInteger, sqlalchemy.ForeignKey("user.id"), index=True, nullable=False)

    author = sqlalchemy.orm.relationship("User", foreign_keys=[authorId], backref="beneficiaryFraudReviews")

    dateReviewed = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now())
