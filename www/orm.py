# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import asyncio, logging
import aiomysql
import  json

logging.basicConfig(level=logging.INFO)

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
	:param autocommit:是否自动提交事务
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
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		return affected

def create_args_string(num):
	'''
	用于输出sql语句中的占位符
	:param num:占位符个数
	:return:返回占位符字符串
	'''
	l = []
	for n in range(num):
		l.append('?')
	return ','.join(l)

class Field(object):
	'''
	定义Field类，负责保存(数据库)表的字段名和字段类型等信息
	'''
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s, %s, %s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	'''
	数据库中字符串类型
	'''
	def __init__(self, name=None, primary_key=False, default=None, ddl='VARCHAR(100)'):
		super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):
	'''
	数据库中布尔类型
	'''
	def __init__(self, name=None, default = False, ddl='BOOLEAN'):
		super().__init__(name, ddl, False, default)

class IntegerFiled(Field):
	'''
	数据库整数类型
	'''
	def __init__(self, name=None, primary_key=False, default=0, ddl='BIGINT'):
		super().__init__(name, ddl, primary_key, default)

class FloatField(Field):
	'''
	数据库浮点类型
	'''
	def __init__(self, name=None, primary_key=False, default=0.0, ddl='REAL'):
		super().__init__(name, ddl, primary_key, default)

class TextField(Field):
	'''
	数据库文本类型
	'''
	def __init__(self, name=None, default=0.0, ddl='TEXT'):
		super().__init__(name, ddl, False, default)

class ModelMetaclass(type):
	'''
	模型元类
	:param cls:当前准备创建的类的对象
	:param name:类的名字
	:param bases:类继承的父类集合
	:param attrs:类的方法集合
	:return: 模型元类
	'''
	def __new__(cls, name, bases, attrs):
		# 排除Model类本身
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None) or name
		logging.info('found model: %s (table: %s)' % (name, tableName))
		# 保存属性名和列的映射关系
		mappings = dict()
		# 保存非主键属性名
		fields = []
		# 保存主键
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info('found mappings: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key:
					if primaryKey:
						raise StandardError('Duplicate primary key for field: %s' % k)
					primaryKey = k
				else:
					fields.append(k)
		if not primaryKey:
			raise StandardError('primary key not found.')
		# 清空attrs中属性名
		# 从类属性中删除该Field属性，否则，容易造成运行时错误（实例的属性会遮盖类的同名属性）
		for k in mappings.keys():
			attrs.pop(k)
		# 将fields中属性名以`属性名`的方式装饰起来
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))
		# 保存属性和列的映射关系
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey
		# 除去主键以外的属性名称
		attrs['__fields__'] = fields
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句
		attrs['__select__'] = 'SELECT `%s`, %s FROM `%s` ' % (primaryKey, ','.join(escaped_fields), tableName)
		attrs['__insert__'] = 'INSERT INTO `%s` (%s, `%s`) VALUES(%s)' % (tableName, ','.join(escaped_fields), primaryKey,\
			create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s` = ?' % (tableName, \
			', '.join(map(lambda f: '`%s` = ?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s` = ?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):
	def __init__(self, **kw):
		super().__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value  = getattr(self, key, None)
		if value is None:
			# 自身没有找到，从mappings映射集合中找
			field = self.__mappings__[key]
			if field.default is not None:
				# field.default如果可以调用就返回调用后的结果
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value

	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		'''
		通过where查找多条记录对象
		:param cls:自身类对象
		:param where:where查询条件
		:param args:sql参数
		:param kw:查询条件列表
		:return:多条记录集合
		'''
		sql = [cls.__select__]
		if where:
			sql.append('WHERE ')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('ORDER BY ')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append(' LIMIT ')
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(''.join(sql), args)
		logging.debug('findAll result: %s' % json.dumps(rs))
		return [cls(**r) for r in rs]

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		'''
		查询某个字段的数量
		:param selectField: 要查询的字段
		:param where: where查询条件
		:param args: 参数列表
		:return: 数量
		'''
		sql = ['SELECT %s AS _num_ FROM `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	@classmethod
	async def find(cls, pk):
		'''
		通过查找记录对象
		:param cls:自身类对象
		:param pk:查询条件主键
		:return:
		'''
		rs = await select('%s where `%s` = ?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	async def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' % rows)

	async def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)

	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)