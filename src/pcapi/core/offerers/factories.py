import bcrypt
import factory

from pcapi.core.offerers.models import ApiKey
from pcapi.core.offerers.models import VenueLabel
from pcapi.core.offerers.models import VenueType
from pcapi.core.offers.factories import OffererFactory
from pcapi.core.offers.factories import VenueFactory
import pcapi.core.providers.models
from pcapi.core.providers.models import AllocineVenueProvider
from pcapi.core.providers.models import AllocineVenueProviderPriceRule
from pcapi.core.testing import BaseFactory


class ProviderFactory(BaseFactory):
    class Meta:
        model = pcapi.core.providers.models.Provider
        sqlalchemy_get_or_create = ["localClass"]

    name = factory.Sequence("Provider {}".format)
    localClass = factory.Sequence("{}Stocks".format)
    enabledForPro = True
    isActive = True


class APIProviderFactory(BaseFactory):
    class Meta:
        model = pcapi.core.providers.models.Provider

    name = factory.Sequence("Provider {}".format)
    apiUrl = factory.Sequence("https://{}.example.org/stocks".format)
    enabledForPro = True
    isActive = True


class VenueProviderFactory(BaseFactory):
    class Meta:
        model = pcapi.core.providers.models.VenueProvider

    venue = factory.SubFactory(VenueFactory)
    provider = factory.SubFactory(APIProviderFactory)

    venueIdAtOfferProvider = factory.SelfAttribute("venue.siret")


class AllocineProviderFactory(BaseFactory):
    class Meta:
        model = pcapi.core.providers.models.Provider
        sqlalchemy_get_or_create = ["localClass"]

    name = factory.Sequence("Provider {}".format)
    localClass = "AllocineStocks"


class AllocineVenueProviderFactory(BaseFactory):
    class Meta:
        model = AllocineVenueProvider

    venue = factory.SubFactory(VenueFactory)
    provider = factory.SubFactory(AllocineProviderFactory)
    venueIdAtOfferProvider = factory.SelfAttribute("venue.siret")
    internalId = factory.Sequence("P{}".format)
    isDuo = True
    quantity = 1000


class AllocineVenueProviderPriceRuleFactory(BaseFactory):
    class Meta:
        model = AllocineVenueProviderPriceRule

    allocineVenueProvider = factory.SubFactory(AllocineVenueProviderFactory)
    priceRule = "default"
    price = 5.5


class VirtualVenueTypeFactory(BaseFactory):
    class Meta:
        model = VenueType

    label = "Offre numérique"


class VenueTypeFactory(BaseFactory):
    class Meta:
        model = VenueType

    label = "Librairie"


class VenueLabelFactory(BaseFactory):
    class Meta:
        model = VenueLabel

    label = "Cinéma d'art et d'essai"


DEFAULT_PREFIX = "development_prefix"
DEFAULT_SECRET = "clearSecret"
DEFAULT_CLEAR_API_KEY = f"{DEFAULT_PREFIX}_{DEFAULT_SECRET}"


class ApiKeyFactory(BaseFactory):
    class Meta:
        model = ApiKey

    offerer = factory.SubFactory(OffererFactory)
    prefix = DEFAULT_PREFIX

    @factory.post_generation
    def hash_secret(self, create, extracted):
        self.secret = bcrypt.hashpw((extracted or DEFAULT_SECRET).encode("utf-8"), bcrypt.gensalt())
