# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"


import logging; logging.basicConfig(level = logging.DEBUG)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import configs

import orm
from coroweb import add_routes, add_static

from handlers import cookie2user, COOKIE_NAME

def init_jinja2(app, **kw):
	'''
	初始化jinja2模板
	:app:Application is a synonym for web-server.
	:kw:配置参数
	:return:空
	'''
	logging.info('init jinja2...')
	options = dict(
		# If set to true the XML/HTML autoescaping feature is enabled by default. 
		autoescape = kw.get('autoescape', True),
		# The string marking the begin of a block. Defaults to '{%'.
		block_start_string = kw.get('block_start_string', '{%'),
		# The string marking the end of a block. Defaults to '%}'.
		block_end_string = kw.get('block_end_string', '%}'),
		# The string marking the begin of a print statement. Defaults to '{{'.
		variable_start_string = kw.get('variable_start_string', '{{'),
		# The string marking the end of a print statement. Defaults to '}}'.
		variable_end_string = kw.get('variable_end_string', '}}'),
		# Some loaders load templates from locations where the template sources may 
		# change (ie: file system or database). If auto_reload is set to True (default) 
		# every time a template is requested the loader checks if the source changed and if yes, 
		# it will reload the template. For higher performance it’s possible to disable that.
		auto_reload = kw.get('auto_reload', True)
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)
	'''
	FileSystemLoader
	Loads templates from the file system. 
	This loader can find templates in folders on the file system and is the preferred way to load them.
	'''
	env = Environment(loader = FileSystemLoader(path), **options)
	'''
	自定义过滤器只是常规的Python函数，过滤器左边作为第一个参数，其余的参数作为额外的参数或关键字参数传递到过滤器。	
	例如在过滤器{{ 42|myfilter(23) }}中，函数被以myfilter(42, 23)调用。
	'''
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env

async def logger_factory(app, handler):
	'''
	logger_factory middleware
	:app:Application is a synonym for web-server.
	:handler:RequestHandler object
	:return:fn
	'''
	async def logger(request):
		logging.info('Request: %s %s' % (request.method, request.path))
		return (await handler(request))
	return logger

async def auth_factory(app, handler):
	'''
	auth_factory middleware
	:app:Application is a synonym for web-server.
	:handler:RequestHandler object
	:return:fn
	'''
	async def auth(request):
		logging.info('check user: %s %s' % (request.method, request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user = await cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ = user
		if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
			return web.HTTPFound('/signin')
		return await handler(request)
	return auth

async def data_factory(app, handler):
	'''
	data_factory middleware
	:app:Application is a synonym for web-server.
	:handler:RequestHandler object
	:return:fn
	'''
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info('request json: %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('request form: %s' % str(request.__data__))
		return (await handler(request))
	return parse_data

async def response_factory(app, handler):
	'''
	response_factory middleware
	:app:Application is a synonym for web-server.
	:handler:RequestHandler object
	:return:fn
	'''
	async def response(request):
		logging.info('Response handler...')
		r = await handler(request)
		#StreamResponse - The base class for the HTTP response handling.
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			'''
			class aiohttp.web.Response(*, body=None, status=200, reason=None, text=None, \
			headers=None, content_type=None, charset=None)
			The most usable response class, inherited from StreamResponse.
			Accepts body argument for setting the HTTP response BODY.
			'''
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				# HTTPFound - To redirect user to another endpoint 
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				'''
				dumps - Serialize obj to a JSON formatted str using this conversion table. 
				If ensure_ascii is false, the result may contain non-ASCII characters and 
				the return value may be a unicode instance.

				If specified, default should be a function that gets called for objects that 
				can’t otherwise be serialized. It should return a JSON encodable version of
				the object or raise a TypeError. If not specified, TypeError is raised.
				'''
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				r['__user__'] = request.__user__
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 600:
			return web.Response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
		# default
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

def datetime_filter(t):
	'''
	创建模板需要的过滤器
	:t:unix时间戳
	:return:返回时间说明字符串
	'''
	delta = int(time.time() - t)
	if delta < 60:
		return u'1分钟前'
	if delta < 3600:
		return u'%s分钟前' % (delta // 60)
	if delta < 86400:
		return u'%s小时前' % (delta // 3600)
	if delta < 604800:
		return u'%s天前' % (delta // 86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

async def init(loop):
	'''
	web框架初始化
	:loop:event loops
	:return:srv
	'''
	# 初始化mysql连接池
	# await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='123456', db='awesome')
	await orm.create_pool(loop=loop, **configs.db)
	'''
	初始化web框架
	middlewares - A middleware is a coroutine that can modify either the request or response.
	'''
	app = web.Application(loop=loop, middlewares=[
		logger_factory, auth_factory, response_factory
	])
	# 初始化模板 
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	# 将模块handlers中的所有函数注册为URL处理函数
	add_routes(app, 'handlers')
	# 添加静态文件夹的路径
	add_static(app)
	# 创建web服务器
	srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9001)
	logging.info('server started at http://127.0.0.1:9001...')
	return srv

if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(init(loop))
	loop.run_forever()