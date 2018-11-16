// combat.js

// patch for lower-version IE:

if(!window.console){
	window.console = {
		log: function() {},
		info: function() {},
		error: function() {},
		warn: function() {},
		debug: function() {}
	};
};

// patch for string.trim():

if(!String.prototype.trim){
	String.prototype.trim = function() {
		return this.replace(/^\s|\s+$/g, '');
	};
};

if(!Number.prototype.toDateTime) {
	var replaces = {
		'yyyy': function(dt) {
			return dt.getFullYear().toString();
		},
		'yy': function(dt) {
			return (dt.getFullYear() % 100).toString();
		},
		'MM': function(dt) {
			var m = dt.getMonth() + 1;
			return m < 10 ? '0' + m : m.toString();
		},
		'M': function(dt) {
			var m = dt.getMonth() + 1;
			return m.toString();
		},
		'dd': function(dt) {
			var d = dt.getData();
			return d < 10 ? '0' + d : d.toString();
		},
		'd': function(dt) {
			var d = dt.getData();
			return d.toString();
		},
		'hh': function(dt) {
			var h = dt.getHours();
			return h < 10 ? '0' + h : h.toString();
		},
		'h': function(dt) {
			var h = dt.getHours();
			return h.toString();
		},
		'mm': function(dt) {
			var m = dt.getMinutes();
			return m < 10 ? '0' + m : m.toString();
		},
		'm': function(dt) {
			var m = dt.getMinutes();
			return m.toString();
		},
		'ss': function(dt) {
			var s = dt.getSeconds();
			return s < 10 ? '0' + s : s.toString();
		},
		's': function(dt) {
			var s = dt.getSeconds();
			return s.toString();
		},
		'a': function(dt) {
			var h = dt.getHours();
			return h < 12 ? 'AM' : 'PM';
		}
	};
	var token = /([a-zA-Z]+)/;
	Number.prototype.toDateTime = function(format) {
		var fmt = format || 'yyyy-MM-dd hh:mm:ss';
		var dt = new Date(this * 1000);
		var arr = fmt.split(token);
		for(var i = 0; i < arr.length; i++){
			var s = arr[i];
			if(s && s in replaces) {
				arr[i] = replaces[s](dt);
			}
		}
		return arr.join('');
	};
};

function encodeHtml(str){
	return String(str)
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
}


// parse query string as object:

function parseQueryString(){
	var q = location.search,
		r = {},
		i, pos, s, qs;
	////////////////////////////
	// charAt() 方法可返回指定位置的字符。
	// substring() 方法用于提取字符串中介于两个指定下标之间的字符。
	////////////////////////////
	if(q && q.charAt(0) === '?'){
		qs = q.substring(1).split('&');
		for (i = 0; i < qs.length; i++) {
			s = qs[i];
			pos = s.indexOf('=');
			if(pos <= 0){
				continue;
			}
			// replace(/\+/g, ' ')是因为在URL规范里面，加号(+)会被编码为空格，所有在decode的时候，需要把加号转回空格去。
			r[s.substring(0, pos)] = decodeURIComponent(s.substring(pos + 1)).replace(/\+/g, ' ');
		}
	}
	return r;
};

function refresh(){
	var t = new Date().getTime(),
		url = location.pathname;
	if(location.search){
		url = url + location.search + '&t=' + t;
	}
	else{
		url = url + '?t=' + t;
	}
	location.assign(url);
};

function toSmartDate(timestamp){
	if(typeof(timestamp) === 'string'){
		timestamp = parseInt(timestamp);
	}
	if(isNaN(timestamp)){
		return '';
	}
	var today = new Date(g_time),
		now = today.getTime(),
		s = '1分钟前',
		t = now - timestamp;
	if(t > 604800000){
		// 1 week ago:
		var that = new Date(timestamp);
		var y = that.getFullYear(),
			m = that.getMonth() + 1,
			d = that.getData(),
			hh = that.getHours(),
			mm = that.getMinutes();
		s = y === today.getFullYear() ? '' : y + '年';
		s = s + m + '月' + d + '日' + hh + ':' + (mm < 10 ? '0' : '') + mm;
	}
	else if (t >= 86400000) {
		// 1-6 days ago:
		s = Math.floor(t / 86400000) + '天前';
	}
	else if (t >= 3600000) {
		// 1-23 hours ago:
		s = Math.floor(t / 3600000) + '小时前';
	}
	else if (t >= 60000) {
		s = Math.floor(t / 60000) + '分钟前';
	}
	return s;
}


$(function() {
	$('.x-smartdate').each(function(){
		$(this).removeClass('x-smartdate').text(toSmartDate($(this).attr('date')));
	});
});


// JS Template

function Template(tpl){
	var fn, match,
		code = ['var r = []; \nvar _html = function(str) { return  str.replace(/&/g, \'&amp;\').replace(/"/g, \'&quot;\').replace(/\'/g, \'&#39;\').replace(/</g, \'&lt;\').replace(/>/g, \'&gt\');};'],
		re = /\{\s*([a-zA-Z\.\_0-9()]+)(\s*\|\s*safe)?\s*\}/m,
		addLine = function(text){
			code.push('r.push(\'' + text.replace(/\'/g, '\\\'').replace(/\n/g, '\\n').replace(/\r/g, '\\r') + '\');');
		};
	while(match = re.exec(tpl)){
		if (match.index > 0) {
			addLine(tpl.slice(0, match.index));
		}
		if (match[2]) {
			code.push('r.push(String(this.' + match[1] + '));');
		}
		else {
			code.push('r.push(_html(String(this.' + match[1] + ')));');
		}
		tpl = tpl.substring(match.index + match[0].length);
	}
	addLine(tpl);
	code.push('return r.join(\'\');');
	fn = new Function(code.join('\n'));
	this.render = function(model){
		return fn.apply(model);
	};
}

// extends JQuery.form: