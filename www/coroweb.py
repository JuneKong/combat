#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: web框架

# 原因是从使用者的角度来说，aiohttp相对比较底层，编写一个URL的处理函数需要这么几步：
# 1、编写一个用@asyncio.coroutine装饰的函数
# 2、传入的参数需要自己从request中获取
# 3、需要自己构造Response对象
# 编写简单的函数而非引入request和web.Response还有一个额外的好处，就是可以单独测试，否则，需要模拟一个request才能测试。

import asyncio, os, inspect, logging, functools

from urllib import parse
from aiohttp import web
from apis import APIError

# 把一个函数映射为一个URL处理函数
def get(path):
	'''Define decorator @get('/path')'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	'''Define decorator @post('/path')'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

# RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数。
# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求

# 来封装一个URL处理函数
class RequsetHandler(object):
	def __init__(self, app, fn):
		self._app = app
		self._func = fn

	@asyncio.coroutine
	def __call__(self, request):
		pass

# 注册一个URL处理函数
def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @path not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.key())))


# 自动扫描创建URL处理函数
def add_routes(app, module_name):
	n = module_name.rfind('.')
	if n == (-1):
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswitch('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
