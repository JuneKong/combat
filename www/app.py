#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#name:app

import logging; logging.basicConfig(level = logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from coroweb import add_routes, add_static

from handlers import cookie2user, COOKIR_NAME
# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
# 添加middleware的时候已经作了倒序处理
# 用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。

# 一个记录URL日志的logger
@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		# 记录日志
		logging.info('Requset: %s %s' % (request.method, request.path))
		# 继续处理请求
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def auth_factory(app, handler):
	@asyncio.coroutine
	def auth(request):
		logging.info('check user: %s %s' % (request.methed, request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIR_NAME)
		if cookie_str:
			user = yield from cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ = user
		return (yield from handler(request))
	return auth

# 把返回值转换为web.Response对象再返回，以保证满足aiohttp的要求
@asyncio.coroutine
def response_factory(app, handler):
	@asyncio.coroutine
	def response(request):
		#结果
		logging.info('Response handler...')
		r = yield from handler(request) # 执行RequestHandler方法
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
			return resp
		if isinstance(r, str):
			if r.startswitch('redirect'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and r >= 100 and r < 600:
			return web.Response(r)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and r < 600:
				return web.Response(r, str(m))
		# default
		resp = web.Response(body=str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

# *********************************
# json.dumps：将Python对象编码成JSON字符串
# json.loads：将已编码的JSON字符串解码为Python对象
# *********************************

# 把参数统一绑定在request.__data__上
@asyncio.coroutine
def data_factory(app, handler):
	@asyncio.coroutine
	def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswitch('application/json'):
				request.__data__ = yield from request.json()
				logging.info('request json: %s' % str(request.__data__))
			elif request.content_type.startswitch('application/x-www-from-urlencoded'):
				request.__data__ = yield from request.post()
				logging.info('request from: %s' % str(request.__data__))
		return (yield from handler(request))
	return parse_data

# **************************************************************************************
# 1、startswith() 方法用于检查字符串是否是以指定子字符串开头
# 2、request.json():只能够接受方法为POST、Body为raw，header内容为application/json类型的数据
# 3、post请求数据的四种编码方式
# 	(1) application/x-www-form-urlencoded：这是最常见的 POST 提交数据的方式
# 		浏览器的原生form表单，如果不设置enctype属性，那么最终就会以该方式提交数据。
# 	(2) multipart/form-data:另一常见方法，必须让form的enctyped等于这个值
# 		一般使用来上传文件
# 	(3) application/json：以json串提交数据。
# 	(4) text/xml：它是一种使用HTTP作为传输协议，XML作为编码方式的远程调用规范。
# ***************************************************************************************

# 时间过滤器
def datetime_filter(t):
	dalta = int(time.time() - t)
	if dalta < 60:
		return u'1分钟前'
	if dalta < 3600:
		return u'%s分钟前' % (dalta // 60)
	if dalta < 86400:
		return u'%s小时前' % (dalta // 3600)
	if dalta < 604800:
		return u'%s天前' % (dalta // 86400)
	dt = datetime.fromtimestamp(t) # 时间戳转换成字符串日期时间
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

# 环境配置
def init_jinja2(app, **kw):
	logging.info('init jinja2...')
	options = dict(
		# 是否默认启用xml/html自动转义特性
		autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string', '}}'),
		# 模块修改后是否自动重载模块
		auto_reload = kw.get('auto_reload', True)
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)
	env = Environment(loader = FileSystemLoader(path), **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env

# *******************************************************************************
# 1、os.path.join函数:将多个路径组合后返回
# **注意：第一个绝对路径之前的参数将会被忽略
# 2、os.path.dirname(path)：去掉文件名，返回目录 
# __file__:表示了当前文件的path
# **os.path.dirname(file)所在脚本是以绝对路径运行的，则会输出该脚本所在的绝对路径，
# 	若以相对路径运行，输出空目录
# 3、os.path.abspath(__file__) 获取脚本完整路径
# **注：当前正在执行的代码的目录，若未执行任何代码文件会报错‘__file__’ is not defined
# 4、jinja2.Environment():(环境)
# 	参数loader:加载器
# 5、假设环境对象env，env.filters属性：过滤器字典
# 6、jinja2.FileSystemLoader(path, encode='utf-8'): 文件系统加载器
# 	path可以为字符串或列表(多个位置时)
# ********************************************************************************


@asyncio.coroutine
def init(loop):
	yield from orm.create_pool(loop=loop, user='root', password='root', db='combat')
	app = web.Application(loop=loop, middlewares=[logger_factory, auth_factory, response_factory])
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	add_routes(app, 'handlers')
	add_static(app)
	srv = yield from loop.create_server(app.make_handler(),'127.0.0.1', 9001)
	logging.info('server started at http://127.0.0.1:9000...');
	return srv;


loop = asyncio.get_event_loop(); # 获取当前上下文的事件循环,创建一个事件循环
# 将协程注册到事件循环，并启动事件循环
# 其实是run_until_complete方法将协程包装成为了一个任务（task）对象. 
# task对象是Future类的子类，保存了协程运行后的状态，用于未来获取协程的结果
loop.run_until_complete(init(loop)) 

loop.run_forever();

# ********************************************
# make_handler():创建用于处理请求的http协议工厂
# ********************************************

