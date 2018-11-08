#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# name: 编写ORM

import asyncio
import logging

import aiomysql

# 创建连接池
# 连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务


@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf-8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )
# ****************************************
# dict.get(key, default=None)
# 返回指定键的值，如果值不在字典中返回默认值。
# dict为字典
# ****************************************


# 执行SELECT语句
#     @param sql 语句
#     @param args 语句参数
#     @param size 获取的记录数量
#     @return 返回记录

# 注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
    	# DictCursor:指定返回的类型为dict(字典)
        cur = yield from conn.cursor(aiomysql.DictCursor)
        # SQL语句的占位符是?，而MySQL的占位符是%s, 因此要替换
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs

# 执行INSERT、UPDATE、DELETE语句
#     @return 影响的行数


@asyncio.coroutine
def execute(sql, args, autocommit=True):
    log(sql)
    with (yield from __pool) as conn:
    	if not autocommit:
    		yield from conn.begin()
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
        	if not autocommit:
        		yield from conn.rollback()
            raise
        return affected

# ORM
from orm import Model, StringField, IntegerField


class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_key=True)
    name = StringField()

# *******************************************************
# IntegerField：整数列(有符号的) -2147483648 ～ 2147483647
# StringField：字符串
# *******************************************************


# 定义Model(基类)

class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' %
                              (key, str(value)))
                setattr(self, key, value)
        return value

    # *******类方法*******
    # 根据属性查找
    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
    	'find object by primary key.'
    	rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
    	if len(rs) == 0:
    		return None
    	return cls(**rs[0])

    # 查找所有
    @classmethod
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):
    	'find objects by where clause.'
    	sql = [cls.__select__]
    	if where:
    		sql.append('where')
    		sql.append(where)
    	if args is None:
    		args = []
    	orderBy = kw.get('orderBy', None)
    	if orderBy:
    		sql.append('order by')
    		sql.append(orderBy)
    	limit = kw.get('limit', None)
    	if limit is not None:
    		sql.append('limit')
    		if isinstance(limit, int):
    			sql.append('?')
    			args.append(limit)
    		elif isinstance(limit, tuple) and len(limit) == 2:
    			sql.append('?, ?')
    			args.extend(limit)
    		else:
    			raise ValueError('Invalid limit value: %s' % str(limit))
    	rs = yield from select(' '.join(sql), args)
    	return [cls(**r) for r in rs]
	
	# 根据number查找
	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where=None, args=None):
		'find number by select and where.'
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

    # *******实例方法*******
    # 调用时要加yield from， 不然仅仅是创建而没有执行
    # 保存
    @asyncio.coroutine
    def save(self):
    	args = list(map(self.getValueOrDefault, self.__fields__))
    	args.append(self.getValueOrDefault(self.__primary_key__))
    	rows = yield from execute(self.__insert__, args)
    	if rows != 1:
    		logging.warn('failed to insert record: affected rows: %s' % rows)

    # 更新
    @asyncio.coroutine
    def update(self):
    	args = list(map(self.getValue, self.__fields__))
    	args.append(self.getValue(self.__primary_key__))
    	rows = yield from execute(self.__update__, args)
    	if rows != 1:
    		logging.warn('failed to update by primary key: affected row: %s' % rows)

    # 删除
    @asyncio.coroutine
    def remove(self):
    	args = [self.getValue(self.__primary_key__)]
    	rows = yield from execute(self.__delete__, args)
    	if rows != 1:
    		logging.warn('failed to remove by primary key: affected  rows: %s' % rows)

# *************************************************************
# 1、只有继承了type的类能够做为metaclass的参数。(不建议使用，高手除外)
# 2、callable() 函数用于检查一个对象是否是可调用的。
# 3、@classmethod 类方法，子类可使用
# 4、append和extend的区别：
# 	    list.append(object) 向列表中添加一个对象object(整体看成一个对象，是列表len+1)
# 		list.extend(sequence) 把一个序列seq的内容添加到列表中(相当于列表的合并)
# 5、如果要把一个类的实例变成 str，就需要实现特殊方法__str__()
# *************************************************************


# Field类
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 映射varchar的StringField类
# 字符
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)
# 布尔值
class BooleanField(Field):
	def __init__(self, name=None, default=False):
		super().__init__(name, 'boolean', False, default)		
# 整型
class IntegerField(Field):
	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)		
# 浮点型
class FloatField(Field):
	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name, 'real', primary_key, default)		
# 文本
class TextField(Field):
	def __init__(self, name=None, default=None):
		super().__init__(name, 'text', False, default)		


def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ', '.join(L)

# 将具体的子类如User的映射信息读取，通过metaclass：ModelMetaclass

class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # 排除Model类本身
        if name == 'Model'
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主域名
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise RuntimeError(
                            "Duplicate primary key for field: %s" % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primany key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        # 构造默认的SELECT,INSERT,UPDATE和DELETE语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (
            primaryKey, ','.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) value (%s)' % (tableName, ','.join(
            escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ','.join(
            map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (
            tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

# *******************************************************
# 1、bases: 基类
# 2、注意：<class 'type'>是所有类型的类型。<class 'object'>也是所有对象的超类（除了它自己）。
# 3、__new__() 方法是在类准备将自身实例化时调用。
#    __new__() 方法始终都是类的静态方法，即使没有被加上静态方法装饰器。
# 4、RuntimeError：一般的运行时错误
# 5、join() 方法用于将序列中的元素以指定的字符连接生成一个新的字符串。
# *******************************************************
