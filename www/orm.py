# -*- coding:utf-8 -*-

import asyncio, logging
import aiomysql

__author__ = "Sunshine'Z"

def log(sql, args=()):
	logging.info('SQL: %s, ARGS: %s' % (sql, args))

async def create_pool(loop, **kw):
	'''
	创建数据库连接池
	:param loop:事件循环处理程序
	:param kw:数据库配置参数集合
	:return:无
	缺省情况下将编码设置为utf8，自动提交事务
	'''
	logging.info('create database connection pool...')
	global __pool
	__pool = await aiomysql.create_pool(
		host = kw.get('host', 'localhost'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 10),
		minsize  = kw.get('minsize', 1),
		loop = loop
	)

async def select(sql, args, size=None):
	'''
	数据库查询函数
	:param sql:sql语句
	:param args:sql语句中的参数
	:param size:要查询的数量
	:return:查询结果
	'''
	log(sql, args)
	async with __pool.get() as conn:
		# 创建一个结果为字典的游标
		async with conn.cursor(aiomysql.DictCursor) as cur:
			# 执行sql语句，将sql语句中的'?'替换成'%s'
			await cur.execute(sql.replace('?', '%s'), args or ())
			# 如果指定了数量，就返回指定数量的记录，如果没有就返回所有记录
			if size:
				rs = await cur.fetchmany(size)
			else:
				rs = await cur.fetchall()
		logging.info('rows returned: %s' % len(rs))
		return rs

async def execute(sql, args, autocommit=True):
	'''
	数据库DML
	:param sql:sql语句
	:param args:sql语句中的参数
	:param autocommit:自动提交事务
	:return:返回操作的结果数
	'''
	log(sql, args)
	async with __pool.get() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?', '%s'), args)
				affected = cur.rowcount
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected
