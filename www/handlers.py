#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 处理请求

'url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post
from models import User, Comment, Blog, next_id

# @get('/')
# async def index():
# 	users = await User.findAll()
# 	return {
# 		# '__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
# 		'__template__': 'test.html',
# 		'users': users
# 	}

@get('/')
def index():
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	blogs = [
		Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
		Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
		Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200)
	]
	return {
		'__template__': 'blogs.html',
		'blogs': blogs
	}

