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

# 运用inspect模式，创建几个函数用以获取URL处理函数与request参数之间的关系

# 获取没有默认值得命名关键字参数(必要参数)
def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
	return tuple(args)

# ***************************
# 1、signature():返回给定可调用对象的签名对象
# 2、param.kind：描述参数值如何绑定到参数
# 3、inspect.Parameter对象的kind属性的五个枚举值：
# 	  KEYWORD_ONLY：值必须作为关键字参数提供。
# 	  POSITIONAL_ONLY：值必须作为位置参数提供。
# 	  POSITIONAL_OR_KEYWORD：值可以作为关键字或位置参数提供
# 	  VAR_POSITIONAL：不绑定到任何其他参数的位置参数的元组
# 	  VAR_KEYWORD：关键字参数的字典，不绑定到任何其他参数。
# 4、empty: 指定没有默认值和注释的特殊类级标记。
# ***************************

# 获取命名关键字参数
def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

# 判断有没有命名关键字参数
def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

# 判断有没有关键字参数
def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

# 判断是否含有名叫'request'参数,且该参数是否为最后一个参数
def has_request_arg(fn):
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last names parameter in function: %s%s' % (fn.__name__, str(sig)))
	return found



# RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数（可调用）。
# RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求

# 来封装一个URL处理函数
class RequestHandler(object):
	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	@asyncio.coroutine
	def __call__(self, request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest(text='Missing Content_type.')
				ct = request.content_type.lower()
				if ct.startswitch('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest(text='JSON body must be object.')
					kw = params
				elif ct.startswitch('application/x-www-from-urlencoded') or ct.startswitch('multipart/form-data'):
					params = yield from request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest(text=('Unsupported Content_type: %s' % request.content_type))
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				# remove all unamed kw：
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			#check named arg:
			for k,v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest(text=('Missing argument: %s' % name))
		logging,info('call with args: %s' % str(kw))
		try:
			r = yield from self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error, data=e.data, message=e.message)

# ***************************************************************************************************************
# 1、__init__()与__call__()的区别：
# 	 __init__()方法的作用是创建(初始化)一个类的实例。
# 	 __call__()的作用是使实例能够像函数一样被调用，同时不影响实例本身的生命周期（__call__()不影响一个实例的构造和析构）。
# 	 但是__call__()可以用来改变实例的内部成员的值。
# 2、match_info主要是保存像@get('/blog/{id}')里面的id，就是路由路径里的参数
# 3、request.query_string：查询字符串
# ***************************************************************************************************************

def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

# ****************************************************
# 1、add_static():添加用于返回静态文件的路由器和处理程序。
# 	 **警告：仅对开发使用add_static()。
# ****************************************************


# 注册一个URL处理函数
def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @path not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.key())))
	app.router.add_route(method, path, RequsetHandler(app, fn))

# ****************************************
# 1、asyncio.iscoroutinefunction():判断是否为协程函数
# 2、inspect.isgeneratorfunction():判断是否为生成器函数
# 3、inspect模块的用处：
# 	(1)对是否是模块，框架，函数等进行类型检查。
# 	(2)获取源码
# 	(3)获取类或函数的参数的信息
# 	(4)解析堆栈
# 4、app.router是一个UrlDispatcher对象：路由器
#    它有一个add_route()方法，注册一个路由器
# ****************************************

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

# ***********************************************************************************
# 1、rfind()：返回字符串最后一次出现的位置(从右向左查询)，如果没有匹配项则返回-1。
# 2、__import__()：用于动态加载类和函数。
# 3、globals()：会以字典类型返回当前位置的全部全局变量。
# 4、locals()：函数会以字典类型返回当前位置的全部局部变量。
# 5、dir()：不带参数时，返回当前范围内的变量、方法和定义的类型列表；
# 			带参数时，返回参数的属性、方法列表。如果参数包含方法__dir__()，该方法将被调用。
# 			如果参数不包含__dir__()，该方法将最大限度地收集参数信息。
# 6、getattr(objec，name[,default]) 函数用于返回一个对象属性值。
# 7、callable() 函数用于检查一个对象是否是可调用的。
# ************************************************************************************