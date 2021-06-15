from typing import Iterable

import pcapi.core.offers.models as offers_models


class SearchBackend:
    def async_index_offer_ids(self, offer_ids: Iterable[int]):
        raise NotImplementedError()

    def enqueue_offer_ids(self, offer_ids: Iterable[int]):
        raise NotImplementedError()

    def enqueue_offer_ids_in_error(self, offer_ids: Iterable[int]):
        raise NotImplementedError()

    def check_offer_is_indexed(self, offer: offers_models.Offer):
        pass

    def index_offers(self, offers: Iterable[offers_models.Offer]) -> None:
        raise NotImplementedError()

    def unindex_offer_ids(self, offers: Iterable[int]) -> None:
        raise NotImplementedError()
