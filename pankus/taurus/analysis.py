#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

#from ipy_progressbar import ProgressBar
import numpy as np
from .importer import Importer
from .data_journal import DataJournal
from .utils import init_kwargs_as_parameters


class Analysis(DataJournal):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def solve_for_origins(self,**kwargs):
        '''
        Let A*S=D where D - destination satisfied vector A - motion exchange matrix and S - origins vector.
        This function solves S=A\D.

        Stores output in parameters table.
        '''
        assert self.one('route/test_point_id_range')[0]
        featured_points=self.do('route/select_od_point').fetchall()

        # get mx matrix
        motion_exchange=[[0.0 for j in featured_points] for i in featured_points]
        for s,e,f, in  self.do('intopp/select_motion_exchange_fraction'):
            motion_exchange[s][e]=f

        # get destinations
        destinations_list=[0.0 for i in featured_points]
        for od_id,_,destinations,_,_,_,_, in self.do('intopp/select_model_parameters').fetchall():
            destinations_list[od_id]=destinations

        #create matrix and solve
        matrix=np.array(motion_exchange)
        origins_list_=np.linalg.solve(matrix.transpose(),destinations_list)

        #solution accuracy
        accuracy = (np.linalg.cond(matrix)*np.finfo(float).eps)

        # save solutions

        new_origins_value=[{
                "od_id":i,
                "origins":origins
            } for i,origins in enumerate(origins_list_)]
        self.transaction("analysis/update_origins",new_origins_value)
        return accuracy

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash()
    def get_no_ring_pairs(self,**kwargs):
        for a,b in self.do('intopp/select_od_id_with_no_ring_assigned').fetchall():
            print("Origin: ", a, " and destination: ", b , " - no ring assigned!")
