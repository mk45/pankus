#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import json,pdb
from .data_journal import DataJournal
from .utils import init_kwargs_as_parameters

class MST(DataJournal):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("bmst_connection", "bmst")
    def minimum_spanning_tree_from_network(self,**kwargs):
        self.do('mst/create_boruvka_mst')
        self.do('mst/bmst_connections_from_network')
        self.do('mst/initialize_bmst')
        self.save_bmst_parameters=self.save_bmst_parameters_to_od_properties
        self.mst()

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("bmst_connection", "bmst")
    def minimum_spanning_tree_from_distance(self,**kwargs):
        self.do('mst/create_boruvka_mst')
        self.do('mst/bmst_connections_from_distance')
        self.do('mst/initialize_bmst')
        self.save_bmst_parameters=self.save_bmst_parameters_to_network
        self.mst()

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash()
    def save_bmst_parameters(self,suffix,**kwargs):
        #only proxy function Wont work until mst executed
        pass

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("od_properties")
    def save_bmst_parameters_to_od_properties(self,suffix='supernode',**kwargs):
        max_level=self.one('bmst/select_max_level')[0]
        for level in range(max_level+1):
            self.do('bmst/save_bmst_to_od',{
                'level':level,
                'supernode_level_name':'L'+str(level)+suffix
            })

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("network_properties")
    def save_bmst_parameters_to_network(self,suffix='supernode',level="Level",**kwargs):
        self.do('bmst/save_network_level',{
            'level_name':level
        })
        max_level=self.one('bmst/select_max_level')[0]
        for level in range(max_level+1):
            self.do('bmst/save_bmst_supernode_to_network_end',{
                'level':level,
                'supernode_level_name':'L'+str(level)+suffix
            })


    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("bmst", "bmst_used_connection")
    def mst(self,**kwargs):
        #iterator=iter(ProgressBar(range(len(featured_points)**2)))
        while not self.one('mst/bmst_finish_condition')[0]:
            self.do('mst/bmst_step')
