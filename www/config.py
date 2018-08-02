# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import config_default

class Dict(dict):
	'''
	支持形如x.y格式的dict
	'''
	def __init__(self, names=(), values=(), **kw):
		super().__init__(**kw)
		'''
		zip([iterable, ...]) - This function returns a list of tuples, where the i-th tuple contains 
		the i-th element from each of the argument sequences or iterables. 
		The returned list is truncated in length to the length of the shortest argument sequence. 
		When there are multiple arguments which are all of the same length, zip() is similar to map() 
		with an initial argument of None. With a single sequence argument, it returns a list of 1-tuples. 
		With no arguments, it returns an empty list.
		'''
		for k, v in zip(names, values):
			self[k] = v

	def __getattr__(self, key):
		try:
			pass
			return self[key]
		except:
			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

def merge(defaults, override):
	'''
	合并两个dict
	:defaults:dict
	:override:dict
	:return:dict
	'''
	r = {}
	for k, v in defaults.items():
		if k in override:
			if isinstance(v, dict):
				r[k] = merge(v, override[k])
			else:
				r[k] = override[k]
		else:
			r[k] = v
	return r

def toDict(d):
	'''
	将dict转化为Dict
	:d:dict
	:return:Dict
	'''
	D = Dict()
	for k, v in d.items():
		D[k] = toDict(v) if isinstance(v, dict) else v
	return D

configs = config_default.configs

try:
	import config_override
	configs = merge(configs, config_override.configs)
except ImportError:
	pass

configs = toDict(configs)