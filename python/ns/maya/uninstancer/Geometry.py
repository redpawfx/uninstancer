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
from maya.OpenMayaAnim import *
import maya.cmds as mc

import ns
import ns.py as nspy
import ns.py.Timer

import ns.maya as nsm
import ns.maya.InstancerUtil


class eLife:
	aliveLastFrame, aliveThisFrame, dead, numValues = range(4)

class Geometry:
	def __init__(self):
		self.root = MDagPath()
		self.shapes = []
		
	def fromInstancer(self, dpInstancer, index):
		MDagPath.getAPathTo( nsm.InstancerUtil.getInstance( dpInstancer, index ),
							 self.root )
		self._fillShapes()
	
	def fromTransform(self, dpTransform):
		self.root = dpTransform
		self._fillShapes()
		
	def duplicate(self, copyAsInstance, suffix):
		dpDuplicate = self._duplicate( self.root, copyAsInstance, suffix )
		dup = Geometry()
		dup.fromTransform(dpDuplicate)
		return dup
		
	def _fillShapes(self):
		'''Get all the shapes that are descendants of the root transform.'''
		it = MItDag( MItDag.kDepthFirst, MFn.kShape )
		it.reset( self.root, MItDag.kDepthFirst, MFn.kShape )

		self.shapes = []
		while not it.isDone():
			if it.item().hasFn( MFn.kShape ):
				self.shapes.append( it.item() )
			it.next()

	def _duplicate( self, dpOriginal, copyAsInstance, suffix ):
		fInstanced = MFnDependencyNode( dpOriginal.transform() )
		
		# We need the full path to the instanced object, but if that
		# object is a shape we actually want the path to the shape's
		# parent transform (this is so that the instance and duplicate
		# commands work right)
		#
		originalFullName = ""
		if dpOriginal.node().hasFn( MFn.kTransform ):
			originalFullName = dpOriginal.fullPathName()
		else:
			MDagPath.getAPathTo( dpOriginal.transform(), dpOriginalTransform )
			originalFullName = dpOriginalTransform.fullPathName()
		
		duplicateNames = []
		if copyAsInstance:
			duplicateNames = mc.instance( originalFullName )
		else:
			duplicateNames = mc.duplicate( originalFullName, rr=True )
	
		duplicateList = MSelectionList()
		MGlobal.getSelectionListByName( duplicateNames[0], duplicateList )
		dpDuplicate = MDagPath()
		duplicateList.getDagPath( 0, dpDuplicate )
		
		self._renameHierarchy( dpDuplicate, dpOriginal, suffix )
		
		if not dpDuplicate.node().hasFn( MFn.kTransform ):
			raise ns.Errors.UnsupportedError( "Currently only instanced transforms are supported." )
			
		fDuplicate = MFnTransform( dpDuplicate.transform() )
		if not fDuplicate.parent(0).hasFn( MFn.kWorld ):
			oDuplicate = dpDuplicate.transform()
			modifier = MDagModifier()
			modifier.reparentNode( oDuplicate )
			modifier.doIt()
			MDagPath.getAPathTo( oDuplicate, dpDuplicate )
		
		return dpDuplicate
				
	def _renameHierarchy( self, dpDuplicate, dpInstance, suffix ):
		itDup = MItDag()
		itInst = MItDag()
		itDup.reset( dpDuplicate )
		itInst.reset( dpInstance )
		
		dupRootName = ""
		
		while not itDup.isDone():
			# Always skip instanced nodes. If we are copying as instance
			# then we want to make sure we don't rename the original
			# nodes (this may cause trouble when baking to blendshapes
			# but that's okay cause we can't bake to blendshapes when
			# copying as instance). If we are not copying as instance,
			# the duplicates will only contain uninstanced nodes regardless
			# of any instancing in the original (the "duplicate -rr"
			# uninstances stuff as it goes)
			#
			if itDup.instanceCount( True ) <= 1:
				fInst = MFnDependencyNode( itInst.item() )
				dupName = fInst.name() + suffix
				
				dpDup = MDagPath()
				itDup.getPath( dpDup )
				
				name = ""
				if itDup.item().hasFn( MFn.kShape ):
					name = mc.rename( dpDup.fullPathName(), dupName )
				else:
					name = mc.rename( dpDup.fullPathName(), dupName, ignoreShape=True )

				if not dupRootName:
					dupRootName = name

			itInst.next()
			itDup.next()
		
		return dupRootName
			
class BlendShape(Geometry):
	def __init__(self, maxTargets):
		Geometry.__init__( self )
		self._maxTargets = maxTargets
		self._targets = [ False ] * maxTargets
		self._fBlendShapes = []
		self._fWeightAnims = []
	
	def setBaseShape(self, geometry):
		self.root = geometry.root
		self.shapes = geometry.shapes
		self._createBlendShape()
	
	def fromInstancer(self, dpInstancer, index):
		Geometry.fromInstancer( self, dpInstancer, index )
		self._createBlendShape()
	
	def addBlendShapeTarget(self, target, index):
		if self._targets[index]:
			# This instanced object has already been added as a target.
			#
			return
		
		assert len( self._fBlendShapes ) == len( self.shapes )
		
		for i in range( len( self._fBlendShapes ) ):
			self._fBlendShapes[i].addTarget( self.shapes[i],
											 0,
											 target.shapes[i],
											 self._blendShapeWeight( index ) )
			
		self._targets[index] = True

	def keyWeight(self, time, index):
		weight = self._blendShapeWeight( index )
		for fWeightAnim in self._fWeightAnims:
			fWeightAnim.addKeyframe( time, weight )

	def _blendShapeWeight( self, index ):
		weightIncrement = 1.0 / float( self._maxTargets )
		weight = float( index + 1 ) * weightIncrement
		return round( weight, 3 )
					
	def _createBlendShape( self ):
		numShapes = len( self.shapes )
		self._fBlendShapes.extend( [ MFnBlendShapeDeformer() ] * numShapes )
		self._fWeightAnims.extend( [ MFnAnimCurve() ] * numShapes )
		
		for i in range( numShapes ):
			self._fBlendShapes[i].create( self.shapes[i],
										  MFnBlendShapeDeformer.kLocalOrigin )
			pWeight = self._fBlendShapes[i].findPlug( "weight", False ).elementByLogicalIndex( 0 )
			self._fWeightAnims[i].create( pWeight )			

class Uninstance:
	def __init__(self, instancer):
		self._instancer = instancer
		self._paths = []
		
	def getPaths(self):
		return self._paths
	
	def bake(self, particleIndex):
		pass
	
	def endFrame(self):
		pass
	
	def finalize(self):
		pass
	
class StaticUninstance(Uninstance):
	def __init__(self, instancer):
		Uninstance.__init__( self, instancer )
	
	def bake(self, particleIndex):
		objectIndex = self._instancer.getObjectIndex( particleIndex )
		if not self._instancer.getInstance( objectIndex ).root.isValid():
			# This shouldn't happen, but we should carry on
			# regardless.
			#
			assert 0
			return
		
		# Transform its base matrix by the particle transformation
		#
		paths = MDagPathArray()
		matrix = MMatrix()
		self._instancer.fInstancer.instancesForParticle( particleIndex, paths, matrix )
	 
		newMatrix = MMatrix()
		newMatrix.setToProduct( self._instancer.getMatrix( objectIndex ), matrix )
		
		# Duplicate the appropriate instanced object.
		#
		dup = self._instancer.duplicateInstance( objectIndex )
		self._paths.append( dup.root )
		
		fNewTransform = MFnTransform( dup.root.transform() )
		fNewTransform.set( MTransformationMatrix( newMatrix ) )
		

	
class AnimatedUninstance(Uninstance):
	def __init__(self, instancer):
		Uninstance.__init__( self, instancer )
		self._initialized = False
		self._geometry = Geometry()
		self._objectIndex = -1
		self._life = eLife.numValues
		
		self._fTxAnim = MFnAnimCurve()
		self._fTyAnim = MFnAnimCurve()
		self._fTzAnim = MFnAnimCurve()
		
		self._fRxAnim = MFnAnimCurve()
		self._fRyAnim = MFnAnimCurve()
		self._fRzAnim = MFnAnimCurve()
		
		self._fSxAnim = MFnAnimCurve()
		self._fSyAnim = MFnAnimCurve()
		self._fSzAnim = MFnAnimCurve()
		
		self._fVAnim = MFnAnimCurve()
		
#		self._times = MTimeArray()
#		self._txKeys = MDoubleArray()
#		self._tyKeys = MDoubleArray()
#		self._tzKeys = MDoubleArray()
#		self._rxKeys = MDoubleArray()
#		self._ryKeys = MDoubleArray()
#		self._rzKeys = MDoubleArray()
#		self._sxKeys = MDoubleArray()
#		self._syKeys = MDoubleArray()
#		self._szKeys = MDoubleArray()
		
	def bake(self, particleIndex):
		objectIndex = self._instancer.getObjectIndex( particleIndex )
		
		if not self._initialized:
			self._initialize( objectIndex )
			
		self._life = eLife.aliveThisFrame

		# Transform its base matrix by the particle transformation
		#
		paths = MDagPathArray()
		matrix = MMatrix()
		self._instancer.fInstancer.instancesForParticle( particleIndex, paths, matrix )
	 
		newMatrix = MMatrix()
		newMatrix.setToProduct( self._instancer.getMatrix( objectIndex ), matrix )

		transformation = MTransformationMatrix( newMatrix )
		translation = transformation.getTranslation( MSpace.kTransform )
		rotation = transformation.eulerRotation()
		scaleUtil = MScriptUtil()
		scaleUtil.createFromDouble( 0.0, 0.0, 0.0 );
		scalePtr = scaleUtil.asDoublePtr()
		transformation.getScale( scalePtr, MSpace.kTransform )

		time = MAnimControl.currentTime()
		self._fTxAnim.addKeyframe( time, translation.x )
		self._fTyAnim.addKeyframe( time, translation.y )
		self._fTzAnim.addKeyframe( time, translation.z )

		self._fRxAnim.addKeyframe( time, rotation.x )
		self._fRyAnim.addKeyframe( time, rotation.y )
		self._fRzAnim.addKeyframe( time, rotation.z )
		
		self._fSxAnim.addKeyframe( time, MScriptUtil.getDoubleArrayItem( scalePtr, 0 ) )
		self._fSyAnim.addKeyframe( time, MScriptUtil.getDoubleArrayItem( scalePtr, 1 ) )
		self._fSzAnim.addKeyframe( time, MScriptUtil.getDoubleArrayItem( scalePtr, 2 ) )

#		Once MFnAnimCurve.setKeys(...) is fixed, we can set all the keys
#		at once for a noticeable speed up.
#		self._times.append( time )
#		self._txKeys.append( translation.x )
#		self._tyKeys.append( translation.y )
#		self._tzKeys.append( translation.z )
#		self._rxKeys.append( rotation.x )
#		self._ryKeys.append( rotation.y )
#		self._rzKeys.append( rotation.z )
#		self._sxKeys.append( MScriptUtil.getDoubleArrayItem( scalePtr, 0 ) )
#		self._syKeys.append( MScriptUtil.getDoubleArrayItem( scalePtr, 1 ) )
#		self._szKeys.append( MScriptUtil.getDoubleArrayItem( scalePtr, 2 ) )

		
		if objectIndex != self._objectIndex:
			# This particle's objectIndex has changed - we may
			# need to create a blendShape and/or add a blendShape
			# target.
			#
			# However, if we're copying as instance then the cycle type
			# must be set to Sequential - we can't handle copying as
			# instance a blendshape with unpredictable target transitions.
			# The instancer will only have created blendshapes if the
			# cycle type is Sequential and we're copying as instance.
			#
			if self._instancer.copyAsInstance():
				if not self._instancer.hasBlendShapes():
					raise nspy.Errors.BadArgumentError("Instancer Cycle must be 'Sequential' when using 'Copy as Instance' to bake Animation. Please uncheck 'Copy as Instance'.")
			else:				
				# If _geometry is not a BlendShape then we are about
				# to add our first blendshape target, so convert
				# _geometry from Geometry to BlendShape
				#
				if not isinstance( self._geometry, BlendShape ):
					blendShape = BlendShape( self._instancer.numInstances() )
					blendShape.setBaseShape( self._geometry )
					# The base shape should be used for all frames up until this
					# frame. The baseshape is represented by index -1.
					#
					prevFrame = MTime( time.value() - 1, MTime.uiUnit() )
					blendShape.keyWeight( prevFrame, -1 )
					self._geometry = blendShape
				
				self._geometry.addBlendShapeTarget( self._instancer.getInstance(objectIndex),
										   			objectIndex )
			
		# If this particle's objectIndex has ever changed we will be
		# baking to a blendShape and thus will need to key every
		# frame - even if it hasn't changed on this particular
		# frame (otherwise we may get unwanted interpolation).
		#
		if not self._instancer.copyAsInstance() and isinstance( self._geometry, BlendShape ):
			self._geometry.keyWeight( time, objectIndex )
		
		self._objectIndex = objectIndex
		
	def endFrame(self):
		if eLife.aliveThisFrame == self._life:
			self._life = eLife.aliveLastFrame
		elif eLife.aliveLastFrame == self._life:
			self._life = eLife.dead
			self._fVAnim.addKeyframe( MAnimControl.currentTime(), 0.0,
								 	   MFnAnimCurve.kTangentStep,
								 	   MFnAnimCurve.kTangentStep )
		
	def finalize(self):
		pass
#		This optimization should work, but the API is being flaky when
#		setting all these keys at once
#		self._fTxAnim.addKeys( self._times, self._txKeys )
#		self._fTyAnim.addKeys( self._times, self._tyKeys )
#		self._fTzAnim.addKeys( self._times, self._tzKeys )
#		
#		self._fRxAnim.addKeys( self._times, self._rxKeys )
#		self._fRyAnim.addKeys( self._times, self._ryKeys )
#		self._fRzAnim.addKeys( self._times, self._rzKeys )
#		
#		self._fSxAnim.addKeys( self._times, self._sxKeys )
#		self._fSyAnim.addKeys( self._times, self._syKeys )
#		self._fSzAnim.addKeys( self._times, self._szKeys )
		
	
		
		
	def _initialize(self, objectIndex):
		self._geometry = self._instancer.duplicateInstance( objectIndex )
		self._paths.append( self._geometry.root )
				
		fNode = MFnTransform( self._geometry.root.transform() )
		fGenerator = MFnAnimCurve()
		
		self._fTxAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "translateX", True ) ) )
		self._fTyAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "translateY", True ) ) )
		self._fTzAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "translateZ", True ) ) )
		
		self._fRxAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "rotateX", True ) ) )
		self._fRyAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "rotateY", True ) ) )
		self._fRzAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "rotateZ", True ) ) )

		self._fSxAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "scaleX", True ) ) )
		self._fSyAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "scaleY", True ) ) )
		self._fSzAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "scaleZ", True ) ) )
		
		self._fVAnim = MFnAnimCurve( fGenerator.create( fNode.findPlug( "visibility", True ) ) )
		self._fVAnim.addKeyframe( MTime( self._instancer.startFrame(), MTime.uiUnit() ), 0.0,
							 	  MFnAnimCurve.kTangentStep,
							 	  MFnAnimCurve.kTangentStep )
		self._fVAnim.addKeyframe( MAnimControl.currentTime(), 1.0,
							 	  MFnAnimCurve.kTangentStep,
							 	  MFnAnimCurve.kTangentStep )
		
		self._objectIndex = objectIndex
		self._initialized = True
		

