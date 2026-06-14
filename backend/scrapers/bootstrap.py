"""Import production retailer modules for side-effect registration."""

from __future__ import annotations

from scrapers.bestbuy_ca import register_bestbuy_ca
from scrapers.dimemtl import register_dimemtl
from scrapers.generic import register_generic

register_generic()
register_bestbuy_ca()
register_dimemtl()
