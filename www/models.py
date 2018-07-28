# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import  time, uuid
from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
	'''
	:return:随机创建唯一id字符串，作为主键缺省值
	'''
	# uuid - universally unique Identifier
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
	__table__ = 'users'

	id = StringField(primary_key = True, default = next_id, ddl = 'VARCHAR(50)')
	email = StringField(ddl = 'VARCHAR(50)')
	passwd = StringField(ddl = 'VARCHAR(50)')
	admin = BooleanField()
	name = StringField(ddl = 'VARCHAR(50)')
	image = StringField(ddl = 'VARCHAR(500)')
	created_at = FloatField(default = time.time)

class Blog(Model):
	__table__ = 'blogs'

	id = StringField(primary_key = True, default = next_id, ddl = 'VARCHAR(50)')
	user_id = StringField(ddl='VARCHAR(50)')
	user_name = StringField(ddl='VARCHAR(50)')
	user_image = StringField(ddl='varchar(500)')
	name = StringField(ddl='varchar(50)')
	summary = StringField(ddl='varchar(200)')

class Comment(Model):
	__table__ = 'comment'

	id = StringField(primary_key=True, default = next_id, ddl = 'VARCHAR(50)')
	blog_id = StringField(ddl = 'VARCHAR(50)')
	user_name = StringField(ddl = 'VARCHAR(50)')
	user_image = StringField(ddl = 'VARCHAR(50)')
	content = TextField()
	created_at = FloatField(default=time.time)