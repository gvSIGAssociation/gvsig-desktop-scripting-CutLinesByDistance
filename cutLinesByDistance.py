# encoding: utf-8

import gvsig
from gvsig.libs import gvpy
import os
from gvsig import geom
from org.gvsig.fmap.geom import Geometry
from org.gvsig.fmap.geom import GeometryLocator
from org.gvsig.fmap.geom.aggregate import MultiPrimitive
from org.gvsig.fmap.geom.primitive import Polygon, Point
# Con geometrias normales se quedaria con el getGeometryType()
from es.unex.sextante.dataObjects import IVectorLayer
from gvsig.libs.toolbox import ToolboxProcess
from es.unex.sextante.gui import core
from es.unex.sextante.gui.core import NameAndIcon
#from es.unex.sextante.parameters import ParameterDataObject
#from es.unex.sextante.exceptions import WrongParameterTypeException
from es.unex.sextante.additionalInfo import AdditionalInfoVectorLayer
#from gvsig import logger
#from gvsig import LOGGER_WARN
#from es.unex.sextante.additionalInfo import AdditionalInfo
from org.gvsig.geoprocess.lib.api import GeoProcessLocator
from org.gvsig.tools import ToolsLocator
from java.lang import Math
from org.gvsig.fmap.geom import Geometry
from org.gvsig.fmap.geom import GeometryLocator


class CutLinesByDistance(ToolboxProcess):
  def defineCharacteristics(self):
    i18nManager = ToolsLocator.getI18nManager()
    
    self.setName(i18nManager.getTranslation("_Cut_lines_by_distance"))
    self.setGroup(i18nManager.getTranslation("_Transform"))
    params = self.getParameters()
    self.setUserCanDefineAnalysisExtent(False)
    params.addInputVectorLayer("studyAreaNameVector",i18nManager.getTranslation("_Transform_Layer"), AdditionalInfoVectorLayer.SHAPE_TYPE_ANY,True)
    params.addNumericalValue("cutDistance", i18nManager.getTranslation("_Cut_distance"),100,1)
    params.addFilepath("outputFilePath",i18nManager.getTranslation("_Output_Layer"),False,False,True,[".shp"])

  def processAlgorithm(self):
    params = self.getParameters()
    studyAreaNameVector = params.getParameterValueAsVectorLayer("studyAreaNameVector").getFeatureStore()
    cutDistance = params.getParameterValueAsDouble("cutDistance")
    outputFilePath = params.getParameterValueAsString("outputFilePath")
    if outputFilePath == "":
        outputFilePath = gvsig.getTempFile("result_geometries",".shp")
    elif not outputFilePath.endswith('.shp'):
        outputFilePath = outputFilePath+".shp"
    process(self, studyAreaNameVector,cutDistance,outputFilePath)
    return True
    
    
def process(selfStatus,store,cutDistance,outputFilePath=None):
    geomManager = GeometryLocator.getGeometryManager()

    fset = store.getFeatureSet()
    nsch = gvsig.createFeatureType(store.getDefaultFeatureType())

    if outputFilePath is None:
        outputFilePath = gvsig.getTempFile("result_geometries",".shp")
    ns = gvsig.createShape(nsch,outputFilePath)
    ns.edit()
    store = ns.getFeatureStore()
    #selfStatus.setRangeOfValues(0,fset.getSize())
    for f in fset:
        #selfStatus.next()
        fg = f.getDefaultGeometry()
        if isinstance(fg,MultiPrimitive):
            linesToProcess = []
            for i in range(0,fg.getPrimitivesNumber()):
                iLine = fg.getPrimitiveAt(i)
                linesToProcess.append(iLine)
        else:
            linesToProcess = [fg]
            
        for iLine in linesToProcess:
            
            setLines = processLine3D(iLine,cutDistance)
            for singleLine in setLines:
                #if singleLine.getNumVertices()<=1:
                #    continue
                nf = store.createNewFeature(f)
                nf.set("GEOMETRY", singleLine)
                store.insert(nf)
        #if selfStatus.isCanceled() == True:
        #    ns.finishEditing()
        #    return True
    ns.finishEditing()
    gvsig.currentView().addLayer(ns)
    return ns
    

def processLine3D(fgeom, segment):
    lines = []
    #output =[]
    dRemainingDistFromLastSegment = 0

    geomManager = GeometryLocator.getGeometryManager()
    ncoords = fgeom.getNumVertices()
    if ncoords == 0:
       return
    dAddedPointX = fgeom.getVertex(0).getX()
    dX1 = fgeom.getVertex(0).getX()
    dAddedPointY = fgeom.getVertex(0).getY()
    dY1 = fgeom.getVertex(0).getY()
    #dZ1 = fgeom.getVertex(0).getZ()
    point = geomManager.create(fgeom.getVertex(0).getGeometryType()) #geom.createPoint(geom.D3, [dAddedPointX, dAddedPointY, dAddedPointZ]) ## add vertex
    point.setCoordinateAt(Geometry.DIMENSIONS.X,dX1)
    point.setCoordinateAt(Geometry.DIMENSIONS.Y,dY1)
    #point.setCoordinateAt(Geometry.DIMENSIONS.Z,dZ1) #point = geom.createPoint(geom.D3M, dX1, dY1, dZ1) #dAddedPointX, dAddedPointY, 0)
    #output.append(point)
    newline = geomManager.create(fgeom.getGeometryType()) #geom.LINE, geom.D3M)
    #newline.addVertex(point)

    for i in range(0, fgeom.getNumVertices()-1):#(i = 0; i < coords.length - 1; i++) {
       dX2 = fgeom.getVertex(i + 1).getX()
       dX1 = fgeom.getVertex(i).getX()
       dY2 = fgeom.getVertex(i + 1).getY()
       dY1 = fgeom.getVertex(i).getY()
       #dZ2 = fgeom.getVertex(i+1).getZ()
       #dZ1 = fgeom.getVertex(i).getZ()
       dDX = dX2 - dX1
       dDY = dY2 - dY1
       #dDZ = dZ2 - dZ1
       dDistToNextPoint = Math.sqrt(dDX * dDX + dDY * dDY)
       newline.addVertex(fgeom.getVertex(i))
       
       if dRemainingDistFromLastSegment + dDistToNextPoint > segment: ## si el segmento es mayor lo partimos
          
          iPoints = (dRemainingDistFromLastSegment + dDistToNextPoint) / segment
          dDist = segment - dRemainingDistFromLastSegment # distancia segmento inicial lo que falta para completar el anterior
          for j in range(0, int(iPoints)):
              dDist = segment - dRemainingDistFromLastSegment
              dDist += j*segment
              dAddedPointX = dX1 + dDist * dDX / dDistToNextPoint
              dAddedPointY = dY1 + dDist * dDY / dDistToNextPoint
              #dAddedPointZ = dZ1 + dDist *dDZ / dDistToNextPoint
              point = geomManager.create(fgeom.getVertex(i).getGeometryType())
              point.setCoordinateAt(Geometry.DIMENSIONS.X,dAddedPointX)
              point.setCoordinateAt(Geometry.DIMENSIONS.Y,dAddedPointY)
              #point.setCoordinateAt(Geometry.DIMENSIONS.Z,dAddedPointZ)
              #output.append(point)
              newline.addVertex(point)
              lines.append(newline)
              newline = geomManager.create(fgeom.getGeometryType())
              newline.addVertex(point)
          dDX = dX2 - dAddedPointX
          dDY = dY2 - dAddedPointY
          #newline = geomManager.create(fgeom.getGeometryType()) #newline = geom.createGeometry(geom.LINE, geom.D3)
          #newline.addVertex(point)
          dRemainingDistFromLastSegment = Math.sqrt(dDX * dDX + dDY * dDY)
       else: # si  es menor lo agregamos y pasamos al siguiente segmento
          dRemainingDistFromLastSegment += dDistToNextPoint
          #newline.addVertex(dX1, dY1, dZ1) 
       print "addvertex2"
       newline.addVertex(dX2, dY2) #, dZ2)
       print newline
    #newline.addVertex(dX2, dY2, dZ2)
    if not newline.getNumVertices() <=1:
        lines.append(newline)
    else:
        print "tak"
        print newline.getVertex(0)
        #print newline.getVertex(0)#.convertToWKT()
    return lines
    
def main(*args):
    #process = CutLinesByDistance()
    #process.selfregister("Scripting")
    #gm = GeoProcessLocator.getGeoProcessManager()
    # Actualizamos el interface de usuario de la Toolbox
    #process.updateToolbox()
    #store = gvsig.currentLayer().getFeatureStore()
    store = gvsig.currentView().getLayer("oneline").getFeatureStore()
    ns = process(None, store,30)
    n = gvpy.runalg("geometriestopoints", ns)
    