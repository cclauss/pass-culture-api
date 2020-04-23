import enum

from sqlalchemy import String, Column, Enum

from models.db import Model
from models.deactivable_mixin import DeactivableMixin
from models.pc_object import PcObject


class FeatureToggle(enum.Enum):
    BENEFICIARIES_IMPORT = 'Permettre l''import des comptes jeunes depuis DMS'
    DEGRESSIVE_REIMBURSEMENT_RATE = 'Permettre le remboursement avec un barème dégressif par lieu'
    FULL_OFFERS_SEARCH_WITH_OFFERER_AND_VENUE = 'Permet la recherche de mots-clés dans les tables structures' \
                                                ' et lieux en plus de celles des offres'
    QR_CODE = 'Permettre la validation d''une contremarque via QR code'
    NEW_RIBS_UPLOAD = 'Permettre aux utilisateurs d''uploader leur ribs via la nouvelle démarche DMS'
    SEARCH_ALGOLIA = 'Permettre la recherche via Algolia'
    SYNCHRONIZE_ALGOLIA = 'Permettre la mise à jour des données pour la recherche via Algolia'
    SYNCHRONIZE_ALLOCINE = 'Permettre la synchronisation journalière avec Allociné'
    SYNCHRONIZE_BANK_INFORMATION = 'Permettre la synchronisation journalière avec DMS' \
                                   ' pour récupérer les informations bancaires des acteurs'
    SYNCHRONIZE_LIBRAIRES = 'Permettre la synchronisation journalière avec leslibraires.fr'
    SYNCHRONIZE_TITELIVE = 'Permettre la synchronisation journalière avec TiteLive / Epagine'
    SYNCHRONIZE_TITELIVE_PRODUCTS = 'Permettre l''import journalier du référentiel des livres'
    SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION = 'Permettre l''import journalier des résumés des livres'
    SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS = 'Permettre l''import journalier des couvertures de livres'
    UPDATE_DISCOVERY_VIEW = 'Permettre la mise à jour des données du carousel'
    UPDATE_BOOKING_USED = 'Permettre la validation automatique des contremarques 48h après la fin de l''évènement'
    WEBAPP_SIGNUP = 'Permettre aux bénéficiaires de créer un compte'
    RECOMMENDATIONS_WITH_DISCOVERY_VIEW = 'Permettre aux utilisateurs d''avoir des recommandations de manière plus rapide'
    RECOMMENDATIONS_WITH_GEOLOCATION = 'Permettre aux utilisateurs d''avoir accès aux offres à 100km de leur position'
    RECOMMENDATIONS_WITH_DIGITAL_FIRST = 'Permettre aux bénéficiaires d''avoir des recommendations' \
                                         ' concernant des offres numériques en priorité'
    SAVE_SEEN_OFFERS = 'Enregistrer en base les offres déjà vues par les utilisateurs'
    BOOKINGS_V2 = 'Permettre d''afficher la nouvelle visualisation des réservations d''un offreur'


class Feature(PcObject, Model, DeactivableMixin):
    name = Column(Enum(FeatureToggle), index=True, unique=True, nullable=False)
    description = Column(String(300), nullable=False)

    @property
    def nameKey(self):
        return str(self.name).replace('FeatureToggle.', '')
