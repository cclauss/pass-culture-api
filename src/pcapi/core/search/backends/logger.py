import logging

from flask import current_app

from pcapi.core.search import testing

from .algolia import AlgoliaBackend


logger = logging.getLogger(__name__)


class FakeClient:
    def add_objects(self, objects):
        logger
        for obj in objects:
            testing[obj["id"]] = obj

    def delete_objects(self, objects):
        for obj in objects:
            testing.pop(obj["id"], None)


class Testing(AlgoliaBackend):
    """A backend to be used by automated tests.

    We subclass a real-looking backend to be as close as possible to
    what we have in production. Only the communication with the
    external search service is faked.
    """

    def __init__(self):
        self.algolia_client = FakeClient()
        self.redis_client = current_app.redis_client
