#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

from .sqlite_database import SQLiteDatabase
from .importer import Importer
from .utils import init_kwargs_as_parameters
from itertools import accumulate
import cmath

class NetworkGenerator(Importer):

    def __init__(self,**kwargs):
        super().__init__(**kwargs)

    # adding new rows to tables: network_geometry and network_properties, these new rows contain data on specified segments connecting points in the network
    def _addel(self,element,elementrel,net_geometry_to_insert,net_data_to_insert,value=1):
        """
        function "addel" adds new rows to tables: network_geometry and network_properties,
        these new rows contain data on specified segments connecting points in the network
        :param element:
        :param elementrel:
        :param net_geometry_to_insert:
        :param net_data_to_insert:
        :param value:
        :return:
        """
        start=[element.real,element.imag]
        end=[elementrel.real,elementrel.imag]
        net_geometry_to_insert.append({
            'start':str(start),
            'end':str(end),
            'linestring':str([start,end])
        })
        net_data_to_insert.append({
            'start':str(start),
            'end':str(end),
            'name':'weight',
            'value':value
        })
    # normalization brings numbers of origins and destinations to a fractional form, new sums of origins and ddestinations equal 1
    def _normalize(self,points_with_data):
        """
        normalization brings numbers of origins and destinations to a fractional forms, new sums of origins and destinations equal 1
        :param points_with_data:
        :return:
        """
        dtotal=sum([point['data']['destinations'] for point in points_with_data])
        stotal=sum([point['data']['origins'] for point in points_with_data])
        for i,point in enumerate(points_with_data):
            points_with_data[i]['data']['destinations']/=dtotal
            points_with_data[i]['data']['origins']/=stotal

    # preparing points data stored in the dictionary 'points_with_data' to be inserted in the "od_geometry" (columns 'od_id' - identificational number of a origin-destination point and 'geometry' - coordinates of the point) and "od_properties" (columns 'od_id' -   identificational number of a origin-destination point, 'name' - name of a parameter describing that point and 'value' - value of the parameter) tables. The construction of "od_properties" table allows later to add new parameters to specific points without creating new columns
    def _insert_points(self,points_with_data):
        # prepare data to insert to database
        """
        function "_insert_points" prepares point data in the dictionary 'points_with_data' to be inserted in the "od_geometry" and "od_properties" tables.
        The construction of "od_properties" table allows later to add new parameters to specific points without creating new columns
        :param points_with_data:
        :return:
        """
        od_geometry_to_insert=[{
            'od_id':p['data']['od_id'],
            'point':str(p['geometry'])
        } for p in points_with_data]

        od_data_to_insert=[]
        for p in points_with_data:
            od_data_to_insert.append({
                'od_id':p['data']['od_id'],
                'name':'destinations',
                'value':p['data']['destinations']
            })
            od_data_to_insert.append({
                'od_id':p['data']['od_id'],
                'name':'origins',
                'value':p['data']['origins']
            })

        # running SQL scripts filling existing tables with the data created earlier
        self.transaction('initial/import_od_geometry',od_geometry_to_insert)
        self.transaction('initial/import_od_properties',od_data_to_insert)

    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_hexhorny_pattern_network(self,size,delta=0.0001,**kwargs):

        self.do('initial/create_network')
        self.do('initial/create_od')

        rows=[]
        vector=cmath.rect(1,cmath.pi/3)
        p=complex(0,0)
        rows.append([[p]])
        ring_generator=p
        for ring in range(size):
            r=[]
            ring_generator+=complex(1,0)
            for prt in range(6):
                prtl=[]
                for e in range(ring+1):
                    point=(ring_generator*vector**prt+vector*vector*e*vector**prt)*delta
                    prtl.append(point)

                r.append(prtl)
            rows.append(r)
        #ring generator at last ring init point
        to_delete_size=len(rows[-1][0])-1
        to_delete_offset=1
        for ringnumber,ring in enumerate(reversed(rows)):
            for prt_nb,prt in enumerate(ring):
                if to_delete_size>0:
                    ring[prt_nb]=ring[prt_nb][:to_delete_offset]+ring[prt_nb][to_delete_offset+to_delete_size:]
            to_delete_offset+=1
            to_delete_size-=3

        points=[]
        for row in rows:
            for part in row:
                for point in part:
                    points.append(point)


        # Let add some data to geometries
        points_with_data= [{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        net_geometry_to_insert=[]
        net_data_to_insert=[]

        for i,r in enumerate(rows):
            if i==0:
                continue
            for j,part in enumerate(r):
                for k,element in enumerate(part):
                    if ((size*2)//3)>=i:
                        # connections in row
                        if k==0:
                            self._addel(rows[i][j][k],rows[i][j-1][-1],net_geometry_to_insert,net_data_to_insert)
                            self._addel(rows[i][j-1][-1],rows[i][j][k],net_geometry_to_insert,net_data_to_insert)
                        else:
                            self._addel(rows[i][j][k],rows[i][j][k-1],net_geometry_to_insert,net_data_to_insert)
                            self._addel(rows[i][j][k-1],rows[i][j][k],net_geometry_to_insert,net_data_to_insert)

                    if i-1==0:
                        # connections to 00
                        self._addel(rows[i][j][k],rows[i-1][0][0],net_geometry_to_insert,net_data_to_insert)
                        self._addel(rows[i-1][0][0],rows[i][j][k],net_geometry_to_insert,net_data_to_insert)
                    elif (len(part)/2)>k and i>1:
                        self._addel(rows[i][j][k],rows[i-1][j][k],net_geometry_to_insert,net_data_to_insert)
                        self._addel(rows[i-1][j][k],rows[i][j][k],net_geometry_to_insert,net_data_to_insert)
                    elif len(part)/2<k and i>1:
                        l=len(part)-k
                        self._addel(rows[i][j][k],rows[i-1][j][-l],net_geometry_to_insert,net_data_to_insert)
                        self._addel(rows[i-1][j][-l],rows[i][j][k],net_geometry_to_insert,net_data_to_insert)
                    else:
                        pass

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()


    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_trianglehex_pattern_network(self,size,delta=0.0001,**kwargs):

        self.do('initial/create_network')
        self.do('initial/create_od')


        rows=[]
        vector=cmath.rect(1,cmath.pi/3)
        p=complex(0,0)
        rows.append([[p]])
        ring_generator=p
        for ring in range(size):
            r=[]
            ring_generator+=complex(1,0)
            for prt in range(6):
                prtl=[]
                for e in range(ring+1):
                    point=(ring_generator*vector**prt+vector*vector*e*vector**prt)*delta
                    prtl.append(point)

                r.append(prtl)
            rows.append(r)

        points=[]
        for row in rows:
            for part in row:
                for point in part:
                    points.append(point)

        # Let add some data to geometries
        points_with_data= [{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        net_geometry_to_insert=[]
        net_data_to_insert=[]

        for p1 in points:
            for p2 in points:
                if p1!=p2 and abs(p1-p2)<delta*1.1:
                    self._addel(p1,p2,net_geometry_to_insert,net_data_to_insert)

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()

    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_hexdiagonal_pattern_network(self,size,delta=0.0001,**kwargs):

        self.do('initial/create_network')
        self.do('initial/create_od')


        rows=[]
        vector=cmath.rect(1,cmath.pi/3)
        p=complex(0,0)
        row_generator=p
        additional=0
        for r_no in range(size*4+1):
            r=[]
            for e in range(size*2+additional+1):
                point=(row_generator+(e)*complex(1,0))*delta
                r.append(point)
            rows.append(r)
            if r_no < size*2:
                additional+=1
                row_generator+=vector**2
            else:
                additional-=1
                row_generator+=vector

        #reget points
        points=[]
        for row in rows:
            for point in row:
                points.append(point)

        # Let add some data to geometries
        points_with_data=[{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        net_geometry_to_insert=[]
        net_data_to_insert=[]
        def add_edge_possibility(rows,old_row,old_elemet,new_row,new_element):
            if new_row>=0 and new_row<len(rows) and new_element>=0 and new_element<len(rows[new_row]):
                if abs(rows[old_row][old_elemet]-rows[new_row][new_element])>delta*1.1:
                    self._addel(
                        rows[old_row][old_elemet],
                        rows[new_row][new_element],
                        net_geometry_to_insert,
                        net_data_to_insert,
                        (3**0.5)/2)
                else:
                    self._addel(
                        rows[old_row][old_elemet],
                        rows[new_row][new_element],
                        net_geometry_to_insert,
                        net_data_to_insert)

        for i,r in enumerate(rows):
            downo=-1
            upo=-1
            if i<len(rows)//2:
                upo=1
            if i>len(rows)//2:
                downo=1

            for j,element in enumerate(r):

                if i%2==0 and j%2==1:
                    add_edge_possibility(rows,i,j,i+2,j+upo)
                    add_edge_possibility(rows,i,j,i-2,j+downo)
                    add_edge_possibility(rows,i,j,i,j+1)
                    add_edge_possibility(rows,i,j,i,j-1)

                if (i<len(rows)//2 and i%2!=0 and j%2!=0) or \
                    (i>len(rows)//2 and i%2!=0 and j%2==0):
                    add_edge_possibility(rows,i,j,i+1,j+(upo+1)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo-1)//2)
                    add_edge_possibility(rows,i,j,i+1,j+(upo-3)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo+3)//2)

                if (i<len(rows)//2 and i%2!=0 and j%2==0) or \
                    (i>len(rows)//2 and i%2!=0 and j%2!=0):
                    add_edge_possibility(rows,i,j,i+1,j+(upo-1)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo+1)//2)
                    add_edge_possibility(rows,i,j,i+1,j+(upo+3)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo-3)//2)

                if i%2==0 and j%2==0:
                    add_edge_possibility(rows,i,j,i+2,j+upo)
                    add_edge_possibility(rows,i,j,i-2,j+downo)
                    add_edge_possibility(rows,i,j,i,j+1)
                    add_edge_possibility(rows,i,j,i,j-1)

                    add_edge_possibility(rows,i,j,i+1,j+(upo-1)//2)
                    add_edge_possibility(rows,i,j,i+1,j+(upo-3)//2)
                    add_edge_possibility(rows,i,j,i+1,j+(upo+1)//2)
                    add_edge_possibility(rows,i,j,i+1,j+(upo+3)//2)

                    add_edge_possibility(rows,i,j,i-1,j+(downo-1)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo-3)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo+1)//2)
                    add_edge_possibility(rows,i,j,i-1,j+(downo+3)//2)

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()



    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_hex_pattern_network(self,size,delta=0.0001,**kwargs):
        '''
        Creates hexagonal pattern network. HEXAGONS binded together by edge (like square pattern but with hexagons)
        Creates also corresponding origins - destinations points.
        origins - destinations are set in way their total sum is 1 for origins and destinations.
        Points for abstract network are generated in WSG84 coordinate system starting at point (0,0).
        On this level we use globe WSG84 as a Carthesian coordinates system.
        Don't use it for

        :param size: How many lines to create on side. 1 by 1 lines create just a hexagon with point inside.
        :param delta: Network relative (to earth WSG84) size.
        :return:
        '''
        self.do('initial/create_network')
        self.do('initial/create_od')

        # main Point generator part

        points=[]
        rows=[]

        vector=cmath.rect(1,cmath.pi/6)
        p=complex(0,0)
        row_generator=p
        k_top=size
        for row in range(size+1):
            r=[]
            vector=vector.conjugate()
            if row==size and size%2==0:
                row_generator+=vector
                vector=vector.conjugate()
                k_top-=1
            r.append(row_generator*delta)
            for e in range(k_top):
                point=(row_generator+e*(vector.conjugate()+vector)+vector)*delta
                r.append(point)
                point=(row_generator+(e+1)*(vector.conjugate()+vector))*delta
                r.append(point)

            rows.append(r)
            row_generator+=complex(0,1)*(1+row%2)

        for row in rows:
            for point in row:
                    points.append(point)

        # Let add some data to geometries
        points_with_data=[{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        net_geometry_to_insert=[]
        net_data_to_insert=[]

        for p1 in points:
            for p2 in points:
                if p1!=p2 and abs(p1-p2)<delta*1.1:
                    self._addel(p1,p2,net_geometry_to_insert,net_data_to_insert)

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()

    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_square_pattern_network(self,size,delta=0.0001,**kwargs):
        '''
        Creates square pattern network.
        Coresponding origins - destinations points are also created.
        origins - destinations are set in way their total sum is 1 for origins and destinations.
        Points for abstract network are generated in WSG84 coordinate system starting at point (0,0).
        On this level we use globe WSG84 as a Carthesian coordinates system.
        Don't use it for

        :param size: How many lines to create. 1 by 1 lines create just a square.
        :param delta: Network relative (to earth WSG84) size.
        :return:
        '''
        self.do('initial/create_network')
        self.do('initial/create_od')

        # main Point generator part

        points=[]
        rows=[]
        for y in range(size+1):
            row=[]
            for x in range(size+1):
                point=complex(x*delta,y*delta)
                row.append(point)
                points.append(point)
            rows.append(row)

        # Let add some data to geometries
        points_with_data=[{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        # Creating network. Data from the matrix created earlier is prepared to be written in the "network_geometry" and "network_properties" tables by being written into net_geometry_to_insert and net_data_to_insert tables. Then SQL scripts use the prepared data to insert it in the network_geometry" and "network_properties" tables.
        net_geometry_to_insert=[]
        net_data_to_insert=[]

        for y,row in enumerate(rows):
            for x,element in enumerate(row):
                if y!=0:
                    self._addel(element,rows[y-1][x],net_geometry_to_insert,net_data_to_insert)
                if y!=len(rows)-1:
                    self._addel(element,rows[y+1][x],net_geometry_to_insert,net_data_to_insert)
                if x!=0:
                    self._addel(element,rows[y][x-1],net_geometry_to_insert,net_data_to_insert)
                if x!=len(row)-1:
                    self._addel(element,rows[y][x+1],net_geometry_to_insert,net_data_to_insert)

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()

    @init_kwargs_as_parameters
    @Importer.log_and_stash("network_properties", "network_geometry")
    def make_trihexhex_pattern_network(self,size,delta=0.0001,**kwargs):
        '''
        Creates trihexhex pattern network.
        mede out of tri-hexagons layers round tri-hexagon
        Coresponding origins - destinations points are also created.
        origins - destinations are set in way their total sum is 1 for origins and destinations.
        Points for abstract network are generated in WSG84 coordinate system starting at point (0,0).
        On this level we use globe WSG84 as a Carthesian coordinates system.
        Don't use it for

        :param size: How many layers to create. 1 by 1 lines create just a square.
        :param delta: Network relative (to earth WSG84) size.
        :return:
        '''
        self.do('initial/create_network')
        self.do('initial/create_od')

        # main Point generator part
        points=[]
        rows=[]
        vector=cmath.rect(1,cmath.pi/6) # single vector of 1/12 circle
        v=vector
        vcon=v.conjugate()

        p=complex(0,0)
        row_generator=p
        k_top=size

        points.append(p)


        row_starting_point=[1]
        row_starting_point+=[2,1]*size
        row_starting_point=list(accumulate(row_starting_point))
        row_starting_point=[(-vcon)*i for i in row_starting_point]

        row_type=[1]
        row_type+=[(i+1)*3+1 for i in range(size)]
        row_type+=list(reversed([1-(i+1)*3 for i in range(size)]))
        row_type=list(reversed(row_type))

        row_generator=[3]*(size+1) # not a point
        row_generator[0]-=1
        row_generator[-1]-=1
        row_generator=list(accumulate(row_generator))
        row_generator=[(-vcon)*i for i in row_generator]

        for rg_i,rg in enumerate(row_generator):
            rg=rg+complex(0,1)
            r=rg
            row=[r]
            u,d = v,v.conjugate()
            if row_type[rg_i]<0:
                u,d=d,u
            for i in range(abs(row_type[rg_i])):
                r+=u
                row.append(r)
                r+=d
                row.append(r)

            rows.append(row)
        del(row_type[0:len(row_generator)])
        u,d = v,v.conjugate()
        for rt in row_type:
            rg+=3*v
            r=rg
            row=[r]
            for i in range(rt):
                r+=u
                row.append(r)
                r+=d
                row.append(r)
            rows.append(row)


        for turn in [1,v**4,v**8]:
            for row in rows:
                for point in row:
                    points.append(turn*point*delta)
            for point in row_starting_point:
                points.append(turn*point*delta)

        # Let add some data to geometries
        points_with_data=[{
            'geometry':[point.real,point.imag],
            'data':{
                'od_id':i,
                'origins':1,
                'destinations':1
            }
        } for i,point in enumerate(points)]

        # Data normalization
        self._normalize(points_with_data)

        #insert
        self._insert_points(points_with_data)

        # Creating network. Data from the matrix created earlier is prepared to be written in the "network_geometry" and "network_properties" tables by being written into net_geometry_to_insert and net_data_to_insert tables. Then SQL scripts use the prepared data to insert it in the network_geometry" and "network_properties" tables.
        net_geometry_to_insert=[]
        net_data_to_insert=[]

        for p1 in points:
            for p2 in points:
                if p1!=p2 and abs(p1-p2)<delta*1.1:
                    self._addel(p1,p2,net_geometry_to_insert,net_data_to_insert)

        self.transaction('initial/import_network_geometry',net_geometry_to_insert)
        self.transaction('initial/import_network_properties',net_data_to_insert)
        self.point_from_network_od()
