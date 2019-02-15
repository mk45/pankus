#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pankus import __version__, __authors__

from .sqlite_database import SQLiteDatabase
import time
import csv
from .utils import init_kwargs_as_parameters
from functools import wraps

class DataJournal(SQLiteDatabase):

    def __init__(self,use_data_stash=False,parent_action_uid=None,**kwargs):
        super().__init__(**kwargs)
        self.parent_action_uid=parent_action_uid
        self.do('datajournal/create_model_log') if not self.table_exists('model_log') else False
        self.do('datajournal/create_data_stash') if not self.table_exists('data_stash') else False

    @staticmethod
    def logged_function(function):
        @wraps(function)
        def wrapper(self,*args,**kwargs):
            parameter_list=[str(argg) for argg in args]
            parameter_list.extend([str(key)+'='+str(kwargs[key]) for key in list(kwargs.keys())])
            action=str(function.__name__)+"("+", ".join(parameter_list)+")"
            version=__version__
            action_uid=self.get_action_uid()
            datetime=time.time()
            out=function(self,*args, **kwargs)
            self.do('datajournal/insert_model_log',{
                                                'action_uid':action_uid,
                                                'action':action,
                                                'datetime':datetime,
                                                'p_action_uid':self.parent_action_uid,
                                                'version':version})
            self.parent_action_uid=action_uid
            return out
        return wrapper

    def get_action_uid(self):
        return self.one('datajournal/get_next_action_uid')[0]

    @staticmethod
    def data_stash(table_name):
        def data_deco(function):
            @wraps(function)
            def wrapper(self,*args,use_data_stash=False,**kwargs):
                out=function(self,*args,use_data_stash=use_data_stash,**kwargs)
                if use_data_stash:
                    assert ";" not in table_name
                    assert len(table_name)<30
                    cursor=self.db_connection.execute("SELECT * FROM "+table_name)
                    names = [description[0] for description in cursor.description]
                    header=','.join(names)
                    data=[str(row)[1:-1] for row in cursor]
                    csv=header+"\n"+"\n".join(data)
                    self.do('datajournal/insert_data_stash',{
                                                        'action_uid':self.parent_action_uid,
                                                        'table_name':table_name,
                                                        'csv':csv})
                return out
            return wrapper
        return data_deco

    @staticmethod
    def log_and_stash(*args_general):
        def real_decorator(function):
            @wraps(function)
            def wrapper(self,*args,use_data_stash=False,**kwargs):
                function2=DataJournal.logged_function(function)
                if use_data_stash:
                    for arg in args_general:
                        function2=(DataJournal.data_stash(arg))(function2)
                return function2(self,*args,use_data_stash=use_data_stash,**kwargs)
            return wrapper
        return real_decorator
