#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 编写Model

import time
import uuid

# ***********
# uuid:不可变对象UUID（UUID类）和函数uuid1()、uuid3()、uuid4()和uuid5()
# 使用uuid1()或uuid4()可以获得一个唯一的ID
# uuid1()包含了主机的网络名称，uuid4()不涉及网络主机名，仅生成一个随机UUID，因此从隐私保护角度uuid4()更加安全。
# 
# 指定类型
# hex：指定32个字符以创建UUID对象，当指定一个32个字符构成的字符串来创建一个UUID对象时，花括号、连字符和URN前缀等都是可选的；
# ***********

from orm import Model, StringField, BooleanField, FloatField, TextField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id,  ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, dll='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    create_at = FloatField(default=time.time)


class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    create_at = FloatField(default=time.time)

# *********************
# 1、日期和时间用float类型存储在数据库中，而不是datetime类型，
# 	 这么做的好处是不必关心数据库的时区以及时区转换问题，排序非常简单，
# 	 显示的时候，只需要做一个float到str的转换，也非常容易。
# ********************
