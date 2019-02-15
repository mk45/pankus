#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import sqlite3
import pkg_resources
#from .taurus_leaf import TaurusLeaf
from .utils import init_kwargs_as_parameters

class SQLiteDatabase:

    def __init__(self,database_name='taurus.db',**kwargs):
        super().__init__()
        self.db_connection=sqlite3.connect(database_name)

    def execute(self,**kwargs):
        return self.db_connection.execute(**kwargs)

    def get_sql_form_file(self,script_name):
        #print(pkg_resources,__name__)
        return pkg_resources.resource_stream(__name__,'SQL/'+script_name+'.sql').read().decode('ascii')

    def build_sql(self,script_string,args={}):
        return script_string.format(**args)


    def commit(self):
        self.db_connection.commit()

    def one(self,script_name,args={}):
        cursor=self.do(script_name,args)
        if cursor:
            return cursor.fetchone()

    def transaction(self,script_name,data):
        sql_string=self.get_sql_form_file(script_name)
        assert hasattr(data,'__iter__')

        self.db_connection.executemany(sql_string,data)
        self.commit()

    def do(self,script_name,args={}):
        '''
        script contains ; is script and executed without output
        script without ; is for fetching output

        :param script_name:
        :param args:
        :return:
        '''
        sql_string=self.get_sql_form_file(script_name)
        if ';' not in sql_string:
            c=self.db_connection.execute(sql_string,args)
            self.commit()
            return c
        elif ':' in sql_string:
            query_list=sql_string.split(';')
            for query in query_list:
                self.db_connection.execute(query,args)
                self.commit()
        else:
            self.db_connection.executescript(sql_string)
            self.commit()


    def table_exists(self,dataset_name):
        c=self.db_connection.cursor()
        return not c.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
            [dataset_name]).fetchone()[0]==0
