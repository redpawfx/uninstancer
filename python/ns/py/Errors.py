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


class Error( Exception ):
	"""Base exception class.
	
	Contains a string with an optional error message."""
	
	def __init__( self, message ):
		self._message = message

	def __str__( self ):
		return self._message

	def __repr__( self ):
		return self._message

	def __unicode__( self ):
		return self._message
		
	def msg( self ):
		return self._message
	
class UnitializedError( Error ):
	"""Thrown when an unitialized variable is accessed."""
	
	def __init__( self, message ):
		Error.__init__( self, message )


class BadArgumentError( Error ):
	"""Thrown when an invalid argument is provided."""

	def __init__( self, message ):
		Error.__init__( self, message )


class OutOfBoundsError( Error ):
	"""Thrown when the value of an argument is outside the allow range."""

	def __init__( self, message ):
		Error.__init__( self, message )


class UnsupportedError( Error ):
	"""Thrown when an implemented feature is invoked."""

	def __init__( self, message ):
		Error.__init__( self, message )


class ThirdPartyError( Error ):
	"""Thrown when a third party library has an error."""

	def __init__( self, message ):
		Error.__init__( self, message )


class SilentError( Error ):
	"""Thrown when an error has occurred but no message should be printed.
	
	Either there's none to print or something else has already printed it."""

	def __init__( self, message ):
		Error.__init__( self, message )
		

class AbortError( Error ):
	"""Thrown when an operation has been aborted either by the user or
	   otherwise."""

	def __init__( self, message ):
		Error.__init__( self, message )
		
