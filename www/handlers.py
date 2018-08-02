# -*- coding:utf-8 -*-

__author__ = "Sunshine'Z"

import re, time, json, logging, hashlib, base64, asyncio

import markdown2

from aiohttp import web

from coroweb import get, post
from apis import Page, APIValueError, APIResourceNotFoundError, APIPermissionError

from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = configs.session.name
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

'''
@get('/')
async def index(request):
	users = await User.findAll()
	return {
		'__template__':'test.html',
		'users': users
	}
'''
def get_page_index(page_str):
	'''
	字符串页数转整数
	:page_str:页数字符串
	:return:页数
	'''
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

def check_admin(request):
	'''
	检查当前登陆用户是否管理员
	:request:The Request object contains all the information about an incoming HTTP request.
	:return:bool
	'''
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def user2cookie(user, max_age):
	'''
	通过user生成cookie
	:user:user信息
	:max_age:过期时间
	:return:cookie字符串
	'''
	expires = str(int(time.time()) + max_age)
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

def text2html(text):
	lines = map(lambda s: '<p>%s<p>' % s.replace('&', '&amp;').\
		replace('<', '&lt').replace('>', '&gt'),\
		filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

async def cookie2user(cookie_str):
	'''
	解析cookie字符串，并判断是否正确
	:cookie_str:cookie字符串
	:return:None|user
	'''
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

@get('/')
async def index(*, page='1'):
	'''
	首页
	:page:页码
	:return:html
	'''
	page_index = get_page_index(page)
	num = await Blog.findNumber('COUNT(id)')
	page = Page(num)
	if num == 0:
		blogs = []
	else:
		blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
	return {
		'__template__': 'blogs.html',
		'page': page,
		'blogs': blogs
	}	

@get('/api/users')
async def api_get_users(*, page='1'):
	'''
	根据页码获取博客的用户
	:page:页码
	:return:dict
	'''
	page_index = get_page_index(page)
	num = await User.findNumber('COUNT(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at DESC', limit=(p.offset, p.limit))
	for u in users:
		u.passwd = '******'
	return dict(page=p, users=users)

@get('/register')
async def register():
	'''
	注册页面
	:return:html
	'''
	return {
		'__template__':'register.html'
	}

@get('/signin')
def signin():
	'''
	登陆页面
	:return:html
	'''
	return {
		'__template__':'signin.html'
	}

@post('/api/users')
async def api_register_user(*, email, name, passwd):
	'''
	注册
	:email:用户email
	:name:用户名称
	:passwd:密码
	:return:web response
	'''
	if not name or not name.strip():
		raise APIValueError('email', 'Invalid email.')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email = ?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	user = User(id = uid, name = name.strip(), email = email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), \
		image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
	await user.save()
	# make session cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/authenticate')
async def authenticate(*, email, passwd):
	'''
	登陆验证
	:email:用户email
	:passwd:密码
	:return:web response
	'''
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid passwd.')
	users = await User.findAll('email = ?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	# check passwd
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password.')
	# authenticate ok, set cookie:
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/signout')
async def signout(request):
	'''
	登出
	:request:The Request object contains all the information about an incoming HTTP request.
	:return:web response
	
	Referer 首部包含了当前请求页面的来源页面的地址，即表示当前页面是通过此来源页面里的链接进入的。
	服务端一般使用 Referer 首部识别访问来源，可能会以此进行统计分析、日志记录以及缓存优化等。
	需要注意的是 referer 实际上是 "referrer" 误拼写。
	https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Referer
	'''
	referer = request.headers.get('Referer')
	# To redirect user to another endpoint 
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

@get('/manage/blogs/create')
async def manage_create_blog():
	'''
	创建博客页面
	:return:web response
	:return:html
	'''
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
	'''
	创建web的API
	:request:The Request object contains all the information about an incoming HTTP request.
	:name:博客名称
	:summary:博客摘要
	:content:博客内容
	'''
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog = Blog(user_id = request.__user__.id, user_name = request.__user__.name, \
		user_image = request.__user__.image, name = name.strip(), \
		summary=summary.strip(), content=content.strip())
	await blog.save()
	return blog

@get('/manage/blogs')
async def manage_blogs(*, page = '1'):
	'''
	博客页面展示页面
	:page:获取对应页码
	:return:html
	'''
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
	'''
	根据ID获取指定博客的API
	:id:博客ID
	:return:blog info
	'''
	logging.debug('api_get_blog id: %s' % id)
	blog = await Blog.find(id)
	return blog

@get('/api/blogs')
async def api_blogs(*, page = '1'):
	'''
	根据页码获取博客的API
	:page:页码
	:return:blog info
	'''
	page_index = get_page_index(page)
	num = await Blog.findNumber('COUNT(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = await Blog.findAll(orderBy='created_at DESC', limit=(p.offset, p.limit))
	return dict(page=p, blogs=blogs)

@get('/manage/blogs/edit')
async def manage_edit_blog(*, id):
	'''
	编辑指定id的博客
	:id:博客的id
	:return:html
	'''
	return {
		'__template__': 'manage_blog_edit.html',
		'id': id,
		'action': '/api/blogs/%s' % id
	}

@post('/api/blogs/{id}/delete')
async def api_delete_blog(request, *, id):
	'''
	删除指定id的博客
	:request:The Request object contains all the information about an incoming HTTP request.
	:id:博客的id
	:return:被删除的博客id
	'''
	check_admin(request)
	blog = await Blog.find(id)
	await blog.remove()
	return dict(id=id)

@post('/api/blogs/{id}')
async def api_update_blog(request, *, id, name, summary, content):
	'''
	更新指定id的博客
	:request:The Request object contains all the information about an incoming HTTP request.
	:id:博客id
	:name:博客名称
	:summary:博客简洁
	:content:博客内容
	:return:
	'''
	check_admin(request)
	blog = await Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	await blog.update()
	return blog

@get('/manage/users')
def manage_users(*, page='1'):
	'''
	根据page展示用户列表
	:page:页数
	:return:html
	'''
	return {
		'__template__': 'manage_users.html',
		'page_index': get_page_index(page)
	}

@get('/manage/comments')
async def manage_comments(*, page='1'):
	'''
	根据page展示用户评论
	:page:页数
	:return:html	
	'''
	return {
		'__template__': 'manage_comments.html',
		'page_index': get_page_index(page)
	}

@get('/api/comments')
async def api_comments(*, page = '1'):
	'''
	根据页码获取博客的评论
	:page:页码
	:return:comment info
	'''
	page_index = get_page_index(page)
	num = await Comment.findNumber('COUNT(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = await Comment.findAll(orderBy='created_at', limit=(p.offset, p.limit))
	return dict(page=p, comments=comments)

@post('/api/post/{id}/comments')
async def api_create_comment(request, *, id, content):
	'''
	创建指定id博客的评论
	:request:The Request object contains all the information about an incoming HTTP request.
	:id:博客id
	:content:博客内容
	:return:comment info
	'''
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = await Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
	await comment.save()
	return comment

@post('/api/comments/{id}/delete')
async def api_delete_comments(request, *, id):
	'''
	删除指定id的评论
	:request:The Request object contains all the information about an incoming HTTP request.
	:id:评论id
	:return:id
	'''
	check_admin(request)
	c = await Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	c.remove()
	return dict(id=id)