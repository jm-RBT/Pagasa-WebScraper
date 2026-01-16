"""
Modular PAGASA WebScraper Package

A modular and reusable implementation of the PAGASA typhoon bulletin scraper
and analyzer. Designed for programmatic use in other systems.

Usage:
    from modular.main import get_pagasa_data
    
    result = get_pagasa_data()
    print(result['typhoon_name'])
    print(result['data'])
"""

from .main import get_pagasa_data

__all__ = ['get_pagasa_data']
