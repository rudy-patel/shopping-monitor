"""Import production retailer modules for side-effect registration."""

from __future__ import annotations

from scrapers.abercrombie import register_abercrombie
from scrapers.apple_ca import register_apple_ca
from scrapers.bestbuy_ca import register_bestbuy_ca
from scrapers.generic import register_generic
from scrapers.indigo import register_indigo
from scrapers.palmisleskate import register_palmisleskate
from scrapers.tikiroomskate import register_tikiroomskate

register_generic()
register_bestbuy_ca()
register_palmisleskate()
register_tikiroomskate()
register_indigo()
register_apple_ca()
register_abercrombie()
