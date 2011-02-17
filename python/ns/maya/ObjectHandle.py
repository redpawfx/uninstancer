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

from maya.OpenMaya import *

import ns.py as nspy
import ns.py.Errors

import ns.maya as nsm


class ObjectHandle:
	
	def __init__( self,
			 	  object = MObject.kNullObj,
			 	  objectName = "" ):
		self._objectHandle = MObjectHandle( object )
		if object.isNull():
			self._isValid = False
			self._objectName = ""
		else:
			self._isValid = True
			if objectName:
				self._objectName = objectName
			elif object.hasFn( MFn.kDagNode ):
				# Object is a DAG node, get its unique dag path
				# name.
				#
				dpObject = MDagPath()
				MDagPath.getAPathTo( object, dpObject )
				self._objectName = dpObject.partialPathName()
			else:
				fObject = MFnDependencyNode( object )
				self._objectName = fObject.name()
				
	def isValid( self ):
		return self._isValid

	def clear( self ):
		self._objectHandle = MObjectHandle()
		self._objectName = ""
		self._isValid = False

	def object( self ):
		if not self.isValid():
			return MObject.kNullObj
		
		if not self._objectHandle.isValid():
			# Handle is no longer valid, search for the object name
			# if it exists.
			#
			selList = MSelectionList();
			MGlobal.getSelectionListByName( self._objectName, selList )
			if selList.isEmpty():
				self._isValid = False
				return MObject.kNullObj
			elif selList.length() > 1:
				raise nspy.Errors.Error( "More than one node matches name " + self._objectName )
			else:
				validObject = MObject()
				selList.getDependNode( 0, validObject )
				self._objectHandle = MObjectHandle( validObject )

		return self._objectHandle.objectRef()
