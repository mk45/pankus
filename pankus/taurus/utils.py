#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'Maciej Kamiński Politechnika Wrocławska'

import progressbar as pb
from functools import wraps

class TaurusLongTask:

    def __init__(self,iterable,
                    progressbar=True,
                    max_value=pb.UnknownLength,
                    additional_text='',
                    **kwargs):
        self.iterator=iter(iterable)
        self.if_progressbar=progressbar
        if hasattr(iterable, '__len__'):
            self.max_value=len(iterable)
        else:
            self.max_value=max_value
        self.additional_text=additional_text
        self.bar_widgets=[ \
                            additional_text+' [', pb.Timer(), '] ', \
                            pb.Bar(), \
                            ' (', pb.ETA(), ') ', \
                        ]

    def __iter__(self):
        if self.if_progressbar:
            self.bar=pb.ProgressBar(\
                max_value=self.max_value,\
                widgets=self.bar_widgets,\
            )
            return self
        return self.iterator

    def __next__(self):
        try:
            element = self.iterator.__next__()
            self.bar.update(self.bar.value+1)
            return element
        except Exception as error:
            self.bar.finish()
            raise error

def init_kwargs_as_parameters(function):
    @wraps(function)
    def wrapper(self,*args,**kwargs):
        return function(self,*args,**{**self.kwargs,**kwargs})
    return wrapper
