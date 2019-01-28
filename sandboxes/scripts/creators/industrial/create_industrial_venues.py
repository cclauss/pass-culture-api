import re

from models.pc_object import PcObject
from sandboxes.scripts.utils.venue_mocks import MOCK_NAMES
from utils.logger import logger
from utils.test_utils import create_venue

OFFERER_WITH_PHYSICAL_VENUE_MODULO = 3
OFFERER_WITH_PHYSICAL_VENUE_WITH_SIRET_MODULO = 6

def create_industrial_venues(offerers_by_name):
    logger.info('create_industrial_venues')

    venue_by_name = {}
    mock_index = 0

    iban_count = 0
    iban_prefix = 'FR7630001007941234567890185'
    bic_prefix, bic_suffix = 'QSDFGH8Z', 556

    for (offerer_index, (offerer_name, offerer)) in enumerate(offerers_by_name.items()):
        geoloc_match = re.match(r'(.*)lat\:(.*) lon\:(.*)', offerer_name)

        venue_name = MOCK_NAMES[mock_index%len(MOCK_NAMES)]

        # create all possible cases:
        # offerer with or without iban / venue with or without iban
        if offerer.iban:
            if iban_count == 0:
                iban = iban_prefix
                bic = bic_prefix + str(bic_suffix)
                iban_count = 1
            elif iban_count == 2:
                iban = None
                bic = None
                iban_count = 3
        else:
            if iban_count == 0 or iban_count == 1:
                iban = iban_prefix
                bic = bic_prefix + str(bic_suffix)
                iban_count = 2
            elif iban_count == 3:
                iban = None
                bic = None
                iban_count = 0

        # every OFFERER_WITH_PHYSICAL_VENUE_MODULO offerers, create an offerer with no physical venue
        if offerer_index%OFFERER_WITH_PHYSICAL_VENUE_MODULO:

            # every OFFERER_WITH_PHYSICAL_VENUE_WITH_SIRET_MODULO offerers, create a physical venue with no siret
            if offerer_index%OFFERER_WITH_PHYSICAL_VENUE_WITH_SIRET_MODULO:
                comment = None
                siret = '{}11111'.format(offerer.siren)
            else:
                comment = "Pas de siret car c'est comme cela."
                siret = None

            venue_by_name[venue_name] = create_venue(
                offerer,
                address=offerer.address,
                bic=bic,
                booking_email="fake@email.com",
                city=offerer.city,
                comment=comment,
                iban=iban,
                latitude=float(geoloc_match.group(2)),
                longitude=float(geoloc_match.group(3)),
                name=venue_name,
                postal_code=offerer.postalCode,
                siret=siret
            )

        bic_suffix += 1
        mock_index += 1

        venue_by_name["{} (Offre en ligne)".format(venue_name)] = create_venue(
            offerer,
            is_virtual=True,
            name="{} (Offre en ligne)".format(venue_name),
            siret=None
        )

    PcObject.check_and_save(*venue_by_name.values())

    logger.info('created {} venues'.format(len(venue_by_name)))

    return venue_by_name
