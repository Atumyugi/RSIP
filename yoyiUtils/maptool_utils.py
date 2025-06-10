import numpy as np
from math import acos, degrees
from PyQt5.QtGui import QIcon, QKeyEvent,QKeySequence,QCursor,QPixmap,QPen, QColor,QFont,QMouseEvent
from PyQt5.QtCore import Qt,QRectF, QPointF,QPoint,pyqtSignal
from PyQt5.QtWidgets import QMessageBox,QUndoStack,QComboBox,QMenu,QAction,QApplication, QWidget
from qgis._gui import QgsMapCanvas, QgsMapMouseEvent
from qgis.core import QgsVertexId,QgsRectangle,QgsPoint,QgsCircle,QgsPointXY, QgsWkbTypes,QgsVectorLayer,\
    QgsVectorDataProvider,QgsFeature,QgsGeometry,QgsLineString,QgsRasterLayer,QgsProject,QgsMapSettings, \
    QgsDistanceArea,QgsWkbTypes,QgsFeatureRequest,QgsMultiPolygon,QgsMapToPixel,QgsMultiLineString,QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform,Qgis,QgsJsonUtils,QgsFields,Qgis
from qgis.gui import QgsProjectionSelectionDialog,QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker,QgsMapToolIdentify,QgsMapTool,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapCanvasItem,QgsMapToolPan,QgsMapMouseEvent,QgsMapToolCapture
from qfluentwidgets import MessageBox,RoundMenu, setTheme, Theme, Action, MenuAnimationType, MenuItemDelegate, CheckableMenu, MenuIndicatorType
from qfluentwidgets import FluentIcon as FIF
from yoyiUtils.plot_rectangle import plot_rectangle,update_orth
from yoyiUtils.yoyiTranslate import yoyiTrans

from shapely import affinity,wkt
import appConfig
import yoyirs_rc

PROJECT = QgsProject.instance()

def makeValid_deleteAngle0_old(geometry:QgsGeometry):
    bedeleteIds = []
    index = 0
    for vertex in geometry.vertices():
        beforeId,afterId = geometry.adjacentVertices(index)
        prev_vertex = geometry.vertexAt(beforeId)
        next_vertex = geometry.vertexAt(afterId)
        v1 = ( round(prev_vertex.x() - vertex.x(),9) , round(prev_vertex.y() - vertex.y(),9))
        v2 = ( round(next_vertex.x() - vertex.x(),9) , round(next_vertex.y() - vertex.y(),9))

        # 计算两个向量之间的角度
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        magnitude_v1 = (v1[0]**2 + v1[1]**2) ** 0.5
        magnitude_v2 = (v2[0]**2 + v2[1]**2) ** 0.5
        magnitude = magnitude_v1 * magnitude_v2
        if magnitude == 0:
            bedeleteIds.append(index)
            continue
        print("point1",vertex.x(),vertex.y())
        print("point2",prev_vertex.x(),prev_vertex.y())
        print("point3",next_vertex.x(),next_vertex.y())
        print("(magnitude_v1 * magnitude_v2)",magnitude)
        print(" -- -- ")
        ddm = dot_product / magnitude
        if ddm < -1 or ddm > 1:
            ddm = 1
        angle = degrees(acos(ddm))
        print(angle)
        if angle < 0.1:
            bedeleteIds.append(index)
        index += 1
    
    for vid in bedeleteIds:
        geometry.deleteVertex(vid)
    
    return geometry

def makeValid_deleteAngle0(geometry:QgsGeometry):
    
    parts = geometry.parts()
    bedeleteParts = []
    for partIndex,part in enumerate(parts):
        bedeleteIds = []
        vertexCount = part.vertexCount()
        for vertexIndex in range(vertexCount):
            vertexId = QgsVertexId(partIndex,0,vertexIndex)
            beforeId,afterId = part.adjacentVertices(vertexId)
            vertex = part.vertexAt(vertexId)
            prev_vertex = part.vertexAt(beforeId)
            next_vertex = part.vertexAt(afterId)
            v1 = ( round(prev_vertex.x() - vertex.x(),9) , round(prev_vertex.y() - vertex.y(),9))
            v2 = ( round(next_vertex.x() - vertex.x(),9) , round(next_vertex.y() - vertex.y(),9))
            # 计算两个向量之间的角度
            dot_product = v1[0] * v2[0] + v1[1] * v2[1]
            magnitude_v1 = (v1[0]**2 + v1[1]**2) ** 0.5
            magnitude_v2 = (v2[0]**2 + v2[1]**2) ** 0.5
            magnitude = magnitude_v1 * magnitude_v2
            if magnitude == 0:
                angle = 0
            else:
                ddm = dot_product / magnitude
                if ddm < -1 or ddm > 1:
                    ddm = 1
                angle = degrees(acos(ddm))
            if vertexCount < 4 and angle < 0.1:
                bedeleteParts.append(partIndex)
                break
            print("point1",vertex.x(),vertex.y())
            print("point2",prev_vertex.x(),prev_vertex.y())
            print("point3",next_vertex.x(),next_vertex.y())
            print("(magnitude_v1 * magnitude_v2)",magnitude)
            print(angle)
            print(" -- -- ")
            if angle < 0.1:
                bedeleteIds.append(vertexId)
        for vid in bedeleteIds:
            part.deleteVertex(vid)
    
    for partIndex in bedeleteParts:
        geometry.deletePart(partIndex)
    return geometry

def autoCompletePolygon(beCompletedGeo:QgsGeometry,geoList):
    geom = None
    for tempGeo in geoList:
        tempGeo : QgsGeometry
        if geom == None:
            geom = tempGeo
        else:
            geom = geom.combine(tempGeo)
    
    if not geom:
        return beCompletedGeo
    
    geom = makeValid_deleteAngle0(geom)

    if geom.contains(beCompletedGeo):
        return None
    
    if geom.intersects(beCompletedGeo):
        tempResGeo = beCompletedGeo.difference(geom)
        if tempResGeo.isGeosValid():
            beCompletedGeo = tempResGeo
    resGeo = beCompletedGeo.makeValid()
    resGeo = makeValid_deleteAngle0(resGeo)
    return resGeo


