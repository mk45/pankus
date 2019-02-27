#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import json,pdb
from .utils import TaurusLongTask
from .data_journal import DataJournal
from .utils import init_kwargs_as_parameters

class Exporter(DataJournal):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    @init_kwargs_as_parameters
    def export_network_geojson(self,
                                out_network_filename="out_net.geojson",
                                fields=None, #if none select all fields ; else list of filelds
                                **kwargs):

        number_of_element,=self.one('exporter/count_network')

        features_to_export={}

        def add_field(name,values):
            if features_to_export=={}:
                for start,end,_ in values:
                    features_to_export[(start,end)]={}
            for start,end,value in values:
                features_to_export[(start,end)][name]=value

        if fields == None:
            fields = [f for f, in self.do('exporter/select_network_names')]

        for name in fields:
            values = [(start,end,value) for start,end,value in self.do('exporter/select_network_named_values',{'name':name}) if value is not None]
            # check number of elements
            if len(values) != number_of_element:
                print("skipping field ",name)
                continue

            try:
                float_values=list(map(lambda x:(x[0],x[1],float(x[2])),values))
            except:
                # it is a sql_string
                add_field(name,values)
                continue

            int_values=list(map(lambda x:(x[0],x[1],int(x[2])),float_values))
            if int_values==float_values:
                add_field(name,int_values)
            else:
                add_field(name,float_values)


        geojson={"type": "FeatureCollection","features": []}
        for start,end,linestring in self.do('exporter/select_network_geometry'):
            geojson["features"].append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": eval(linestring)
                    },
                "properties" : features_to_export[(start,end)]
            })

        with open(out_network_filename,'w',encoding='utf-8') as net:
            json.dump(geojson,net)

    @init_kwargs_as_parameters
    def export_od_geojson(self,
                            out_od_filename="out_od.geojson",
                            fields=None, #if none select all fields ; else list of filelds
                            **kwargs):
        number_of_element,=self.one('exporter/count_od')
        features_to_export={}
        def add_field(name,values):
            if features_to_export=={}:
                for od_id,_ in values:
                    features_to_export[od_id]={}
            for od_id,value in values:
                features_to_export[od_id][name]=value

        if fields == None:
            fields = [f for f, in self.do('exporter/select_od_names')]

        for name in fields:
            values = [(od_id,value) for od_id,value in self.do('exporter/select_od_named_values',{'name':name}) if value is not None]

            # check number of elements
            if len(values) != number_of_element:
                print("skipping field ",name)
                continue

            try:
                float_values=list(map(lambda x:(x[0],float(x[1])),values))
            except:
                # it is a sql_string
                add_field(name,values)
                continue

            int_values=list(map(lambda x:(x[0],int(x[1])),float_values))
            if int_values==float_values:
                add_field(name,int_values)
            else:
                add_field(name,float_values)

        geojson={"type": "FeatureCollection","features": []}
        for od_id,point in self.do('exporter/select_od_geometry'):
            geojson["features"].append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": eval(point)
                    },
                "properties" : features_to_export[od_id]
            })

        with open(out_od_filename,'w',encoding='utf-8') as od:
            json.dump(geojson,od)
