#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'
__all__ = [
    'Taurus'
]
__taurus_version__="4.0"
from .importer import Importer
from .route import Route
from .intervening_opportunities import InterveningOpportunities
from .mst import MST
from .network_generators import NetworkGenerator
from .analysis import Analysis
from .data_journal import DataJournal

class Taurus(Route,InterveningOpportunities,MST,NetworkGenerator,Analysis,DataJournal):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
