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

import sys

import maya.OpenMaya as OpenMaya

import ns.maya as nsm
import ns.maya.ModifierOps


class MayaModifier:
	'''Wrapper around MDagModifier to add support for additional undoable
	   operations. New operations can be added by extending NSmayaOperation,
	   built-in undoable options can be added to the NSmayaModifier undo stack
	   by calling nativeModifier().'''
	
	def __init__( self ):
		self.clear()
	
	def doIt( self ):
		'''Perform all operations that have not yet been done. If
		   a native modifier is at the top of the stack it will
		   always be done (because we don't know if the user has
		   used the native modifier since the last call to doIt())'''
		if self.__nativeModifierAvailable and (len( self.__ops ) == self.__doneIndex):
			# If mDoneIndex equals mOps.size() it means no new ops
			# have been added since the last call to doIt(). However,
			# as long as a native modifier op is at the top of
			# the stack, we want to doIt() whenever the NSmayaModifier
			# is done. This is because the native modifier has its
			# own stack of ops that can be added to independently of
			# the NSmayaModifier - new ops may have been added to
			# the native modifier since the last doIt() call.
			self.__ops[-1].doIt()
		else:
			for i in range( self.__doneIndex, len(self.__ops) ):
				self.__ops[i].doIt()
				self.__doneIndex = i + 1
	
	def _undo( self, high, low ):
		'''Undo all operations from mDoneIndex down to and including
		   the operation at downToIndex.
		   doneIndex stores the index one beyond the last "done" operation
		   and will be decremented after every operation is undone. (i.e.
		   after an operation is undone, doneIndex assumes its index).'''
		doneIndex = self.__doneIndex
		if high < low:
			return doneIndex
		
		for i in range( high + 1, low, -1 ):
			self.__ops[i-1].undoIt()
			doneIndex = self.__doneIndex
		
		return doneIndex
			
	def undoIt( self ):
		'''Undo all operations'''
		self.__doneIndex = self._undo( self.__doneIndex - 1, 0 )
	
	def clear( self ):
		'''Clear all operations'''
		self.__doneIndex = 0
		self.__nativeModifierAvailable = False
		self.__ops = []
	
	def nativeModifier( self, reuse=True ):
		'''If reuse is true and the last op pushed is a MayaNativeOp
		   return the underlying MDagModifier. Otherwise push an MayaNativeOp
		   and return its underlying MDagModifier. This guarantees that native
		   operations are all grouped together.'''
		
		op = None
		if reuse and self.__nativeModifierAvailable:
			op = self.__ops[-1]
		else:
			op = nsm.ModifierOps.NativeOp()
			addOp( op )
			self.__nativeModifierAvailable = True
			
		return op.nativeModifier()
	
	def addOp( self, op ):
		self.__ops.append( op )
		self.__nativeModifierAvailable = False

	
	def removeChildAt( self, oParent, index ):
		self.addOp( nsm.ModifierOps.RemoveChildOp( oParent, index ) )
	
	
	