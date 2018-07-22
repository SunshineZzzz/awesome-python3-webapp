# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import json, logging, inspect, functools

class APIError(Exception):
	'''
	基础的APIError，包含错误类型(必要)，数据(可选)，信息(可选)
	'''
	def __init__(self, error, data='', message=''):
		super().__init__(message)
		self.error = error
		self.data = data
		self.message

class APIValueError(APIError):
	'''
	表明输入数据有问题，data说明输入的错误字段
	'''
	def __init__(self, field, message=''):
		super().__init__('value:invalid', field, message)

class APIResourceNotfoundError(APIError):
	'''
	表明找不到资源，data说明资源名字
	'''
	def __init__(self, field, message=''):
		super().__init__('value:not found', field, message)

class APIPermissionError(APIError):
	'''
	接口没有权限
	'''
	def __init__(self, message=''):
		super().__init__('permission:forbidden', 'permission', message)