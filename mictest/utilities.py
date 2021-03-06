'''
Brian Gravelle

useful stuff for processing mictest data in the python notebooks here
'''




################################################################################################################

#                                                    Imports

################################################################################################################


import os
from os import listdir
from os.path import isfile, join

import sys

try:
    import taucmdr
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['__TAUCMDR_HOME__'], 'packages'))
finally:
    from taucmdr.model.project import Project
    from taucmdr.data.tau_trial_data import TauTrialProfileData

import matplotlib
import matplotlib.pyplot as plt
matplotlib.style.use('ggplot')
font = {'weight' : 'bold',
        'size'   : 24
}
matplotlib.rc('font', **font)

import pandas as pd
import math
import numpy as np
import operator
import time
import re
import collections
import seaborn as sns
# for fancy tables
from IPython.core.display import display, HTML, display_html





################################################################################################################

#                                   retrieving data from profiles

################################################################################################################



#TODO add params so this is a real function
def get_pandas_non_summary():
    '''
    returns a dictionary of pandas
    keys are the metrics that each panda has data for
    vals are the pandas that have the data organized however they organzed it
    DEPRECATED - may not work
    '''
    num_trials = Project.selected().experiment().num_trials
    trials = Project.selected().experiment().trials(xrange(0, num_trials))
    trial_data = {}
    for i in xrange(0, num_trials):
        trial_data[i] = trials[i].get_data()
        
    start = time.time()
    metric_data = {}

    for trial in xrange(0, num_trials):
        thread_data = []
        for i in xrange(0, len(trial_data[trial])):
            for j in xrange(0, len(trial_data[trial][i])):
                for k in xrange(0, len(trial_data[trial][i][j])):
                    thread_data.append(trial_data[trial][i][j][k].interval_data())
                    metric_data[trial_data[trial][i][j][k].metric] = pd.concat(thread_data)
                    metric_data[trial_data[trial][i][j][k].metric].index.names = ['trial', 'rank', 'context', 'thread', 'region']
        
    end = time.time()
    
    print('Time spent constructing dataframes %s' %(end-start))
    print('\nMetrics included:')
    for m in metric_data.keys():
        print("\t%s"%m)
    
    return metric_data

def load_perf_data(application,experiment,nolibs=False):
    '''
        Return a Pandas dictionary from data in the detault path
    '''
    path = ".tau/" + application + "/" + experiment + "/"
    if not os.path.exists(path):
        sys.exit("Error: invalid data path: %s" % path)
    metric_dict = get_pandas(path = ".tau/" + application + "/" + experiment + "/")
    if nolibs:
        filtered_dict = {}
        for k,v in metric_dict.items():
            if k == 'METADATA': filtered_dict[k] = metric_dict[k]
            else: filtered_dict[k] = filter_libs_out(metric_dict[k])
        return filtered_dict
    else:
        return metric_dict

def get_pandas(path):
    '''
    returns a dictionary of pandas
        - keys are the metrics that each panda has data for
    params
        - path is the path to 
    vals are the pandas that have the data organized however they organzed it
        - samples are turned into summaries
        - tau cmdr must be installed and .tau with the relevant data must be in this dir
    '''
    if not os.path.exists(path):
        sys.exit("Error: invalid data path: %s" % path)
    metric_data = {}
    
    paths = [path+n+'/' for n in listdir(path) if (not isfile(join(path, n)))]
    num_trials = len(paths)
    #files = [f for f in listdir(path) if not isfile(join(p, f))]
    for p in paths:
        d = [f for f in listdir(p) if (not isfile(join(p, f))) and (not (f == 'MULTI__TIME'))]
        prof_data = TauTrialProfileData.parse(p+'/'+d[0])
        time_data = TauTrialProfileData.parse(p+'/MULTI__TIME')
        prof_data.metadata = time_data.metadata
        metric = prof_data.metric
        metric_data[metric] = prof_data.summarize_samples()
        metric_data[metric].index.names = ['rank', 'context', 'thread', 'region']
        metric_data['METADATA'] = prof_data.metadata
    return metric_data

def get_pandas_scaling(path):
    '''
    returns a dictionary of pandas
    keys are the metrics that each panda has data for
    vals are the pandas that have the data organized however they organzed it
        - samples are turned into summaries
        - tau cmdr must be installed and .tau with the relevant data must be in this dir
    '''
    
    metric_data = {}
    
    paths = [path+n+'/' for n in listdir(path) if (not isfile(join(path, n)))]
    num_trials = len(paths)
    #files = [f for f in listdir(path) if not isfile(join(p, f))]
    for p in paths:
        d = [f for f in listdir(p) if (not isfile(join(p, f))) and (not (f == 'MULTI__TIME'))]
        trial_dir = p+'/'+d[0]
        prof_data = TauTrialProfileData.parse(trial_dir)
        metric = prof_data.metric

        prof_list = [f for f in listdir(trial_dir)]
        num_treads = len(prof_list)
        try:
            metric_data[num_treads][metric] = prof_data.summarize_samples()
            metric_data[num_treads][metric].index.names = ['rank', 'context', 'thread', 'region']
        except:
            metric_data[num_treads] = {}
            metric_data[num_treads][metric] = prof_data.summarize_samples()
            metric_data[num_treads][metric].index.names = ['rank', 'context', 'thread', 'region']

    return metric_data




################################################################################################################

#                                   Printing and plotting data

################################################################################################################


def print_metadata(data):
    
    for key in data['METADATA']:
        print('{:50} {}'.format(key,data['METADATA'][key] ))


def print_available_metrics(data):
    
    for key in data:
        if not key == 'METADATA':
            print(key)

def set_chart_font_size(fntsize):
    font = {'size'   : fntsize}; matplotlib.rc('font', **font)

def bar_chart(dfs,x='region',y='Inclusive',size=(15,7)):
    fig, ax = plt.subplots(figsize=size)
    dfs.plot(ax = ax, kind='bar')
    return fig


################################################################################################################

#                                   Hotspots and related filtering functions

################################################################################################################




def filter_libs_out(dfs):
    dfs_filtered = dfs.groupby(level='region').filter(lambda x: not (x.name == '.TAU application') and ('tbb' not in x.name) and ('syscall' not in x.name)  and ('std::' not in x.name))
    return dfs_filtered

def largest_stddev(dfs,n):
    return dfs['Exclusive'].groupby(level=region).std(ddof=0).dropna().sort_values(ascending=False, axis=0)[:n]

def largest_correlation(dfs,n):
    unstacked_dfs = dfs.unstack(region)
    return unstacked_dfs.loc[:,'Exclusive'].corrwith(unstacked_dfs.loc[:,('Inclusive','.TAU application')]).sort_values(ascending=False, axis=0)[:n]

def largest_exclusive(dfs,n):
    return dfs['Exclusive'].groupby(level='region').max().nlargest(n)

def largest_inclusive(dfs,n):
    return dfs['Inclusive'].groupby(level='region').max().nlargest(n)

def means(dfs, inclusive=True, sort=True, plot=False):
    if inclusive: which='Inclusive'
    else: which='Exclusive'
    temp = dfs.groupby('region')[which].sum().reset_index().groupby('region').mean()
    if sort: temp = temp.sort_values(by=which,ascending=False)
    if plot: bar_chart(temp)
    return temp

def thread_stddev(dfs, inclusive=True, sort=True, plot=False):
    if inclusive: which='Inclusive'
    else: which='Exclusive'
    temp = dfs.groupby(['thread','region'])[which].sum().reset_index().groupby(['thread']).std()
    if plot: bar_chart(temp)
    if sort: return temp.sort_values(by=which,ascending=False)
    else: return temp

def hotspots(dfs, n, flag):
    if flag == 0:
        largest = largest_exclusive(dfs,n)
    elif flag == 1:
        largest = largest_inclusive(dfs,n)
    elif flag == 2:
        largest = largest_stddev(dfs,n)
    elif flag == 3:
        largest = largest_correlation(dfs,n)
    else:
        print('Invalid flag')
    y = ['exclusive time', 'inclusive time', 'standard deviation', 'correlation to total runtime']
    print('Hotspot Analysis Summary')
    print('='*80)
    print('The code regions with largest %s are: ' %y[flag])
    for i in xrange(0,n):
        try:
            print('%s: %s (%s)' %(i+1, largest.index[i], largest[i]))
        except:
            break

def get_hotspots(metric,n=10):
    print('selected metric: %s\n' %metric)
    hotspots(expr_intervals[metric], n, 1)
    
    print('='*80)
    
    filtered_dfs = filter_libs_out(expr_intervals[metric])
    hotspots(filtered_dfs, n, 1)


################################################################################################################

#                                   Stuff that was supposed to print prety tables

################################################################################################################

# UTILITIES (NOT WORKING)
# TODO make this work

# using something like head() in panda will probably be better
# or to_html()
# This is where useful functions go. Currently includes:

# table printing

# from IPython.core.display import display, HTML, display_html

# def parse_region(region):
#     _location_re = re.compile(r'\{(.*)\} {(\d+),(\d+)}-{(\d+),(\d+)}')
#     func = region.split('=>')[-1]
#     loc = re.search(r'\[(.*)\]', func)
#     if loc:
#         location = loc.group(1)
#         match = _location_re.match(location)
#         if match:
#             return match.group(1)
#     if '[SAMPLE]' in func:
#         loc = re.search(r'\[\{(.*)\} \{(\d+)\}\]', func)
#         if loc:
#             return loc.group(1)

# def add_link(multiindex):
#     link = parse_region(multiindex[4])
#     if link:
#         return (multiindex[0],multiindex[1],multiindex[2],multiindex[3],'<a href="{0}">{1}</a>'.format((link), multiindex[4]))
#     else:
#         return multiindex

    
# def print_table(intervals):
#     '''
#     intervals is a panda with a metric's data
#     '''
#     expr_intervals_link = intervals.copy()
#     expr_intervals_link.index = expr_intervals_link.index.map(lambda x: add_link(x))
#     HTML(expr_intervals_link.to_html(escape=False))

    
# metric='PAPI_TOT_CYC'
# print_table(expr_intervals[metric])
# expr_intervals_link = expr_intervals[metric].copy()
# expr_intervals_link.index = expr_intervals_link.index.map(lambda x: add_link(x))
# HTML(expr_intervals_link.to_html(escape=False))
