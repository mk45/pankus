#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import json,pdb,math
from .utils import TaurusLongTask
from heapq import heappush,heappop
from vincenty import vincenty
from .data_journal import DataJournal
from .utils import init_kwargs_as_parameters

class Route(DataJournal):


    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    # generates connections between pairs of points. A connection has specified start, end and weight written in the table "connection".
    # Connections are inserted into tables using SQL scripts "create_connection" and "insert_connection".
    # "insert_connection" script uses tables "network_geometry" and "point" to write data into new tables.
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("connection")
    def generate_connections(self,weight_name="weight",**kwargs):
        """
        "generate_connections" function creates connections between pairs of points using network geometry and points data.
        Each connection is expressed as a set of data - start id, end id and weight.

        """

        self.do('route/create_connection')
        self.do('route/insert_connection',{
            'weight_name':weight_name
        })

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("distance")
    def distance_air_lines(self,distance_type="geom",**kwargs):
        """
        Args:
            distance_type (varchar): 'geom'  for geometrical distance or 'vincenty' for WGS 84 with distance from vincenty algorithm
        """
        assert self.one('route/test_point_id_range')[0]
        self.do('route/create_distance')

        featured_points=self.do('route/select_od_point').fetchall()
        all_points=self.do('route/select_point').fetchall()


        for start_point_geometry,start,_, in TaurusLongTask(\
                                                featured_points,\
                                                additional_text='Distances',\
                                                **kwargs):
            new_distances=[]
            sp_json_geometry=json.loads(start_point_geometry)

            for end_point_geometry,i,_, in all_points:
                ep_json_geometry=json.loads(end_point_geometry)

                if distance_type=="geom":
                    dist=sum([(i[0]-i[1])**2 for i in zip(ep_json_geometry,sp_json_geometry)])**0.5
                elif distance_type=="vincenty":
                    dist=vincenty(sp_json_geometry,ep_json_geometry)
                else:
                    #dist=None
                    raise ValueError("Unknown value")

                new_distances.append({
                   'start_id': start,
                   'end_id': i,
                   'weight': dist,
                   'successor_id': i,
                   'predecessor_id': start
                })

            self.transaction('route/import_distance',new_distances)
        self.commit()


    # it creates distances meant as routes between pairs of origin-destination points, built from previously generated connections.
    # Distances are written in the table distance. Each record in the distance table is described by following parameters: start id, end id, weight, successorr id and predecessor id.
    # Data is written into table distance using SQL script "import_distance".
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("distance")
    def distance(self,**kwargs):
        """
        "distance" function creates distances meant as routes between pairs of origin-destination points built from available connections.
        Distances are expressed as a set od following data: start_id, end_id, weight, successor id and predecessor id.
        """
        #self.generate_connections()
        assert self.one('route/test_point_id_range')[0]
        self.do('route/create_distance')

        featured_points=self.do('route/select_od_point').fetchall()
        all_points=self.do('route/select_point').fetchall()

        connections=[{} for _ in all_points]
        for start,end,weight, in self.do('route/select_connection'):
            connections[start][end]=weight

        for _,start,_, in TaurusLongTask(\
                            featured_points,\
                            additional_text='Distances',\
                            **kwargs):
            #heap
            H=[]
            new_distances = [{
               'start_id': start,
               'end_id': i,
               'weight': float('inf'),
               'successor_id': None,
               'predecessor_id': None
            } for _,i,_, in all_points]

            used=[False for _ in all_points]
            new_distances[start]['weight'] = 0
            new_distances[start]['predecessor_id'] = start
            new_distances[start]['successor_id'] = start
            used[start] = True

            for end,weight in connections[start].items():
                new_distances[end]['weight'] = weight
                new_distances[end]['successor_id'] = end
                new_distances[end]['predecessor_id'] = start
                heappush(H, (weight, end))

            while H != []:

                weight,closest_end = heappop(H)
                if used[closest_end]:
                    continue

                used[closest_end] = True

                for n_end,c_weight in connections[closest_end].items():
                    if used[n_end]:
                        continue
                    n_weight = c_weight+weight
                    if new_distances[n_end]['weight'] > n_weight:
                        new_distances[n_end]['weight'] = n_weight
                        new_distances[n_end]['successor_id'] = new_distances[closest_end]['successor_id']
                        new_distances[n_end]['predecessor_id'] = closest_end
                        heappush(H,(n_weight, n_end))
            self.transaction('route/import_distance',new_distances)
        self.commit()
