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

from maya.OpenMaya import *

import ns.maya as nsm
import ns.maya.ObjectHandle

class Operation:
	'''Abstract base class for an undoable operation. Based on the Command
	   pattern - each operation knows how to do and undo itself.'''
	
	def __init__(self):
		raise NotImplementedError
	
	def doIt( self ):
		raise NotImplementedError
	
	def undoIt( self ):
		raise NotImplementedError
	

class NativeOp( Operation ):
	'''A wrapper operation that contains a native modifier (ie MDagModifier).
	   Doing/undoing this op just delegates to the native modifier.'''
	
	def __init__( self ):
		self._dagModifier = MDagModifier()
	
	def doIt( self ):
		self._dagModifier.doIt()
	
	def undoIt( self ):
		self._dagModifier.undoIt()
	
	def nativeModifier( self ):
		return self._dagModifier
	
class RemoveChildOp( Operation ):
	'''A wrapper operation that contains a native modifier (ie MDagModifier).
	   Doing/undoing this op just delegates to the native modifier.'''
	
	def __init__( self, oParent, index ):
		fParent = MFnDagNode( oParent )
		self._initialize( oParent, fParent.child( index ) )
	
	def doIt( self ):
		fParent = MFnDagNode( self._parentHandle.object() )
		fParent.removeChild( self._childHandle.object() )
	
	def undoIt( self ):
		fParent = MFnDagNode( self._parentHandle.object() )
		fParent.addChild( self._childHandle.object(),
						  MFnDagNode.kNextPos,
						  True )
	
	def _initialize( self, oParent, oChild ):
		self._parentHandle = nsm.ObjectHandle.ObjectHandle( oParent )
		dpaChild = MDagPathArray()
		MDagPath.getAllPathsTo( oChild, dpaChild )
		foundPath = False
		for dp in dpaChild:
			dp.pop()
			if dp.node() != oParent:
				dp.push( oChild )
				self._childHandle = nsm.ObjectHandle.ObjectHandle( oChild,
																   dp.partialPathName() )
				foundPath = True
				break
		if not foundPath:
			self._childHandle = nsm.ObjectHandle.ObjectHandle( oChild )
