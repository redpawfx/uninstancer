# The MIT License
#	
# Copyright (c) 2009 James Piechota
#	
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.	

import time

class _Timer:
	def __init__(self):
		self.start = -1.0
		self.elapsed = 0.0

_timers = {}

def _getTimer(name):
	timer = None
	try:
		timer = _timers[name]
	except:
		timer = _Timer()
		_timers[name] = timer
	return timer

def start(name):
	# If the timer was already running this will restart it
	_getTimer(name).start = time.time()
	
def stop(name):
	timer = _getTimer(name)
	if timer.start >= 0:
		timer.elapsed += time.time() - timer.start
		timer.start = -1.0
	return timer.elapsed

def elapsed(name):
	return _getTimer(name).elapsed

def names():
	return _timers.keys()

def deleteAll():
	_timers = {}

def delete(name):
	try:
		_timers.pop(name)
	except:
		pass