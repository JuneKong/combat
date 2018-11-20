#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 测试

import orm
from models import User, Blog, Comment
import asyncio


def test(loop):
    yield from orm.create_pool(loop=loop, user='root', password='root', db='combat')
    u = User(name='Test', email="test@example.com",
             passwd='123456', image='about:blank')
    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()

if loop.is_closed(): 
	sys.exit(0)