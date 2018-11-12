python 实战项目：博客

创建对象池：好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。

day4:
	test.py:有修改，与廖雪峰教程的test有差别
	遇到1054和1062的错误
	orm：遇到问题“AttributeError: 'Connection' object has no attribute '_writer'” ，是因为在创建数据库链接库的时候把编码那个关键字的值写错了
	create_loop中的连接编码charset属性应把默认的'utf-8'改为'utf8'