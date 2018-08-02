// patch for lower-version IE:
if (!window.console) {
	window.console = {
		log: function() {},
		info: function() {},
		error: function() {},
		warn: function() {},
		debug: function() {}
	};
}

// patch for string.strim():
if (!String.prototype.trim) {
	String.prototype.trim = function() {
		return this.replace(/^\s+|\s+/g, '');
	}
}

// patch for Number.toDateTime():
if (!Number.prototype.toDateTime) {
	var replaces = {
		'yyyy':function(dt) {
			return dt.getFullYear().toString();
		},
		'yy':function(dt) {
			return (dt.getFullYear() % 100).toString();
		},
		'MM':function(dt) {
			var m = dt.getMonth() + 1;
			return m < 10 ? '0' + m : m.toString();
		},
		'M':function(dt) {
			var m = dt.getMonth() + 1;
			return m.toString();
		},
		'dd':function(dt) {
			var d = dt.getDate();
			return d < 10 ? '0' + d : d.toString(); 
		},
		'd':function(dt) {
			var d = dt.getDate();
			return d.toString();
		},
		'hh':function(dt) {
			var h = dt.getHours();
			return h < 10 ? '0' + h : h.toString();
		},
		'h':function(dt) {
			var h = dt.getHours();
			return h.toString();
		},
		'mm':function(dt) {
			var m = dt.getMinutes();
			return m < 10 ? '0' + m : m.toString();
		},
		'm':function(dt) {
			var m = dt.getMinutes();
			return m.toString();
		},
		'ss':function(dt) {
			var s = dt.getSeconds();
			return s < 10 ? '0' + s : s.toString();
		},
		's':function(dt) {
			var s = dt.getSeconds();
			return s.toString();
		},
		'a':function(dt) {
			var h = dt.getHours();
			return h < 12 ? 'AM' : 'PM';
		}
	};
	var token = /([a-zA-Z]+)/;
	Number.prototype.toDateTime = function(format) {
		var fmt = format || 'yyyy-MM-dd hh:mm:ss'
		var dt = new Date(this * 1000);
		var arr = fmt.split(token);
		for (var i=0; i<arr.length; i++) {
			var s = arr[i];
			if(s && s in replaces) {
				arr[i] = replaces[s](dt);
			}
		}
		return arr.join('');
	};
}

// escape html
function encodeHtml(str) {
	return String(str)
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/'/, '&#39;')
		.replace(/</, '&lt;')
		.replace(/>/, '&gt;')
}

// parse query string as object
function parseQueryString() {
	/*
	The Location interface represents the location (URL) of the object it is linked to. 
	Changes done on it are reflected on the object it relates to. Both the Document and 
	Window interface have such a linked Location, accessible via Document.location and 
	Window.location respectively.

	search - Is a DOMString containing a '?' followed by the parameters or "querystring" of the URL. 
	Modern browsers provide URLSearchParams and URL.searchParams to make it easy to parse out the parameters from the querystring.
	*/
	var 
		q = location.search,
		r = {},
		i, pos, s, qs;
	if (q && q.charAt(0) === '?') {
		qs = q.substring(1).split('&');
		for(i=0; i<qs.length; i++) {
			s = qs[i];
			pos = s.indexOf('=');
			if (pos <= 0) {
				continue;
			}
			r[s.substring(0, pos)] = decodeURIComponent(s.substring(pos+1)).replace(/\+/g, ' ');
		}
	}

	return r;
}

// switch page
function gotoPage(i) {
	var r = parseQueryString();
	r.page = i;
	/* 
	location.assign - Loads the resource at the URL provided in parameter.
	
	$.param - Create a serialized representation of an array, a plain object, 
	or a jQuery object suitable for use in a URL query string or Ajax request. 
	In case a jQuery object is passed, it should contain input elements with 
	name/value properties
	*/
	location.assign('?' + $.param(r));
}

// refresh
function refresh() {
	var 
		t = new Date().getTime(),
		// pathname - Is a DOMString containing an initial '/' followed by the path of the URL.
		url = location.pathname;
	if(location.search) {
		url = url + location.search + '&t=' + t;
	} else {
		url = url + '?t=' + t;
	}
	location.assign(url);
}

function toSmartDate(timestamp) {
	if(typeof(timestamp) === 'string') {
		timestamp = parseInt(timestamp);
	}
	if(isNAN(timestamp)) {
		return '';
	}

	var 
		today = new Date(),
		// milliseconds
		now = today.getTime(),
		s = '1分钟前',
		t = now - timestamp;
	if (t > 604800000) {
		// 1 week ago
		var that = new Date(timestamp);
		var 
			y = that.getFullYear(),
			m = that.getMonth() + 1,
			d = that.getDate(),
			hh = that.getHours(),
			mm = that.getMinutes();
		s = y === today.getFullYear ? '' : y + '年';
		s = s + m + '月' + d + '日' + hh + ':' + (mm < 10 ? '0' : '') + mm;
	} 
	else if (t >= 86400000) {
		// 1-6 days ago
		s = s = Math.floor(t / 86400000) + '天前';
	} 
	else if (t >= 3600000) {
		// 1-23 hours ago
		s = Math.floor(t / 3600000) + '小时前';
	} 
	else if (t >= 60000) {
		// 1-60 minute ago
		s = Math.floor(t / 60000) + '分钟前';
	} 
	else {
		// 1-59 seconds
		s = Math.floor(t / 1000) + '秒以前';
	}

	return s;
}

$(function() {
	$('.x-smartdate').each(function() {
		$(this).removeClass('x-smartdate').text(toSmartDate($(this).attr('date')))
	});
});

// JS Template
function Template(tpl) {
	var
		fn,
		match,
		code = ['var r=[];\nvar _html = function (str) { return str.replace(/&/g, \'&amp;\').replace(/"/g, \'&quot;\').replace(/\'/g, \'&#39;\').replace(/</g, \'&lt;\').replace(/>/g, \'&gt;\'); };'],
		re = /\{\s*([a-zA-Z\.\_0-9()]+)(\s*\|\s*safe)?\s*\}/m,
		addLine = function (text) {
			code.push('r.push(\'' + text.replace(/\'/g, '\\\'').replace(/\n/g, '\\n').replace(/\r/g, '\\r') + '\');');
		};
	while (match = re.exec(tpl)) {
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
	this.render = function (model) {
		return fn.apply(model);
	};
}

// extends jQuery.form
$(function () {
	console.log('Extends $form...');
	$.fn.extend({
		// 用于展示表单错误
		showFormError: function (err) {
			return this.each(function () {
				var
					$form = $(this),
					// 用于展示错误的元素
					$alert = $form && $form.find('.uk-alert-danger'),
					// 错误对象
					fieldName = err && err.data;
				if (! $form.is('form')) {
					console.error('Cannot call showFormError() on non-form object.');
					return;
				}
				$form.find('input').removeClass('uk-form-danger');
				$form.find('select').removeClass('uk-form-danger');
				$form.find('textarea').removeClass('uk-form-danger');
				if ($alert.length === 0) {
					console.warn('Cannot find .uk-alert-danger element.');
					return;
				}
				if (err) {
					$alert.text(err.message ? err.message : (err.error ? err.error : err)).removeClass('uk-hidden').show();
					/* 
						offset - Get the current coordinates of the first element in the set of matched elements, 
						relative to the document.
						scrollTop - Get the current vertical position of the scroll bar for the first element in 
						the set of matched elements or set the vertical position of the scroll bar for every matched 
						element.
						当一个元素的实际高度超过其显示区域的高度时，在一定的设置下，浏览器会为该元素显示相应的垂直滚动条。
						此时，scrollTop()返回的就是该元素在可见区域之上被隐藏部分的高度(单位：像素)。
						如果垂直滚动条在最上面(也就是可见区域之上没有被隐藏的内容)，或者当前元素是不可垂直滚动的，
						那么scrollTop()将返回0。
					*/
					if (($alert.offset().top - 60) < $(window).scrollTop()) {
						$('html,body').animate({ scrollTop: $alert.offset().top - 60 });
					}
					if (fieldName) {
						$form.find('[name=' + fieldName + ']').addClass('uk-form-danger');
					}
				}
				else {
					$alert.addClass('uk-hidden').hide();
					$form.find('.uk-form-danger').removeClass('uk-form-danger');
				}
			});
		},
		// 用于展示表单加载样式
		showFormLoading: function (isLoading) {
			return this.each(function () {
				var
					$form = $(this),
					$submit = $form && $form.find('button[type=submit]'),
					$buttons = $form && $form.find('button');
					$i = $submit && $submit.find('i'),
					iconClass = $i && $i.attr('class');
				if (! $form.is('form')) {
					console.error('Cannot call showFormLoading() on non-form object.');
					return;
				}
				if (!iconClass || iconClass.indexOf('uk-icon') < 0) {
					console.warn('Icon <i class="uk-icon-*>" not found.');
					return;
				}
				if (isLoading) {
					$buttons.attr('disabled', 'disabled');
					$i && $i.addClass('uk-icon-spinner').addClass('uk-icon-spin');
				}
				else {
					$buttons.removeAttr('disabled');
					$i && $i.removeClass('uk-icon-spinner').removeClass('uk-icon-spin');
				}
			});
		},
		// 表单发起AJAX请求
		postJSON: function (url, data, callback) {
			if (arguments.length===2) {
				callback = data;
				data = {};
			}
			return this.each(function () {
				var $form = $(this);
				$form.showFormError();
				$form.showFormLoading(true);
				_httpJSON('POST', url, data, function (err, r) {
					if (err) {
						$form.showFormError(err);
						$form.showFormLoading(false);
					}
					callback && callback(err, r);
				});
			});
		}
	});
});

// ajax submit form
function _httpJSON(method, url, data, callback) {
	var opt = {
		type: method,
		dataType: 'json'
	};
	if (method === 'GET') {
		opt.url = url + '?' + data;
	}
	if (method === 'POST') {
		opt.url = url;
		opt.data = JSON.stringify(data || {});
		opt.contentType = 'application/json';
	}
	// An alternative construct to the success callback option
	$.ajax(opt).done(function(data, textStatus, jqXHR){
		if (data && data.error) {
			return callback(data);
		}
		return callback(null, data);
	// An alternative construct to the error callback option
	}).fail(function(jqXHR, textStatus, errorThrown){
		return callback({'error': 'http_bad_response', 'data': '' + jqXHR.status, 'message': '网络好像出问题了 (HTTP ' + jqXHR.status + ')'});
	});
}

// get for ajax
function getJSON(url, data, callback) {
	if (arguments.length === 2) {
		callback = data;
		data = {};
	}
	if (typeof(data) === 'object') {
		var arr = [];
		/*
		A generic iterator function, which can be used to seamlessly iterate over both objects and arrays. 
		Arrays and array-like objects with a length property (such as a function's arguments object) are 
		iterated by numeric index, from 0 to length-1. Other objects are iterated via their named properties.
		*/
		$.each(data, function(k, v) {
			arr.push(k + '=' + encodeURIComponent(v));
		});
		data = arr.join('&');
	}
	_httpJSON('GET', url, data, callback)
}

// post for ajax
function postJSON(url, data, callback) {
	if(arguments.length === 2) {
		callback = data;
		data = {};
	}
	_httpJSON('POST', url, data, callback)
}

// 展示错误
function _display_error($obj, err) {
	if ($obj.is(':visible')) {
		$obj.hide();
	}

	var msg = err.message || String(err);
	var L = ['<div class="uk-alert uk-alert-danger">'];
	L.push('<p>Error: ');
	L.push(msg);
	L.push('</p><p>Code: ');
	L.push(err.error || '500');
	L.push('</p></div>');
	// Display the matched elements with a sliding motion.
	$obj.html(L.join('')).slideDown();
}

// error
function error(err) {
	_display_error($('#error'), err);
}

// fatal
function fatal(err) {
	_display_error($('#loading'), err);
}

// extend Vue
if (typeof(Vue)!=='undefined') {
	Vue.filter('datetime', function (value) {
		var d = value;
		if (typeof(value)==='number') {
			d = new Date(value);
		}
		return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate() + ' ' + d.getHours() + ':' + d.getMinutes();
	});
	Vue.component('pagination', {
		template: '<ul class="uk-pagination">' +
				'<li v-if="! has_previous" class="uk-disabled"><span><i class="uk-icon-angle-double-left"></i></span></li>' +
				'<li v-if="has_previous"><a v-attr="onclick:\'gotoPage(\' + (page_index-1) + \')\'" href="#0"><i class="uk-icon-angle-double-left"></i></a></li>' +
				'<li class="uk-active"><span v-text="page_index"></span></li>' +
				'<li v-if="! has_next" class="uk-disabled"><span><i class="uk-icon-angle-double-right"></i></span></li>' +
				'<li v-if="has_next"><a v-attr="onclick:\'gotoPage(\' + (page_index+1) + \')\'" href="#0"><i class="uk-icon-angle-double-right"></i></a></li>' +
			'</ul>'
	});
}

$(function() {
	if (location.pathname === '/' || location.pathname.indexOf('/blog')===0) {
		$('li[data-url=blogs]').addClass('uk-active');
	}
});

// init:
function _bindSubmit($form) {
	$form.submit(function (event) {
		event.preventDefault();
		showFormError($form, null);
		var
			fn_error = $form.attr('fn-error'),
			fn_success = $form.attr('fn-success'),
			fn_data = $form.attr('fn-data'),
			data = fn_data ? window[fn_data]($form) : $form.serialize();
		var
			$submit = $form.find('button[type=submit]'),
			$i = $submit.find('i'),
			iconClass = $i.attr('class');
		if (!iconClass || iconClass.indexOf('uk-icon') < 0) {
			$i = undefined;
		}
		$submit.attr('disabled', 'disabled');
		$i && $i.addClass('uk-icon-spinner').addClass('uk-icon-spin');
		postJSON($form.attr('action-url'), data, function (err, result) {
			$i && $i.removeClass('uk-icon-spinner').removeClass('uk-icon-spin');
			if (err) {
				console.log('postJSON failed: ' + JSON.stringify(err));
				$submit.removeAttr('disabled');
				fn_error ? fn_error() : showFormError($form, err);
			}
			else {
				var r = fn_success ? window[fn_success](result) : false;
				if (r===false) {
					$submit.removeAttr('disabled');
				}
			}
		});
	});
	$form.find('button[type=submit]').removeAttr('disabled');
}

$(function () {
	$('form').each(function () {
		var $form = $(this);
		if ($form.attr('action-url')) {
			_bindSubmit($form);
		}
	});
});
