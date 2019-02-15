#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import json,pdb,math
from .utils import TaurusLongTask
from .data_journal import DataJournal
from .utils import init_kwargs_as_parameters

class InterveningOpportunities(DataJournal):

    # uploading keyword arguments, if the value is missing field is filled with default value
    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    # importing model parameters, if the values are not given default values from function init are used
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def import_model_parameters(self,
                                origins_name='origins',
                                destinations_name='destinatons',
                                selectivity_name='selectivity',
                                convolution_start_name='conv_a',
                                convolution_size_name='conv_b',
                                convolution_intensity_name='conv_alpha',
                                **kwargs):
        """
        importing model parameters, if the values are not given default values from function init are used
        """
        self.do('intopp/create_model_parameters')
        self.do('intopp/insert_model_parameters',{
            'origins_name':origins_name,
            'destinations_name':destinations_name,
            'selectivity_name':selectivity_name,
            'convolution_start_name':convolution_start_name,
            'convolution_size_name':convolution_size_name,
            'convolution_intensity_name':convolution_intensity_name
        })

    # creating selectivity, a parameter describing probability of object choosing a point as a destination,
    # taking into consideration other point placed between the object and considered point.
    # Sum of all destinations from table "model_parameters" is selected, then used to calculate selectivity value,
    # which is later updated in the "model_parameters" table.
    # Before being written in the table value of selectivity is multiplied by 1 000 000 to include its fractional part with high accuracy.
    # When selectivity value is used in calculations it is divided by the same number.
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def create_escape_fraction_selectivity(self,efs,**kwargs):
        """
        creating selectivity, a parameter describing probability of object choosing a point as a destination,
        taking into consideration other point placed between the object and considered point.
        Sum of all destinations from table "model_parameters" is selected, then used to calculate selectivity value,
        which is later updated in the "model_parameters" table.
        Before being written in the table value of selectivity is multiplied by 1 000 000 to include its fractional part with high accuracy.
        When selectivity value is used in calculations it is divided by the same number.

        Args:
            efs (float):
        Returns:
            float: selectivity
        """
        # TODO search for selectivity in convolution
        destinations_total,=self.one('intopp/select_destinations_total')
        selectivity=-math.log(efs)/destinations_total
        self.do('intopp/update_od_selectivity',{'selectivity':selectivity*1000000})

        return selectivity

    # building specified number of rings which are written in the table "ring" containing following parameters,
    # which describe ring placement of a origin-destination point in the realtion to the second origin-destination point.
    # Function selects maximum value of distance from table distance then uses it to calculate a factor essential in rings creation.
    # In calculations maximum distance is multiplied by 1.0001 in order to move slightly the border of last ring so the furthest point in the network is included.
    # Table "ring" is filled using SQL script "insert_ring_uniform"
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def build_uniform_rings(self,no_of_rings,**kwargs):
        """
        build_uniform_rings builds specified in the no_of_rings parameter number of rings which are written in the table ring describing ring placement of a origin-destination point in the correlation to the second origin-destination point. Function selects maximum value of distance from table distance then uses it to calculate a factor essential in rings creation. During calculations maximum distance is multiplied by 1.0001 in order to move slightly the border of last ring so the furthest point in the network is included. Table ring is filled using SQL script insert_ring_uniform insert_ring_uniform.sql writes ring table using point and distance tables. insert_ring_uniform.sql script selects pairs of origin-destinations points from point table and matches them with corresponding ring, expressed as value of weight of distance between points multiplied by a factor calculated in the buid_uniform_rings fuction

        Args:
            no_of_rings (int): number of rings to build from one origin
        """

        self.do('intopp/create_ring')
        max_distance,=self.one('intopp/distance_maximum')
        factor=no_of_rings/(max_distance)
        self.do('intopp/insert_ring_uniform',{'factor':factor})
        # last ring must be no_of_rings-1 but through equation no_of_rings shall occur
        # We must update it
        self.merge_ring_with_next(no_of_rings)

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def build_weighted_rings(self,weight,**kwargs):
        """
        build_weighted_rings builds rings based on specified weight which are written in the table ring describing ring placement of a origin-destination point in the correlation to the second origin-destination point. Function selects given weight as a factor essential in rings creation. Table ring is filled using SQL script insert_ring_uniform insert_ring_weighted.sql writes ring table using point and distance tables. insert_ring_weighted.sql script selects pairs of origin-destinations points from point table and matches them with corresponding ring, expressed as the value of weight of distance between points divided by a factor calculated in the build_weighted_rings fuction

        Args:
            weight (float): rings separaded from each other by specified weight are created, weight parameter is expressed in the same units as distances betwwen points
        """
        self.do('intopp/create_ring')
        factor=weight
        self.do('intopp/insert_ring_weighted',{'factor':factor})

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def merge_ring_with_next(self, n, **kwargs):
        """
        merge_ring_with_next function merges next ring with ring with specified in function parameters number

        Args:
            n (int): number of ring which next ring will be merged into
        """
        self.do('intopp/update_ring_next', {'ring': n})

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def only_origin_in_first_ring(self, **kwargs):
        """
        only_origin_in_first_ring function moves points to the next ring if there's not empty set containing current element with distance greater than 0
        """
        self.do('intopp/update_origin_in_first_ring')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring_layout")
    def read_rings_layout(self,fixed_rings_layout=None,fixed_rings_name=None,**kwargs):
        """
        read_rings_layout either uses fixed_rings_layout given by the user in
        function parameters or loads the data from list od_properties table
        and prepares the table ring_layout necessary to create rings in specified layout

        Args:
            fixed_rings_layout (list<float>):
                example:
                [2.5,2.5,1,1,2,5,10,10]
            fixed_rings_name (sting)
                name of the field in od_properties table
        """
        self.do('intopp/create_ring_layout')
        #bag for future values
        rings_layout = []

        for od_id, layout_from_od_description in self.do('intopp/select_ring_layout',{"fixed_rings_name":fixed_rings_name}):
            # the vlue of layout for origin  we will insert
            layout_value=[]
            if layout:
                layout_value=layout
            else:
                layout_value=json.loads(layout_from_od_description)

            assert layout_value != None # TODO some more chceck and error handling required here

            prior_rings_sum=0
            for counter, value, in enumerate(layout_value):
                assert value >= 0 # TODO some more chceck and error handling required here
                rings_layout.append({
                    "od_id":od_id,
                    "ring_number":counter,
                    "ring_size":value,
                    "prior_rings_size": prior_rings_sum
                })
                prior_rings_sum+=value

        self.transaction('intopp/insert_ring_layout',rings_layout)

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def build_rings_from_layout(self,**kwargs):
        """
        build_rings_from_layout builds rings according to specified layout
        """
        self.do('intopp/create_ring')
        self.do('intopp/insert_ring_from_layout')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring")
    def snap_outstanding_od_to_last_ring(self,**kwargs):
        """
        null rings (assigned to od_id pairs in table ring) are given new number equal to maximum ring number + 1
        """
        self.do('intopp/insert_into_last_ring')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash()
    def get_max_distance(self,**kwargs):
        """
        Computes maximum distance in all distances

        Returns
            float: maximum distance
        """
        max_distance, = self.one('intopp/distance_maximum')
        return max_distance

    # creating table "ring_total" containing data on number of destinations located in specified ring and sum of all the destinations from rings prior to the described ring.
    # Table is filled by SQL script which uses tables "ring" and "model_parameters"
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("ring_total")
    def ring_total(self,**kwargs):
        """
        function "ring_total" creates table "ring_total" containing data on number of destinations located in specified ring and sum of all destiantions from rings prior to this ring
        :return: self
        """
        self.do('intopp/create_ring_total')
        self.do('intopp/insert_ring_total')

    # normalization of motion exchange. All the "objects" left in te network are set to be new 100% of network population
    # ("objects" that left the network in search for destinatons aren't included). SQL script "normalization" uses tables "motion_exchange_fraction" and creates helper table "temp_motion_exchange_fraction_total". Table "motion_exchange" is then updated with normalized values.
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("motion_exchange", "motion_exchange_fraction")
    def normalize_motion_exchange(self,**kwargs):
        """
        function "normalize_motion_exchange" normalizes motion exchange, setting all the objects left in the network to be the new 100% of netwok population
        SQL script "normalization" uses tables "motion_exchange_fraction" and creates helper table "temp_motion_exchange_fraction_total".
        Table "motion_exchange" is then updated with normalized values.
        """
        self.do('intopp/normalization')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def destination_shift(self,**kwargs):
        """
        destination_shift update destinations after motion exchange
        """
        self.do('intopp/destination_shift')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def general_shift(self,**kwargs):
        """
        general_shift updates both destinations and origins after motion exchange
        """
        self.do('intopp/general_shift')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("model_parameters")
    def origins_shift(self,**kwargs):
        """
        origins_shift
        """
        self.do('intopp/origins_shift')

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("od_properties")
    def save_intopp_parameters(self,suffix,**kwargs):
        """
        save_intopp_parameters allows user to update origins, destnations and selectivity names in od_parameters table with addition of specified suffix
        """
        self.do('intopp/save_parameters',{
            'origins_new_name':'origins'+suffix,
            'destinations_new_name':'destinations'+suffix,
            'selectivity_new_name':'selectivity'+suffix,
        })


    #calculating numbers of transported "objects". Results are written in the "motion_exchange" table, describing accurate quantity of transported "objects" and "motion_exchange_fraction" table, describing the same amounts in a form of fractions. Due to the model nature especially importatnt are fraction of "objects" which found destination in a chosen ring and fraction of "objects" which found destinations in the prior rings. "motion_exchange" function uses data stored in tables "ring", "ring_total" and "model_parameters".
    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("motion_exchange", "motion_exchange_fraction")
    def motion_exchange(self,**kwargs):
        """
        calculates numbers of transported "objects". Results ae written in the "motion_exchange" table. which describes accurate quantity of transported "objects"
        "motion_exchange_fraction" contains the same data in a different form - quantity of transported objects is expressed as a fraction.
        Due to the model nature especially importatnt are fraction of "objects" which found destination in a chosen ring and fraction of "objects" which found destinations in the prior rings.
        "motion_exchange" function uses data stored in tables "ring", "ring_total" and "model_parameters".
        """
        self.do('intopp/create_motion_exchange')

        featured_points=self.do('route/select_od_point').fetchall()
        expected_problem_size=len(featured_points)**2

        # creating a matrix which will be used to store created dictionaries and write 'motion_exchange' table in SQL
        motion_exchange=[]
        for start_id,\
            end_id,\
            ring,\
            destinations_in,\
            destinations_prior,\
            origins,\
            destinations,\
            selectivity,\
            conv_start,\
            conv_size,\
            conv_intensity in TaurusLongTask(\
                                self.do('intopp/select_for_motion_exchange'),\
                                max_value=expected_problem_size,\
                                additional_text='Intervening Opportunities',\
                                **kwargs\
                                ):

            # calculating fraction of all "objects" that found destinations prior to the currently chosen ring
            fraction_before_ring=self.convolution_mix(
                destinations_prior,
                selectivity/1000000.0,
                conv_start,
                conv_size,
                conv_intensity
            )

            # calculating fraction of "objects" that found destinations prior and in the currently chosen ring
            fraction_after_ring=self.convolution_mix(
                destinations_prior+destinations_in,
                selectivity/1000000.0,
                conv_start,
                conv_size,
                conv_intensity
            )
            if destinations_in!=0:
                fraction=(fraction_after_ring-fraction_before_ring)*destinations/destinations_in
            else:
                fraction=0

            motion_exchange.append({
                'od_start_id':start_id,
                'od_end_id':end_id,
                'fraction':fraction,
                'motion_exchange':(origins*fraction)
            })

            if len(motion_exchange)>10000:
                self.transaction('intopp/insert_motion_exchange',motion_exchange)
                self.transaction('intopp/insert_motion_exchange_fraction',motion_exchange)
                motion_exchange=[]

        self.transaction('intopp/insert_motion_exchange',motion_exchange)
        self.transaction('intopp/insert_motion_exchange_fraction',motion_exchange)
        self.commit()


    def convolution_cdf(self,destinations,selectivity,conv_a,conv_b):

        #For recursive calls
        if destinations<=0:
            return 0

        if conv_a<0:
            offset = self.convolution_cdf(-conv_a,selectivity,0,conv_b)

            return (self.convolution_cdf(destinations-conv_a,selectivity,0,conv_b)-offset)+\
                   (offset-self.convolution_cdf(-destinations-conv_a,selectivity,0,conv_b))
        # main integral part of convolution CDF

        #before or no convolution
        if destinations<=conv_a or conv_b==0:
            return 1.0 - math.exp(-selectivity*destinations)

        if destinations>conv_a and destinations<=conv_b+conv_a:
            return self.convolution_cdf(conv_a,selectivity,conv_a,conv_b)+\
                   (math.exp(-selectivity*(conv_a+destinations))*\
                         (math.exp(selectivity*destinations)*\
                          ((-conv_a*selectivity)+(destinations*selectivity)-1.0)+\
                          math.exp(conv_a*selectivity)))/(conv_b*selectivity)

        return self.convolution_cdf(conv_a+conv_b,selectivity,conv_a,conv_b)+\
               ((1.0-math.exp(conv_b*selectivity))*\
                    math.exp(-selectivity*(conv_a+conv_b+destinations))*\
                    (math.exp(selectivity*(conv_a+conv_b))-
                     math.exp(selectivity*destinations)))/(conv_b*selectivity)


    def convolution_mix(self,origins,selectivity,conv_a,conv_b,alpha):

        assert alpha>=0.0 and alpha<=1.0
        if alpha>0:
            return self.convolution_cdf(origins,selectivity,conv_a,conv_b)*alpha+\
                   self.convolution_cdf(origins,selectivity,0,0)*(1.0-alpha)
        return self.convolution_cdf(origins,selectivity,0,0)

    @init_kwargs_as_parameters
    @DataJournal.log_and_stash("od_properties")
    def save_model_parameters(self,parameter,saved_name,**kwargs):
        """
        save_model_parameters function allows the user to store data on model parameters in a dictionary and update od_properties table with new values of specified by the user parameter
        """
        model_parameters=[{
            "od_id":t[0],
            "origins":t[1],
            "destinations":t[2],
            "selectivity":t[3],
            "convolution_start":t[4],
            "convolution_size":t[5],
            "convolution_intensity":t[6]
        } for t in self.do('intopp/select_model_parameters').fetchall()]

        assert parameter in model_parameters[0].keys()

        self.do('initial/clean_value',{'name':saved_name,"new_name":saved_name})

        new_value = [{
            "od_id": parameters['od_id'],
            "name": saved_name,
            "value": parameters[parameter]
        } for parameters in model_parameters]

        self.transaction('initial/update_od_values',new_value)
