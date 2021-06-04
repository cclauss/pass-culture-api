import random

import factory

from pcapi.core import testing
import pcapi.core.users.factories as users_factories

from . import models


class BeneficiaryFraudCheckFactory(testing.BaseFactory):
    class Meta:
        model = models.BeneficiaryFraudCheck

    user = factory.SubFactory(users_factories.UserFactory)
    type = factory.LazyAttribute(lambda o: random.choice(list(models.FraudCheckerThirdParty)))


class BeneficiaryFraudResult(testing.BaseFactory):
    class Meta:
        model = models.BeneficiaryFraudResult

    user = factory.SubFactory(users_factories.UserFactory)
    score = factory.LazyAttribute(lambda o: random.randint(0, 100))
    status = factory.LazyAttribute(lambda o: random.choice(list(models.FraudStatus)))


class BeneficiaryFraudReview(testing.BaseFactory):
    class Meta:
        model = models.BeneficiaryFraudReview

    author = factory.SubFactory(users_factories.UserFactory, isAdmin=True)
