#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 

'url handlers '

import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post
from models import User, Comment, Blog, next_id

@get('/')
async def index(request):
	users = await User.findAll()
	return {
		# '__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
		'__template__': 'test.html',
		'users': users
	}