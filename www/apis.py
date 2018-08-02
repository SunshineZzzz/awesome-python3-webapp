# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import json, logging, inspect, functools

class Page(object):
	'''
	分页管理器
	:item_count:总数量
	:page_size:每页显示数量
	:page_count:总页数
	:offset:用于limit语句中的offset
	:limit:用于limit语句中的offset,limit
	:page_index:当前页
	:has_next:是否有一下一页
	:has_previous:是否有上一页
	'''
	def __init__(self, item_count, page_index = 1, page_size = 10):
		self.item_count = item_count
		self.page_size = page_size
		self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
		if (item_count == 0) or (page_index > self.page_count):
			self.offset = 0
			self.limit = 0
			self.page_index = 1
		else:
			self.page_index = page_index
			self.offset = self.page_size * (page_index - 1)
			self.limit = self.page_size
		self.has_next = self.page_index < self.page_count
		self.has_previous = self.page_index > 1

	def __str__(self):
		return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

	__repr__ = __str__

class APIError(Exception):
	'''
	基础的APIError，包含错误类型(必要)，数据(可选)，信息(可选)
	'''
	def __init__(self, error, data='', message=''):
		super().__init__(message)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	'''
	表明输入数据有问题，data说明输入的错误字段
	'''
	def __init__(self, field, message=''):
		super().__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
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