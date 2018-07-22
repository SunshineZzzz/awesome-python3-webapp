# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError

def get(path):
	'''
	定义@get('/path')装饰器
	:path:URL路径信息
	:return:返回装饰后的函数
	'''
	def decorator(func):
		# wrapper.__name__ = func.__name__
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	'''
	定义@post('/path')装饰器
	:path:URL路径信息
	:return:返回装饰后的函数
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

def get_required_kw_args(fn):
	'''
	获取指定函数的没有默认值的命名关键字参数
	:fn:函数
	:return:返回没有默认值的命名关键字参数
	'''
	args = []
	# 获取函数签名
	# parameters - An ordered mapping of parameters’ names to the corresponding Parameter objects.
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		'''
		kind - Describes how argument values are bound to the parameter.
		
		KEYWORD_ONLY() - Value must be supplied as a keyword argument. 
		Keyword only parameters are those which appear after a * or *args entry 
		in a Python function definition.
		
		default - The default value for the parameter. If the parameter has no default value, 
		this attribute is set to Parameter.empty.
		'''
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
				args.append(name)
	return tuple(args)

def get_named_kw_args(fn):
	'''
	获取指定函数的命名关键字参数
	:fn:函数
	:return:返回命名关键字参数元组
	'''
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

def has_named_kw_args(fn):
	'''
	指定函数是否有命名关键字参数
	:fn:函数
	:return:boolean
	'''
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_arg(fn):
	'''
	指定函数是否有关键字参数
	:fn:函数
	:return:boolean	
	'''
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		'''
		VAR_KEYWORD - A dict of keyword arguments that aren’t bound to any other parameter. 
		This corresponds to a **kwargs parameter in a Python function definition.
		'''
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

def has_request_arg(fn):
	'''
	指定函数是否有request参数，并且request后面可以的参数只能是*args, **kw, * a, b ...
	:fn:函数
	:return:boolean	
	'''
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		print(param.kind)
		if name == 'request':
			found = True
			continue
		'''
		VAR_POSITIONAL - A tuple of positional arguments that aren’t bound to any other parameter. 
		This corresponds to a *args parameter in a Python function definition.
		
		POSITIONAL_ONLY - Value must be supplied as a positional argument.
		
		POSITIONAL_OR_KEYWORD - Value may be supplied as either a keyword or positional argument 
		(this is the standard binding behaviour for functions implemented in Python.)
		'''
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL\
			and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != \
			inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter \
				in function: %s%s' % (fn.__name__, str(sig)))
	return found

class RequestHandler(object):
	'''
	RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数。
	(要完全符合aiohttp框架的要求，就需要把结果转换为web.Response对象，后面创建middleware的工厂函数时实现。)
	:app:Application is a synonym for web-server.
	:fn:调用函数
	'''
	def __init__(self, app, fn):
		self._app = app
		self._fn = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg =  has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	# 可以将实例视为函数
	async def __call__(self, request):
		kw = None
		# 如果函数有  命名关键字参数或者关键字参数
		if self._has_named_kw_args or self._has_var_kw_arg:
			# 判断客户端发来的方法是否为POST
			if request.method = 'POST':
				# 查询看客户端有没有提交的数据格式
				if not request.content_type:
					# HTTPClientError
					#  400 - HTTPBadRequest
					return web.HTTPBadRequest(text='Missing Content_Type.')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					# Read request body decoded as json.
					params = await request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw = params
				#
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
			if request.method = 'GET':
				# The query string in the URL, e.g., id=10
				qs = request.query_string
				if qs:
					kw = dict()
					'''
					example
					>>> from urllib.parse import urlparse
					>>> o = urlparse('http://www.cwi.nl:80/%7Eguido/Python.html')
					>>> o   
					ParseResult(scheme='http', netloc='www.cwi.nl:80', path='/%7Eguido/Python.html',
					params='', query='', fragment='')
					
					parse_qs - Parse a query string given as a string argument 
					(data of type application/x-www-form-urlencoded). Data are returned as a dictionary. 
					The dictionary keys are the unique query variable names and the values are lists of 
					values for each name.
					
					The optional argument keep_blank_values is a flag indicating whether blank values 
					in percent-encoded queries should be treated as blank strings. 
					A true value indicates that blanks should be retained as blank strings. 
					The default false value indicates that blank values are to be ignored and treated as 
					if they were not included.
					'''
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
			if kw is None:
				# match_info - Read-only property with AbstractMatchInfo instance for result of route resolving.
				kw = dict(**request.match_info)
			else:
				# 当函数参数没有关键字参数时，移去request除命名关键字参数所有的参数信息
				if not self._has_var_kw_arg and self._named_kw_args:
					# remove all unamed kw:
					copy = dict()
					# 遍历命名关键字参数
					for name in self._named_kw_args:
						if name in kw:
							copy[name] = kw[name]
					kw = copy
				for k, v in request.match_info.items():
					if k in kw:
						logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
					kw[k] = v
				# 假如命名关键字参数(没有附加默认值)，request没有提供相应的数值，报错
				if self._has_request_arg:
					for name in self._required_kw_args:
						if name not in kw:
							return web.HTTPBadRequest(text='Missing argument: %s'%(name))
				logging.info('call with args: %s' % str(kw))
				try:
					r = await self._func(**kw)
					return r
				except APIError as e:
					return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
	'''
	添加静态文件夹的路径
	:app:Application is a synonym for web-server.
	:return:无
	'''
	
	'''
	os.path.join - Join one or more path components intelligently.
	os.path.dirname - Return the directory name of pathname path.
	os.path.abspath - Return a normalized absolutized version of the pathname path.
	'''
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	'''
	router - Read-only property that returns router instance
	router.add_static - Adds a router and a handler for returning static files.
	'''
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
	'''
	用来注册一个URL处理函数
	:app:Application is a synonym for web-server.]
	:fn:导入的函数
	:return:无
	'''
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', \
		'.join(inspect.signature(fn).parameters.keys())))
	'''
	add_route(method, path, handler, *, name=None, expect_handler=None)
	Append handler to the end of route table.

	'''
	app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, moudle_name):
	'''
	直接导入文件，批量注册一个URL处理函数
	:app:Application is a synonym for web-server.]
	:moudle_name:导入的模块名
	:return:无	
	'''
	n = moudle_name.rfind('.')
	if n == (-1):
		mod = __import__(moudle_name, globals(), locals())
	else:
		name = moudle_name[n+1:]
		mod = getattr(__import__(moudle_name[:n], globals(), locals(), fromlist=[name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
	