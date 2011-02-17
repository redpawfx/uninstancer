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
from maya.OpenMayaFX import *

import ns.py as nspy
import ns.py.Errors
import ns.py.Const

import ns.maya as nsm
import ns.maya.DG

def instancer( dpParticle ):
	fParticle = MFnParticleSystem( dpParticle )
	aInstanceData = fParticle.attribute("instanceData")
	pInstanceData = MPlug( dpParticle.node(), aInstanceData )

	numInstancers = pInstanceData.numElements()
	if 0 == numInstancers:
		raise nspy.Errors.Error( "%s is not associated with an instancer." % fParticle.name() )
	elif numInstancers > 1:
		raise nspy.Errors.Error( "%s has more than one instancer associated with it. Please use the -instancer flag to indicate which instancer should be uninstanced." % fParticle.name() )

	aInstancePointData = fParticle.attribute("instancePointData")
	pInstancePointData = pInstanceData.elementByLogicalIndex( 0 ).child( aInstancePointData )

	destinations = MPlugArray()
	pInstancePointData.connectedTo( destinations, False, True )

	if 0 == destinations.length():
		raise nspy.Errors.Error( "%s is not associated with an instancer." % fParticle.name() )
	elif destinations.length() > 1:
		raise nspy.Errors.Error( "%s has more than one instancer associated with it. Please use the -instancer flag to indicate which instancer should be uninstanced." % fParticle.name() )

	oInstancer = destinations[0].node()
	if not oInstancer.hasFn( MFn.kInstancer ):
		fWrongNode = MFnDependencyNode( oInstancer )
		raise nspy.Errors.Error( "%s is connected to %s which is not a particle instancer." % fParticle.name(), fWrongNode.name() )

	return oInstancer

def runUpTo( dpParticle, time ):
	timeUnit = MTime( time - 1, MTime.uiUnit() )
	fParticle = MFnParticleSystem( dpParticle )
	fParticle.evaluateDynamics( timeUnit, True )

def count( dpParticle ):
	fParticle = MFnParticleSystem( dpParticle )
	numParticles = fParticle.count()
	if MFileIO.isReadingFile():
		# When loading a file MFnParticleSystem doesn't return
		# anything useful. Instead grab an arbitrary per-particle
		# attribute value directly (without using
		# MFnParticleSystem::getPerParticleAttribute which is
		# also useless during file load) and get the
		# number of elements.
		#
		pId0 = NSmayaDG.getPlug( dpParticle.node(), "id0" )
		oId0 = pId0.asMObject()
		fId0 = MFnDoubleArrayData( oId0 )
		numParticles = fId0.length()

	return numParticles;

def _getPerParticleIntData( dpParticle, attrName, value ):
	if MFileIO.isReadingFile():
		plug = NSmayaDG.getPlug( dpParticle.node(), attrName )
		oData = plug.asMObject()
		fData = MFnIntArrayData( oData )
		fData.copyTo( value )
	else:
		fParticle = MFnParticleSystem( dpParticle )
		fParticle.getPerParticleAttribute( attrName, value )

def _getPerParticleVectorData( dpParticle, attrName, value ):
	if MFileIO.isReadingFile():
		plug = NSmayaDG.getPlug( dpParticle.node(), attrName )
		oData = plug.asMObject()
		fData = MFnVectorArrayData( oData )
		fData.copyTo( value )
	else:
		fParticle = MFnParticleSystem( dpParticle )
		fParticle.getPerParticleAttribute( attrName, value )

def _getPerParticleDoubleData( dpParticle, attrName, value ):
	if MFileIO.isReadingFile():
		plug = NSmayaDG.getPlug( dpParticle.node(), attrName )
		oData = plug.asMObject()
		fData = MFnDoubleArrayData( oData )
		fData.copyTo( value )
	else:
		fParticle = MFnParticleSystem( dpParticle )
		fParticle.getPerParticleAttribute( attrName, value )

def getPerParticleVectorData( dpParticle, attrName, value ):
	fParticle = MFnParticleSystem( dpParticle )
	if fParticle.isPerParticleVectorAttribute( attrName ):
		try:
			_getPerParticleVectorData( dpParticle.node(), attrName, value )
		except:
			raise nspy.Errors.Error( "Unable to query per-particle data from %s.%s" % (fParticle.name(), attrName) )
	else:
		raise nspy.Errors.Error( "%s.%s is not a valid per-particle vector attribute." % (fParticle.name(), attrName) )


def getPerParticleIntData( dpParticle, attrName, value ):
	fParticle = MFnParticleSystem( dpParticle )
	if fParticle.isPerParticleIntAttribute( attrName ):
		try:
			_getPerParticleIntData( dpParticle, attrName, value )
		except:
			raise nsm.Errors.MayaError( "Unable to query per-particle data from %s.%s" % (fParticle.name(), attrName) )
	elif fParticle.isPerParticleDoubleAttribute( attrName ):
		# Manually convert the double data to ints.
		#
		temp = MDoubleArray()
		try:
			_getPerParticleDoubleData( dpParticle, attrName, temp)
		except:
			raise nsm.Errors.MayaError( "Unable to query per-particle data from %s.%s" % (fParticle.name(), attrName) )
		
		value.setLength( temp.length() )
		for i in range( 0, temp.length() ):
			value[i] = temp[i]
	else:
		raise nspy.Errors.Error( "%s.%s is not a valid per-particle vector attribute." % (fParticle.name(), attrName) )


def getPerParticleDoubleData( dpParticle, attrName, value ):
	fParticle = MFnParticleSystem( dpParticle )
	if fParticle.isPerParticleDoubleAttribute( attrName ):
		try:
			_getPerParticleDoubleData( dpParticle, attrName, value )
		except:
			raise nsm.Errors.MayaError( "Unable to query per-particle data from %s.%s" % (fParticle.name(), attrName) )
	elif fParticle.isPerParticleIntAttribute( attrName ):
		# Manually convert the double data to ints.
		#
		temp = MIntArray()
		try:
			_getPerParticleIntData( dpParticle, attrName, temp)
		except:
			raise nsm.Errors.MayaError( "Unable to query per-particle data from %s.%s" % (fParticle.name(), attrName) )
		
		value.setLength( temp.length() )
		for i in range( 0, temp.length() ):
			value[i] = temp[i]
	else:
		raise nspy.Errors.Error( "%s.%s is not a valid per-particle vector attribute." % (fParticle.name(), attrName) )

def mappedAttribute( dpParticle, particleOption, instancerIndex ) :
#
# Description:
#		Find the particle system attribute that is mapped to the
#		indicated particle instancing option. Returns "" if there
#		is none.
#
	fParticle = MFnParticleSystem( dpParticle )
	aInstanceData = fParticle.attribute("instanceData")
	pInstanceData = MPlug( dpParticle.node(), aInstanceData )

	aInstanceAttributeMapping = fParticle.attribute("instanceAttributeMapping")
	pInstanceAttrMap = pInstanceData.elementByLogicalIndex( instancerIndex ).child( aInstanceAttributeMapping )

	oArrayData = pInstanceAttrMap.asMObject()
	fArrayData = MFnStringArrayData( oArrayData )
	array = fArrayData.array()
	for i in range( 0, len(array), 2 ):
		if particleOption == array[i]:
			return array[i+1]

	return ""

class IdMapper:
	
	def __init__( self ):
		self._sortedIds = MIntArray()
		self._idIndices = MIntArray()
		self._unsortedIds = MDoubleArray()
			
	def fromParticle( self, oParticle, deepCopy=False ):
		fParticle = MFnParticleSystem( oParticle )
		pIdMapping = nsm.DG.getPlug( node=oParticle, attrName="idMapping" )
		pSortedId = pIdMapping.child( fParticle.attribute( "sortedId" ) )
		pIdIndex = pIdMapping.child( fParticle.attribute( "idIndex" ) )
		pParticleId = nsm.DG.getPlug( node=oParticle, attrName="particleId" )

		fSortedId = MFnIntArrayData( pSortedId.asMObject() )
		fIdIndex = MFnIntArrayData( pIdIndex.asMObject() )
		fParticleId =MFnDoubleArrayData( pParticleId.asMObject() )
	
		self.set( fSortedId.array(),
				  fIdIndex.array(),
				  fParticleId.array(),
				  deepCopy )

	def set( self, sortedIds, idIndices, unsortedIds, deepCopy=False ):
		if deepCopy:
			self._sortedIds.copy(sortedIds)
			self._idIndices.copy(idIndices)
			self._unsortedIds.copy(unsortedIds)
		else:
			# Presumably sortedIds and idIndices were queried from the particle's
			# idMapping attribute. Assigning them to the member variables, therefore,
			# shouldn't do a full copy and instead just assign a reference to the
			# internal Maya data (according to the API docs).
			#
			self._sortedIds = sortedIds
			self._idIndices = idIndices
			self._unsortedIds = unsortedIds

	def idToIndex( self, particleId ):
		# TODO: take advantage of the fact that mSortedIds is sorted and
		#		 do a binary search
		#
		for i in range(self._sortedIds.length()):
			if self._sortedIds[i] == particleId:
				return self._idIndices[i]
		return nspy.Const.kInvalidIndex
	
	def indexToId( self, particleIndex ):
		if particleIndex < self._unsortedIds.length():
			return int(self._unsortedIds[ particleIndex ])
		return nspy.Const.kInvalidIndex

