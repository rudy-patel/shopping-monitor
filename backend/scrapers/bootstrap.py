"""Import production retailer modules for side-effect registration."""

from __future__ import annotations

from scrapers.bestbuy_ca import register_bestbuy_ca
from scrapers.generic import register_generic
from scrapers.palmisleskate import register_palmisleskate
from scrapers.tikiroomskate import register_tikiroomskate

register_generic()
register_bestbuy_ca()
register_palmisleskate()
register_tikiroomskate()
