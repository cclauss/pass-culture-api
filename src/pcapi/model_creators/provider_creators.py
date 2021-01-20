from datetime import datetime

from pcapi.local_providers.providable_info import ProvidableInfo
from pcapi.models.db import Model
from pcapi.models.product import Product
from pcapi.models.provider import Provider
from pcapi.repository import repository
from pcapi.repository.provider_queries import get_provider_by_local_class


def activate_provider(provider_classname: str) -> Provider:
    provider = get_provider_by_local_class(provider_classname)
    provider.isActive = True
    provider.enabledForPro = True
    repository.save(provider)
    return provider


def create_providable_info(
    model_name: Model = Product, id_at_providers: str = "1", date_modified: datetime = None
) -> ProvidableInfo:
    providable_info = ProvidableInfo()
    providable_info.type = model_name
    providable_info.id_at_providers = id_at_providers
    if date_modified:
        providable_info.date_modified_at_provider = date_modified
    else:
        providable_info.date_modified_at_provider = datetime.utcnow()
    return providable_info
