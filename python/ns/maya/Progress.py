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

#
# Later this can be made into a class to support progress windows
# on different platforms (e.g. Max vs. Maya, or Win vs. Linux)
#

import sys

from maya.OpenMayaUI import MProgressWindow
from maya.OpenMaya import MGlobal

import ns.py as npy
import ns.py.Errors

_uiProgress = False

def reset( maxRange ):
	global _uiProgress
	_uiProgress = (MGlobal.mayaState() == MGlobal.kInteractive)
	if _uiProgress:
		MProgressWindow.reserve()
		MProgressWindow.setProgressRange( 0, maxRange )
		MProgressWindow.setProgress( 0 )
		MProgressWindow.startProgress()
		MProgressWindow.setInterruptable( True )
	
def stop():
	if _uiProgress:
		MProgressWindow.endProgress()

def checkForCancel():
	if _uiProgress:
		if MProgressWindow.isCancelled():
			raise npy.Errors.AbortError("Operation cancelled by user")

def setTitle( title ):
	if _uiProgress:
		MProgressWindow.setTitle( title )

def setProgressStatus( status ):
	if _uiProgress:
		MProgressWindow.setProgressStatus( status )
	else:
		print >> sys.stderr, "### %s" % status
	
def setProgress( progress ):
	if _uiProgress:
		MProgressWindow.setProgress( progress )
		checkForCancel()
	
def advanceProgress( progress ):
	if _uiProgress:
		MProgressWindow.advanceProgress( progress )
		checkForCancel()


