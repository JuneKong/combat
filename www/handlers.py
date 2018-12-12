#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 处理请求

'url handlers '

import re
import time
import json
import logging
import hashlib
import base64
import asyncio

import markdown2

from coroweb import get, post
from apis import Page, APIValueError, APIResourceNotFoundError

from models import User, Comment, Blog, next_id
from config import configs

COOKIR_NAME = 'cobsession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(
    r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
# 注意用户口令是客户端传递的经过SHA1计算后的40位Hash字符串，所以服务器端并不知道用户的原始口令。
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

# 检测是否登录且是否为管理员
def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p


# @get('/')
# async def index():
# 	users = await User.findAll()
# 	return {
# 		# '__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
# 		'__template__': 'test.html',
# 		'users': users
# 	}

# *****************start:用户浏览页面********************************
# 首页
@get('/')
def index():
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary,
             created_at=time.time() - 120),
        Blog(id='2', name='Something New', summary=summary,
             created_at=time.time() - 3600),
        Blog(id='3', name='Learn Swift', summary=summary,
             created_at=time.time() - 7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

# 注册
@get('/register')
def register():
	return {
		'__template__': 'register.html'
	}

# 登录
@get('/signin')
def signin():
	return {
		'__template__': 'signin.html'
	}

# 退出
@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIR_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out.')
	return r

# 日志详情
@get('/blog/{id}')
def get_blog(id):
	blog = yield from Blog.find(id)
	comments = yield from Comment.findAll('blog_id=?', [id], orderBy='create_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
		'__template__': 'blog.html',
		'blog': blog,
		'comments': comments
	}

# *****************end:用户浏览页面********************************



# *****************start:管理页面********************************

@get('/manage/')
def manage():
	return 'redirect:/manage/comments/'

# 评论列表
@get('/manage/comments')
def manage_comments(*, page='1'):
	return {
		'__template__': 'manage_comments.html',
		'page_index': get_page_index(page)
	}

# 日志列表
@get('/manage/blogs')
def manage_blogs(*, page='1'):
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}

# 创建日志
@get('/manage/blogs/create')
def manage_create_blog():
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}

# 修改日志
@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
	return {
		'__template__': 'manage_blog_edit.html',
		'id': id,
		'action': '/api/blogs/%s' % id
	}
# 用户列表
@get('/manage/users')
def manage_users(*, page='1'):
	return {
		'__template__': 'manage_users.html',
		'page_index': get_page_index(page)
	}
# *****************end:管理页面********************************


# *****************start:后端api********************************
# 获取日志
@get('/api/blogs')
def api_blogs(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = yield from Blog.findAll(orderBy='create_at desc', limit=(p.offect, p.limit))
	return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
def api_get_blog(*, id):
	blog = yield from Blog.find(id)
	return blog

# 创建日志
@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
	check_admin(request);
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
	yield from blog.save();
	return blog

# 修改日志
@post('/api/blogs/{id}')
def api_update_blog(id, request, *, name, summary, content):
	check_admin(request)
	blog = yield from Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	yield from blog.update()
	return blog

# 删除日志
@post('/api/blogs/{id}/delete')
def api_delete_blog(request, *, id):
	check_admin(request)
	blog = yield from Blog.find(id)
	yield from blog.remove()
	return dict(id=id)

# 获取评论
@get('/api/comments')
def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num:
		return dict(page=p, comments=())
	comments = yield from Comment.findAll(orderBy='create_at desc', limit=(p.offset, p.limit))
	return dict(page=p, comments=comments)

# 创建评论
@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = yield from Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
	yield from comment.save()
	return comment

# 删除评论
@post('/api/comments/{id}/delete')
def api_delete_comment(id, request):
	check_admin(request)
	c = yield from Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	yield from c.remove()
	return dict(id=id)

# 创建新用户
@post('/api/users')
def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = yield from User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(
        sha1_passwd.encode('tuf-8')).hexdigest(), image='about:_blank')
    yield from user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIR_NAME, user2cookie(
        user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 获取用户
@get('/api/users')
def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = yield from User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = yield from User.findAll(orderBy='create_at desc', limit(p.offset, p.limit))
	for u in users:
		u.password = '******'
	return dict(page=p, users=users)

# *****************end:后端api********************************



# 用户是否存在
@post('/api/authenticate')
def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')
	users = yield from User.findAll('email=?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	# check passwd:
	sha1 = hashlib.sha1();
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password.')
	# authenticate ok, set cookie:
	r = web.Response()
	r.set_cookie(COOKIR_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r


# 计算加密cookie
def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

# 解密cookie
@asyncio.coroutine
def cookie2user(cookie_str):
	# parse cookie and load user if cookie is valid.
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = yield from User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
	except Exception as e:
		logging.exception(e)
		return None

# 文本转换
def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)