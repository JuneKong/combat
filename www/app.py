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

# middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
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

# 把返回值转换为web.Response对象再返回，以保证满足aiohttp的要求
@asyncio.coroutine
def response_factory(app, handler):
	@asyncio.coroutine
	def response(request):
		#结果
		logging.info('Response handler...')
		r = yield from handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
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

# 时间过滤器
def datatime_filter(t):
	dalta = int(time.time() - t)
	if dalta < 60:
		return u'1分钟前'
	if dalta < 3600:
		return u'%s分钟前' % (dalta // 60)
	if dalta < 86400:
		return u'%s小时前' % (dalta // 3600)
	if dalta < 604800:
		return u'%s天前' % (dalta // 86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


def init_jinja2(app, **kw):
	logging.info('init jinja2...')
	options = dict(
		autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string', '{{'),
		variable_end_string = kw.get('variable_end_string', '}}'),
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

# ********************************
# 1、os.path.join函数:将多个路径组合后返回
# **注意：第一个绝对路径之前的参数将会被忽略
# 2、os.path.dirname(path)：去掉文件名，返回目录 
# __file__:表示了当前文件的path
# **os.path.dirname(file)所在脚本是以绝对路径运行的，则会输出该脚本所在的绝对路径，若以相对路径运行，输出空目录
# 3、os.path.abspath(__file__) 获取脚本完整路径
# **注：当前正在执行的代码的目录，若未执行任何代码文件会报错‘__file__’ is not defined
# 4、jinja2.Environment():(环境)
# 	参数loader:加载
# ********************************


@asyncio.coroutine
def init(loop):
	yield from orm.create_pool(loop=loop, user='root', password='root', db='combat')
	app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
	init_jinja2(app, filters=dict(detatime=datatime_filter))
	add_routes(app, 'handlers')
	add_static(app)
	srv = yield from loop.create_server(app.make_handler(),'127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...');
	return srv;

loop = asyncio.get_event_loop();
loop.run_until_complete(init(loop))
loop.run_forever();

