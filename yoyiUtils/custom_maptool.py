# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2022/6/7 15:30
import numpy as np
import math
import traceback
from PyQt5.QtGui import QIcon, QKeyEvent,QKeySequence,QCursor,QPixmap,QPen, QColor,QFont,QMouseEvent
from PyQt5.QtCore import Qt,QRectF, QPointF,QPoint,pyqtSignal
from PyQt5.QtWidgets import QMessageBox,QUndoStack,QComboBox,QMenu,QAction,QApplication, QWidget
from qgis.core import QgsMapLayer,QgsRectangle,QgsPoint,QgsCircle,QgsPointXY, QgsWkbTypes,QgsVectorLayer,\
    QgsVectorDataProvider,QgsFeature,QgsGeometry,QgsPolygon,QgsLineString,QgsRasterLayer,QgsProject,QgsMapSettings, \
    QgsDistanceArea,QgsWkbTypes,QgsFeatureRequest,QgsMultiPolygon,QgsMapToPixel,QgsMultiLineString,QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform,QgsSnappingConfig,Qgis,QgsTolerance
from qgis.gui import QgsMapCanvas, QgsMapMouseEvent,QgsProjectionSelectionDialog,QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker,QgsMapToolIdentify,QgsSnapIndicator,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapCanvasItem,QgsMapToolPan,QgsMapMouseEvent

from widgets.mapToolRectangleDialog import mapToolRectangleWindowClass
from widgets.mapToolInputAttrWindow import inputAttrWindowClass
from widgets.mapToolSingleAttrSelectWindow import selectSingleAttrWindowClass
from widgets.mapToolAttrSelectWindow import selectAttrWindowClass

from widgets.mapToolMeasureDistanceDialog import MeasureDistanceMapToolDialogClass
from widgets.mapToolMeasureAreaDialog import MeasureAreaMapToolDialogClass

from qfluentwidgets import MessageBox,RoundMenu, setTheme, Theme, Action, MenuAnimationType, CheckableMenu, MenuIndicatorType
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.maptool_utils import autoCompletePolygon
from yoyiUtils.plot_rectangle import plot_rectangle,update_orth
from yoyiUtils.yoyiTranslate import yoyiTrans

from shapely import affinity,wkt
from typing import Union
import appConfig

import yoyirs_rc

PROJECT = QgsProject.instance()

snapTypeDict = {
    0 : QgsSnappingConfig.SnappingType.Vertex,
    1 : QgsSnappingConfig.SnappingType.Segment,
    2 : QgsSnappingConfig.SnappingType.VertexAndSegment,
}

def makeGeoIsVectorCrs(geometry: Union[QgsGeometry,QgsLineString],mapCrs:QgsCoordinateReferenceSystem,vectorCrs:QgsCoordinateReferenceSystem,reverse=False):
    if mapCrs.authid() == vectorCrs.authid():
        return geometry
    else:
        if reverse:
            xform = QgsCoordinateTransform(vectorCrs,mapCrs,PROJECT.transformContext())
        else:
            xform = QgsCoordinateTransform(mapCrs,vectorCrs,PROJECT.transformContext())
        geometry.transform(xform)
        return geometry

class YoyiMapCanvas(QgsMapCanvas):
    def __init__(self, parent: QWidget,yoyiTrs:yoyiTrans) -> None:
        super().__init__(parent)
        self.ct: QgsMapToPixel = self.getCoordinateTransform()
        self.yoyiTrs = yoyiTrs
    
    def changeTrs(self,yoyiTrs):
        self.yoyiTrs = yoyiTrs

    def changeMapCanvasProjection(self):
        mapSetting : QgsMapSettings = self.mapSettings()
        dialog = QgsProjectionSelectionDialog()
        dialog.setWindowIcon(QIcon(":/img/resources/logo.png"))
        if mapSetting.destinationCrs().authid():
            dialog.setCrs(mapSetting.destinationCrs())
        dialog.exec()
        if dialog.crs():
            self.setDestinationCrs(dialog.crs())
            if self.mapTool() and type(self.mapTool()) == RecTangleSelectFeatureMapTool:
                self.mapTool().refreshForm()
        
        dialog.deleteLater()

    # 右键窗口触发事件
    def on_custom_menu_requested(self,point:QgsPointXY):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        copyXy = Action(FIF.COPY,self.yoyiTrs._translate('复制坐标'))
        copyXy.triggered.connect(lambda: QApplication.clipboard().setText(f"{point.x():.6f},{point.y():.6f}"))
        cusMenu.addAction(copyXy)
        changeCrs = Action(FIF.GLOBE,self.yoyiTrs._translate("切换地图坐标系"))
        changeCrs.triggered.connect(self.changeMapCanvasProjection)
        cusMenu.addAction(changeCrs)
        curPos : QPoint = QCursor.pos()

        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.RightButton:
            if self.mapTool() and type(self.mapTool()) != QgsMapToolPan:
                super().mousePressEvent(e)
                return
            else:
                point =  self.ct.toMapCoordinates(self.mouseLastXY())
                self.on_custom_menu_requested(point)
                return
        super().mousePressEvent(e)

class DoubleMapCanvas(QgsMapCanvas):
    def __init__(self,parent=None):
        super(DoubleMapCanvas, self).__init__(parent)

    def setDoubleCanvas(self,canvas):
        self.canvas2 : QgsMapCanvas = canvas
        self.vertex = QgsVertexMarker(self.canvas2)
        self.vertex.setIconType(QgsVertexMarker.ICON_X)
        self.vertex.setIconSize(18)
        self.ct: QgsMapToPixel = self.getCoordinateTransform()

    def mouseMoveEvent(self, e):
        super(DoubleMapCanvas, self).mouseMoveEvent(e)
        self.vertex.setCenter(self.ct.toMapCoordinates(self.mouseLastXY()))

    def mouseReleaseEvent(self, e):
        super(DoubleMapCanvas, self).mouseReleaseEvent(e)
        self.canvas2.setExtent(self.extent())
        self.canvas2.refresh()

    def keyReleaseEvent(self, e):
        super(DoubleMapCanvas,self).keyReleaseEvent(e)
        self.canvas2.setExtent(self.extent())
        self.canvas2.refresh()

    def wheelEvent(self, e):
        super(DoubleMapCanvas,self).wheelEvent(e)
        self.canvas2.setExtent(self.extent())
        self.canvas2.refresh()

class DoublePanTool(QgsMapToolPan):
    def __init__(self,canvas1,canvas2):
        super(DoublePanTool, self).__init__(canvas1)
        self.canvas1 : QgsMapCanvas = canvas1
        self.canvas2 : QgsMapCanvas = canvas2

    def canvasReleaseEvent(self, e):
        super(DoublePanTool, self).canvasReleaseEvent(e)
        #print(self.canvas1.extent(),self.canvas2.extent())
        self.canvas2.setExtent(self.canvas1.extent())
        self.canvas2.refresh()
    
class RectangleMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,layer,parentWindow,preField=None,preFieldValue=None,recExtent=None,otherCanvas=None,fieldValueDict=None,dialogMianFieldName=None,preDialog=None):
        """
        preFile - preFieldValue 直接不弹出选择框，直接赋予属性
        fieldValueDict 给一个属性选择框，下拉选择属性
        """
        super(RectangleMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(3)
        self.crossVertex = QgsVertexMarker(self.mapCanvas)
        self.crossVertex.setIconType(QgsVertexMarker.ICON_CROSS)
        self.crossVertex.setIconSize(2000)
        self.wkbType = "rectangle"
        self.editLayer : QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.mainWindow = parentWindow
        self.preField = preField
        self.preFieldValue = preFieldValue
        self.fieldValueDict = fieldValueDict
        self.dialogMianFieldName = dialogMianFieldName
        self.recExtent: QgsRectangle = recExtent
        self.otherCanvas = otherCanvas
        isHorizontal = appConfig.yoyiSetting().configSettingReader.value('horizontalRectangle',type=bool)
        self.drawType = 0 if isHorizontal else 1 # 0 水平矩形 1 旋转矩形
        self.reset()

    def reset(self):
        self.startPoint = self.startPointII = self.endPoint = None
        self.isEmittingPoint = False
        self.miniBoxGeo = None
        self.r : QgsGeometry = None
        self.rubberBand.reset()
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))

    def changeFieldValue(self,fieldValue):
        self.preFieldValue = fieldValue
    
    def changeDrawType(self,mode):
        self.drawType = mode
        if mode == 0:
            appConfig.yoyiSetting().changeSetting('horizontalRectangle', True)
        else:
            appConfig.yoyiSetting().changeSetting('horizontalRectangle', False)
        self.reset()

    # 右键窗口触发事件
    def on_custom_menu_requested(self):
        cusMenu = CheckableMenu(parent=self.mainWindow)
        cusMenu.setItemHeight(50)

        self.rectangeAction = Action('水平矩形模式')
        self.rectangeAction.setCheckable(True)
        self.rotateRectangeAction = Action('旋转矩形模式')
        self.rotateRectangeAction.setCheckable(True)
        
        if self.drawType == 0:
            self.rectangeAction.setChecked(True)
        else:
            self.rotateRectangeAction.setChecked(True)
        self.rectangeAction.triggered.connect(lambda: self.changeDrawType(0))
        self.rotateRectangeAction.triggered.connect(lambda: self.changeDrawType(1))

        cusMenu.addAction(self.rectangeAction)
        cusMenu.addAction(self.rotateRectangeAction)

        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()))

    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        snapMatch = self.snapper.snapToMap(e.pos())
        self.snapIndicator.setMatch(snapMatch)
        if snapMatch.isValid():
            tempPoint = snapMatch.point()
        if (not self.isEmittingPoint) and e.button() == Qt.MouseButton.RightButton:
            self.reset()
            self.on_custom_menu_requested()
        if self.drawType == 1:
            if e.button() == Qt.LeftButton:
                if not self.isEmittingPoint:
                    if self.startPoint == None:
                        self.startPoint = tempPoint
                    elif self.startPointII == None:
                        if tempPoint.x()!=self.startPoint.x() and tempPoint.y()!=self.startPoint.y():
                            self.startPointII = tempPoint
                    elif self.endPoint == None:
                        self.endPoint = tempPoint
                        self.isEmittingPoint = True
                elif self.isEmittingPoint and self.miniBoxGeo:
                    self.r = self.miniBoxGeo
                    self.isEmittingPoint = False
                    self.addFeature()
            elif e.button() == Qt.RightButton:
                self.reset()
        else:
            if e.button() == Qt.LeftButton:
                if not self.isEmittingPoint:
                    self.startPoint = tempPoint
                    self.endPoint = self.startPoint
                    self.isEmittingPoint = True
                    self.showRect(self.startPoint, self.endPoint)
                elif self.isEmittingPoint and self.rectangle():
                    self.r = self.rectangle()
                    self.isEmittingPoint = False
                    self.addFeature()
            elif e.button() == Qt.RightButton:
                self.reset()

    def canvasMoveEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        snapMatch = self.snapper.snapToMap(e.pos())
        self.snapIndicator.setMatch(snapMatch)
        if snapMatch.isValid():
            tempPoint = snapMatch.point()
        self.crossVertex.setCenter(tempPoint)
        if not self.isEmittingPoint:
            if self.r:
                pass
            elif self.startPoint and self.startPointII:
                self.showLine([self.startPoint,self.startPointII,tempPoint])
            elif self.startPoint:
                self.showLine([self.startPoint, tempPoint])
        else:
            if self.drawType == 1:
                self.showRotateRect(self.startPoint,self.startPointII,self.endPoint,tempPoint)
            else:
                self.endPoint = tempPoint
                self.showRect(self.startPoint, self.endPoint)

    def showLine(self,points):
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        for point in points:
            self.rubberBand.addPoint(point, False)
        self.rubberBand.show()

    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())
        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)  # true to update canvas
        self.rubberBand.show()

    def showRotateRect(self,startPoint,startPointII,endPoint,tempPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPointII.x(), startPointII.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(tempPoint.x(), tempPoint.y())
        tempGeo = QgsGeometry.fromMultiPolygonXY([[[point1,point2,point3,point4]]])
        self.miniBoxGeo,a,b,c,d = tempGeo.orientedMinimumBoundingBox()
        if self.miniBoxGeo.isGeosValid():
            self.rubberBand.addGeometry(self.miniBoxGeo)
            self.rubberBand.show()
        else:
            self.reset()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            #print("可编辑？",self.editLayer.isEditable())
            feat = QgsFeature(self.editLayer.fields())
            if self.fieldValueDict is not None:
                if type(self.fieldValueDict) is dict:
                    selectAttrWindows = selectAttrWindowClass(self.fieldValueDict, self.mainWindow)
                    selectAttrWindows.exec()
                    resDict = selectAttrWindows.resDict
                    selectAttrWindows.destroy()
                else:
                    resDict = self.fieldValueDict
                
                print("resDict",resDict)

                if resDict:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setGeometry(self.r)
                    print(self.r)
                    feat.setAttributes(resDict)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
                else:
                    self.reset()
            elif self.preField is not None and type(self.preFieldValue) == list:
                if len(self.preFieldValue) > 1:
                    selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self.mainWindow)
                    selectAttrWindows.exec()
                    resIndex = selectAttrWindows.resIndex
                    selectAttrWindows.destroy()
                else:
                    resIndex = 0
                if resIndex >= 0:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setAttribute(self.preField, self.preFieldValue[resIndex])
                    feat.setGeometry(self.r)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            elif self.preField is not None and self.preFieldValue is not None:
                feat.setAttribute(self.preField, self.preFieldValue)
                tempGeo = self.r
                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(tempGeo):
                    MessageBox('提示', "面矢量与图层范围不相交", self.mainWindow).exec_()
                    self.reset()
                else:
                    feat.setGeometry(tempGeo)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            else:
                inputAttrWindows = inputAttrWindowClass(self,feat,self.mainWindow)
                inputAttrWindows.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return None
        return QgsGeometry.fromRect(QgsRectangle(self.startPoint, self.endPoint))


    def deactivate(self):
        try:
            self.mapCanvas.scene().removeItem(self.crossVertex)
        except:
            pass
        self.reset()
        self.snapIndicator.setVisible(False)
        super(RectangleMapTool, self).deactivate()

class PolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,layer,parentWindow,preField=None,preFieldValue=None,recExtent=None,otherCanvas=None,fieldValueDict=None,dialogMianFieldName=None):
        super(PolygonMapTool, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()

        self.mainWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(3)

        self.wkbType = "polygon"
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.preField = preField
        self.preFieldValue = preFieldValue
        self.fieldValueDict = fieldValueDict
        self.dialogMianFieldName= dialogMianFieldName
        self.recExtent: QgsRectangle = recExtent
        self.otherCanvas = otherCanvas

        self.reset()

    def reset(self):
        self.is_start = False  # 开始绘图
        self.cursor_point = None
        self.cursor_pos = None

        self.autoLong = -1 # 1 0 是缓冲区  -1 是真死了
        self.autoLongLastIndex = -1

        self.points = []
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)
        #stream tolerance
        self.lastPixelPos = None
        self.streamTolerance = appConfig.yoyiSetting().configSettingReader.value('streamTolerance',type=int)

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))

    def changeFieldValue(self,fieldValue):
        self.preFieldValue = fieldValue

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Backspace:
            if self.autoLong >= 0 and self.autoLongLastIndex >= 0 and len(self.points)>=1:
                self.points = self.points[:self.autoLongLastIndex]
                self.showPolygon()
                self.autoLong = -1
            elif self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                self.showPolygon()
            else:
                self.reset()

    def canvasDoubleClickEvent(self, e: QgsMapMouseEvent) -> None:
        #print(e.button())
        if e.button() == Qt.LeftButton:
            self.autoLong = 1
            if self.points and len(self.points) >=1:
                self.autoLongLastIndex = len(self.points)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.cursor_pos:
                self.cursor_pos = event.pos()
                self.cursor_point = event.mapPoint()
                snapMatch = self.snapper.snapToMap(event.pos())
                self.snapIndicator.setMatch(snapMatch)
                if snapMatch.isValid():
                    self.cursor_point = snapMatch.point()
                    self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
            self.addPoint(self.cursor_point)
            if self.autoLong >= 0:
                self.autoLong -= 1
        elif event.button() == Qt.RightButton:
            # 右键结束绘制
            if self.is_start:
                self.is_start = False
                self.cursor_point = None
                self.p = self.polygon()

                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(self.p):
                    MessageBox('提示', "面矢量与图层范围不相交", self.mainWindow).exec_()
                    self.reset()
                else:
                    if self.p is not None:
                        self.addFeature()
                    else:
                        self.reset()
                self.points = []
            else:
                pass

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            
            drawGeometry = makeGeoIsVectorCrs(self.p,self.mapCanvas.mapSettings().destinationCrs(),self.editLayer.crs())

            # if self.fieldValueDict == "WEB":
            #     if not self.parentWindow.isOpenAttrWindowSB.isChecked():
            #          remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
            #                             self.parentWindow.remark1Type,
            #                             self.parentWindow.remark2Type,
            #                             self.parentWindow.remark3Type,
            #                             self.parentWindow.remark1List,
            #                             self.parentWindow.remark2List,
            #                             self.parentWindow.remark3List,
            #                             self.parentWindow.remark2String,
            #                             self.parentWindow.remark3String
            #                            )
            if self.fieldValueDict is not None:
                if type(self.fieldValueDict) is dict:
                    selectAttrWindows = selectAttrWindowClass(self.fieldValueDict, self.mainWindow)
                    selectAttrWindows.exec()
                    resDict = selectAttrWindows.resDict
                    selectAttrWindows.destroy()
                else:
                    resDict = self.fieldValueDict

                if resDict:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setGeometry(drawGeometry)
                    feat.setAttributes(resDict)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
                else:
                    self.reset()
            elif self.preField is not None and type(self.preFieldValue) == list:
                if len(self.preFieldValue) > 1:
                    selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self.mainWindow)
                    selectAttrWindows.exec()
                    resIndex = selectAttrWindows.resIndex
                    selectAttrWindows.destroy()
                else:
                    resIndex = 0
                if resIndex >= 0:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setAttribute(self.preField, self.preFieldValue[resIndex])
                    feat.setGeometry(drawGeometry)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            elif self.preField is not None and self.preFieldValue is not None:
                feat = QgsFeature(self.editLayer.fields())
                feat.setAttribute(self.preField,self.preFieldValue)
                feat.setGeometry(drawGeometry)
                self.editLayer.addFeature(feat)
                self.mapCanvas.refresh()
                if self.otherCanvas:
                    self.otherCanvas.refresh()
                self.reset()
                self.mainWindow.updateShpUndoRedoButton()
            else:
                feat = QgsFeature(self.editLayer.fields())
                feat.setGeometry(drawGeometry)
                self.editLayer.addFeature(feat)
                self.reset()
                self.mainWindow.updateShpUndoRedoButton()

    def addFeatureByDict(self,resDict:dict):
        if resDict:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            feat.setAttributes(resDict)
            self.editLayer.addFeature(feat)
            self.mapCanvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()
            self.mainWindow.updateShpUndoRedoButton()
        else:
            self.reset()

    def addPoint(self,point,streamCheck=False):
        if self.lastPixelPos:
            tempPosDis = math.sqrt((self.cursor_pos.x()-self.lastPixelPos.x())**2 + (self.cursor_pos.y()-self.lastPixelPos.y())**2)
            # 距离过近 小于根号2 删除
            if tempPosDis<1.415:
                return
            # 小于 流的容差 删除
            if streamCheck and self.lastPixelPos and tempPosDis<self.streamTolerance:
                return
        self.lastPixelPos : QPoint = self.cursor_pos
        self.points.append(point)
        self.is_start = True 

    def canvasMoveEvent(self, event):
        try:
            self.cursor_pos = event.pos()
            self.cursor_point = event.mapPoint()
            snapMatch = self.snapper.snapToMap(event.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                self.cursor_point = snapMatch.point()
                self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
                
            if self.autoLong == 1:
                self.addPoint(self.cursor_point,streamCheck=True)

            if not self.is_start:
                return
            self.showPolygon()
        except Exception as e:
            MessageBox('提示', "缓存过多，已自动清除", self.mainWindow).exec_()
            self.reset()

    def showPolygon(self):
        if self.points and len(self.points)>=1:
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)  # 防止拖影
            first_point = self.points[0]
            last_point = self.points[-1]
            if first_point and last_point:
                self.rubberBand.addPoint(first_point, False)
                for point in self.points[1:-1]:
                    self.rubberBand.addPoint(point, False)
                if self.cursor_point:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), False)
                else:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), True)
                    self.rubberBand.show()
                    return
                self.rubberBand.addPoint(self.cursor_point, True)
                self.rubberBand.show()
        else:
            self.reset()
            
    def polygon(self):
        if self.points and len(self.points) <= 2:
            return None
        pointList = []
        for point in self.points:
            pointList.append(QgsPointXY(point[0],point[1]))
        tempPolygon : QgsGeometry = QgsGeometry.fromMultiPolygonXY([[pointList]])
        resPolygon = tempPolygon.makeValid()

        isAutoComplete = appConfig.yoyiSetting().configSettingReader.value('autoComplete',type=bool)
        if resPolygon.type() == 2:
            if isAutoComplete:
                featureRequest = QgsFeatureRequest().setFilterRect(resPolygon.boundingBox())
                filterFeatures = self.editLayer.getFeatures(featureRequest)
                geoList = []
                for feature in filterFeatures:
                    geoList.append(feature.geometry())
                
                resPolygon = autoCompletePolygon(resPolygon,geoList)

                if resPolygon and resPolygon.type() == 2 and resPolygon.area() >0:
                    return resPolygon
                else:
                    MessageBox('提示', "面要素非法", self.mainWindow).exec_()
                    return None
            else:
                return resPolygon
        else:
            MessageBox('提示', "面矢量几何逻辑错误", self.mainWindow).exec_()
            return None

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super(PolygonMapTool, self).deactivate()

class PolygonOrthMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,layer,mainWindow,preField=None,preFieldValue=None,recExtent=None,otherCanvas=None,fieldValueDict=None,dialogMianFieldName=None):
        super(PolygonOrthMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(1)
        self.wkbType = "polygon"
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()
        self.mainWindow = mainWindow
        self.preField = preField
        self.preFieldValue = preFieldValue
        self.fieldValueDict = fieldValueDict
        self.dialogMianFieldName= dialogMianFieldName
        self.recExtent: QgsRectangle = recExtent
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.is_start = False  # 开始绘图
        self.is_vertical = False  # 垂直画线
        self.cursor_point = None
        self.points = []
        self.rubberBand.reset()

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))

    def changeFieldValue(self,fieldValue):
        self.preFieldValue = fieldValue

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Backspace:
            if self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                print(self.points)
                self.showPolygon()
            else:
                self.reset()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(self.cursor_point)
            self.is_start = True
        elif event.button() == Qt.RightButton:
            # 右键结束绘制
            if self.is_start:
                self.is_start = False

                #point0 = np.array([self.points[0].x(), self.points[0].y()])
                #point1 = np.array([self.points[-1].x(), self.points[-1].y()])
                #point2 = np.array([self.cursor_point.x(), self.cursor_point.y()])
                #newx, newy = update_orth(point0, point1, point2)
                #self.points.append(QgsPointXY(newx, newy))

                self.p = self.polygon()

                #self.cursor_point = None
                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(self.p):
                    MessageBox('提示', "面矢量与图层范围不相交", self.mainWindow).exec_()
                    self.reset()
                else:
                    if self.p is not None:
                        if self.p.isGeosValid():
                            self.addFeature()
                        else:
                            MessageBox('错误', "面矢量拓扑逻辑错误", self.mainWindow).exec_()
                            self.reset()
                    else:
                        self.reset()
                #self.showPolygon()
                self.points = []
            else:
                pass

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            if self.fieldValueDict is not None:
                if type(self.fieldValueDict) is dict:
                    selectAttrWindows = selectAttrWindowClass(self.fieldValueDict, self.mainWindow)
                    selectAttrWindows.exec()
                    resDict = selectAttrWindows.resDict
                    selectAttrWindows.destroy()
                else:
                    resDict = self.fieldValueDict
                if resDict:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setGeometry(self.p)
                    feat.setAttributes(resDict)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
                else:
                    self.reset()
            elif self.preField is not None and type(self.preFieldValue) == list:
                if len(self.preFieldValue) > 1:
                    selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self.mainWindow)
                    selectAttrWindows.exec()
                    resIndex = selectAttrWindows.resIndex
                    selectAttrWindows.destroy()
                else:
                    resIndex = 0
                if resIndex >= 0:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setAttribute(self.preField, self.preFieldValue[resIndex])
                    feat.setGeometry(self.p)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            elif self.preField is not None and self.preFieldValue is not None:
                feat = QgsFeature(self.editLayer.fields())
                feat.setAttribute(self.preField,self.preFieldValue)
                feat.setGeometry(self.p)
                self.editLayer.addFeature(feat)
                self.mapCanvas.refresh()
                if self.otherCanvas:
                    self.otherCanvas.refresh()
                self.reset()
                self.mainWindow.updateShpUndoRedoButton()
            else:
                feat = QgsFeature(self.editLayer.fields())
                #print("可编辑？",self.editLayer.isEditable())
                inputAttrWindows = inputAttrWindowClass(self,feat,self.mainWindow)
                inputAttrWindows.show()

    def addFeatureByDict(self,resDict:dict):
        if resDict:
            feat = QgsFeature(self.editLayer.fields())
            feat.setGeometry(self.p)
            feat.setAttributes(resDict)
            self.editLayer.addFeature(feat)
            self.mapCanvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()
            self.mainWindow.updateShpUndoRedoButton()
        else:
            self.reset()

    def canvasMoveEvent(self, event):
        self.cursor_point = event.mapPoint()
        if not self.is_start:
            return
        self.showPolygon()

    def showPolygon(self):
        if self.points and len(self.points)>=1:
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)  # 防止拖影
            first_point = self.points[0]
            last_point = self.points[-1]
            if first_point and last_point:
                self.rubberBand.addPoint(first_point, False)
                for point in self.points[1:-1]:
                    self.rubberBand.addPoint(point, False)
                if self.cursor_point:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), False)
                    if len(self.points) >=2:
                        point1 = np.array([self.points[-2].x(),self.points[-2].y()])
                        point2 = np.array([last_point.x(),last_point.y()])
                        point3 = np.array([self.cursor_point.x(),self.cursor_point.y()])
                        newx,newy = plot_rectangle(point1,point2,point3)
                        self.cursor_point = QgsPointXY(newx,newy)
                else:
                    self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), True)
                    self.rubberBand.show()
                    return
                self.rubberBand.addPoint(self.cursor_point, True)
                self.rubberBand.show()
        else:
            self.reset()

    def polygon(self):
        if self.points and len(self.points) <= 2:
            return None
        pointList = []
        for point in self.points:
            pointList.append(QgsPointXY(point[0],point[1]))
        return QgsGeometry.fromMultiPolygonXY([[pointList]])

    def deactivate(self):
        self.reset()
        super(PolygonOrthMapTool, self).deactivate()

class CircleMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,layer,mainWindow,preField=None,preFieldValue=None,recExtent=None,otherCanvas=None,fieldValueDict=None,dialogMianFieldName=None):
        super(CircleMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(1)
        self.wkbType = "circle"
        self.editLayer : QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.mainWindow = mainWindow
        self.preField = preField
        self.preFieldValue = preFieldValue
        self.fieldValueDict = fieldValueDict
        self.dialogMianFieldName = dialogMianFieldName
        self.recExtent : QgsRectangle = recExtent
        self.distance = QgsDistanceArea()
        self.distance.setSourceCrs(self.editLayer.crs(),self.editLayer.transformContext())
        self.points = None
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset()
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))

    def changeFieldValue(self,fieldValue):
        self.preFieldValue = fieldValue

    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        snapMatch = self.snapper.snapToMap(e.pos())
        self.snapIndicator.setMatch(snapMatch)
        if snapMatch.isValid():
            tempPoint = snapMatch.point()
        if e.button() == Qt.LeftButton:
            if not self.isEmittingPoint:
                self.startPoint = tempPoint
                self.endPoint = self.startPoint
                self.isEmittingPoint = True
                self.showCircle(self.startPoint, self.endPoint)
        elif e.button() == Qt.RightButton:
            if self.isEmittingPoint:
                #self.r = self.rectangle()
                if self.points is not None:
                    self.addFeature()
                    self.isEmittingPoint = False


    def canvasMoveEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        snapMatch = self.snapper.snapToMap(e.pos())
        self.snapIndicator.setMatch(snapMatch)
        if snapMatch.isValid():
            tempPoint = snapMatch.point()
        if not self.isEmittingPoint:
            return
        self.endPoint = tempPoint
        self.showCircle(self.startPoint, self.endPoint)


    def showCircle(self, startPoint, endPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() and startPoint.y() == endPoint.y():
            return
        A = QgsPointXY(startPoint.x(), startPoint.y())
        B = QgsPointXY(endPoint.x(), endPoint.y())
        distanceAB = self.distance.measureLine(A,B)

        circle = QgsCircle(QgsPoint(startPoint.x(), startPoint.y()),distanceAB)
        #a : QgsPolygon  = self.circle.toPolygon()
        #QgsGeometry.fromPolygonXY(self.circle.toPolygon())
        self.points = circle.points()

        for point in self.points[0:-1]:
            self.rubberBand.addPoint(QgsPointXY(point), False)
        self.rubberBand.addPoint(QgsPointXY(self.points[-1]), True)
        self.rubberBand.show()

    def addFeature(self):
        if self.caps & QgsVectorDataProvider.AddFeatures:
            #print("可编辑？",self.editLayer.isEditable())
            if self.fieldValueDict is not None:
                if type(self.fieldValueDict) is dict:
                    selectAttrWindows = selectAttrWindowClass(self.fieldValueDict, self.mainWindow)
                    selectAttrWindows.exec()
                    resDict = selectAttrWindows.resDict
                    selectAttrWindows.destroy()
                else:
                    resDict = self.fieldValueDict
                if resDict:
                    feat = QgsFeature(self.editLayer.fields())
                    pointsXY = [[]]
                    for point in self.points[0:-1]:
                        pointsXY[0].append(QgsPointXY(point))
                    tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
                    feat.setGeometry(tempGeo)
                    feat.setAttributes(resDict)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
                else:
                    self.reset()
            elif self.preField is not None and type(self.preFieldValue) == list:
                if len(self.preFieldValue) > 1:
                    selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self.mainWindow)
                    selectAttrWindows.exec()
                    resIndex = selectAttrWindows.resIndex
                    selectAttrWindows.destroy()
                else:
                    resIndex = 0
                if resIndex >= 0:
                    feat = QgsFeature(self.editLayer.fields())
                    feat.setAttribute(self.preField, self.preFieldValue[resIndex])
                    pointsXY = [[]]
                    for point in self.points[0:-1]:
                        pointsXY[0].append(QgsPointXY(point))
                    tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
                    feat.setGeometry(tempGeo)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            elif self.preField is not None and self.preFieldValue is not None:
                feat = QgsFeature(self.editLayer.fields())
                feat.setAttribute(self.preField,self.preFieldValue)
                pointsXY = [[]]
                for point in self.points[0:-1]:
                    pointsXY[0].append(QgsPointXY(point))
                tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(tempGeo):
                    MessageBox('提示', "面矢量与图层范围不相交", self.mainWindow).exec_()
                    self.reset()
                else:
                    feat.setGeometry(tempGeo)
                    self.editLayer.addFeature(feat)
                    self.mapCanvas.refresh()
                    if self.otherCanvas:
                        self.otherCanvas.refresh()
                    self.reset()
                    self.mainWindow.updateShpUndoRedoButton()
            else:
                feat = QgsFeature(self.editLayer.fields())
                inputAttrWindows = inputAttrWindowClass(self,feat,self.mainWindow)
                inputAttrWindows.show()

    def addFeatureByDict(self,resDict:dict):
        if resDict:
            feat = QgsFeature(self.editLayer.fields())
            feat.setAttribute(self.preField, self.preFieldValue)
            pointsXY = [[]]
            for point in self.points[0:-1]:
                pointsXY[0].append(QgsPointXY(point))
            tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
            feat.setGeometry(tempGeo)
            feat.setAttributes(list(resDict.values()))
            self.editLayer.addFeature(feat)
            self.mapCanvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()
            self.reset()
            self.mainWindow.updateShpUndoRedoButton()
        else:
            self.reset()

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super(CircleMapTool, self).deactivate()

# 编辑顶点 mapTool
class EditVertexMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,otherCanvas=None,useBbox=False):
        super(EditVertexMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.editLayer:QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setLineStyle(2) # Qt::PenStyle 1实线 2虚线 3点线
        self.rubberBand.setColor(QColor(255, 0, 0, 100))
        self.rubberBand.setWidth(3)
        self.pointVertex = QgsVertexMarker(self.mapCanvas)
        self.pointVertex.setIconType(QgsVertexMarker.ICON_CIRCLE)
        self.pointVertex.setIconSize(30)
        self.lineVertex = QgsVertexMarker(self.mapCanvas)
        self.lineVertex.setIconType(QgsVertexMarker.ICON_CROSS)
        self.lineVertex.setIconSize(30)
        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.editLayer.removeSelection()
        self.otherCanvas = otherCanvas
        self.useBbox = useBbox

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.isEmittingPoint = False #是不是已经开始编辑顶点
        self.changeId = None
        self.isInsert = False
        self.farthestPoint: QgsPointXY = None
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)

    # 重新渲染Rubber Band
    def reshapeRubberBand(self,points):
        self.rubberBand.reset()
        for point in points:
            self.rubberBand.addPoint(point)
    
    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key_Backspace:
            # 如果还没开始编辑顶点状态 
            if not self.isEmittingPoint:
                pass
            # 搜寻到最近的顶点进行删除
            else:
                if self.isInsert:
                    self.rubberBand.reset()
                    self.mapCanvas.refresh()
                    self.isInsert = False
                    self.isEmittingPoint = False
                else:
                    featureGeometry : QgsGeometry = self.editLayer.getFeature(self.featureId).geometry()
                    res = featureGeometry.deleteVertex(self.changeId)
                    if res:
                        self.editLayer.changeGeometry(self.featureId, featureGeometry)
                        self.parentWindow.updateShpUndoRedoButton()
                        self.rubberBand.reset()
                        self.mapCanvas.refresh()
                        self.isInsert = False
                        self.isEmittingPoint = False

    def canvasDoubleClickEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if self.featureId:
            if not self.editLayer.getFeature(self.featureId).geometry().contains(tempPoint):
                self.reset()
                self.pointVertex.hide()
                self.lineVertex.hide()
                #self.parentWindow.actionSelectSinglePolygon.trigger()

    def canvasPressEvent(self, e):
        if self.featureId is not None:
            tempPoint = self.toMapCoordinates(e.pos())
            snapMatch = self.snapper.snapToMap(e.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                tempPoint = snapMatch.point()
            featureGeometry : QgsGeometry = self.editLayer.getFeature(self.featureId).geometry()
            #featureGeometry.orthogonalize()
            # 如果还没开始
            if not self.isEmittingPoint:
                if e.button() == Qt.LeftButton:
                    nearestPoint,self.changeId,self.beforeVertexId,self.afterVertexId,_ = featureGeometry.closestVertex(tempPoint)
                    self.isEmittingPoint = True
                    if self.useBbox:
                        maxDis = 0
                        for pointS in featureGeometry.vertices():
                            pointSXY = QgsPointXY(pointS.x(), pointS.y())
                            tempDistance = nearestPoint.distance(pointSXY)
                            if tempDistance > maxDis:
                                maxDis = tempDistance
                                self.farthestPoint = pointSXY
                elif e.button() == Qt.RightButton:
                    squaredCartesian,minDistPoint,self.afterVertexId,leftOf = featureGeometry.closestSegmentWithContext(tempPoint,0.000000000001)
                    self.beforeVertexId = self.afterVertexId -1
                    self.isEmittingPoint = True
                    self.isInsert = True
            else:
                if self.isInsert:
                    featureGeometry.insertVertex(tempPoint.x(),tempPoint.y(),self.afterVertexId)
                    if self.useBbox:
                        tempGeo = QgsGeometry.fromRect(featureGeometry.boundingBox())
                        self.editLayer.changeGeometry(self.featureId, tempGeo)
                    else:
                        self.editLayer.changeGeometry(self.featureId, featureGeometry)
                else:
                    featureGeometry.moveVertex(tempPoint.x(),tempPoint.y(),self.changeId)
                    if self.useBbox:
                        resGeo = QgsGeometry.fromRect(QgsRectangle(self.farthestPoint,tempPoint))
                        self.editLayer.changeGeometry(self.featureId, resGeo)
                    else:
                        self.editLayer.changeGeometry(self.featureId, featureGeometry)
                self.parentWindow.updateShpUndoRedoButton()
                self.rubberBand.reset()
                self.mapCanvas.refresh()
                if self.otherCanvas:
                    self.otherCanvas.refresh()
                self.isInsert = False
                self.isEmittingPoint = False
        else:
            resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
            if resList:
                print(resList," -- ",resList[0].mFeature.id())
                self.featureId = resList[0].mFeature.id()
                self.editLayer.selectByIds([self.featureId])
                self.pointVertex.show()
                self.lineVertex.show()

    def canvasMoveEvent(self, e):
        if self.featureId is not None:
            tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
            snapMatch = self.snapper.snapToMap(e.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                tempPoint = snapMatch.point()
            featureGeometry : QgsGeometry = self.editLayer.getFeature(self.featureId).geometry()
            #featureGeometry.makeValid()
            if self.isEmittingPoint:
                if self.isInsert:
                    pointBefore = featureGeometry.vertexAt(self.beforeVertexId)
                    pointAfter = featureGeometry.vertexAt(self.afterVertexId)
                    self.reshapeRubberBand([QgsPointXY(pointBefore.x(),pointBefore.y()),tempPoint,QgsPointXY(pointAfter.x(),pointAfter.y())])
                else:
                    #nearestPoint = self._tempLayer.getFeature(self.changeId)
                    #self.featureGeometry.moveVertex(tempPoint.x(),tempPoint.y(),self.changeId)
                    pointBefore = featureGeometry.vertexAt(self.beforeVertexId)
                    pointAfter = featureGeometry.vertexAt(self.afterVertexId)
                    self.reshapeRubberBand([QgsPointXY(pointBefore.x(),pointBefore.y()),tempPoint,QgsPointXY(pointAfter.x(),pointAfter.y())])
            else:
                nearestPoint,vertexId,beforeVertexId,afterVertexId,_ = featureGeometry.closestVertex(tempPoint)
                squaredCartesian,minDistPoint,lineVertexId1,leftOf = featureGeometry.closestSegmentWithContext(tempPoint,0.000000000001)
                #print(self.featureGeometry.vertexAt(lineVertexId1),self.featureGeometry.vertexAt(lineVertexId1-1))
                x = (featureGeometry.vertexAt(lineVertexId1).x() + featureGeometry.vertexAt(lineVertexId1-1).x()) / 2
                y = (featureGeometry.vertexAt(lineVertexId1).y() + featureGeometry.vertexAt(lineVertexId1-1).y()) / 2
                #centerPointForLine : QgsGeometry = self.featureGeometry.shortestLine( QgsGeometry.fromPointXY(tempPoint) )
                self.pointVertex.setCenter(nearestPoint)
                self.lineVertex.setCenter(QgsPointXY(x,y))

    def deactivate(self):
        self.reset()
        try:
            self.mapCanvas.scene().removeItem(self.pointVertex)
            self.mapCanvas.scene().removeItem(self.lineVertex)
        except:
            pass
        self.snapIndicator.setVisible(False)
        super().deactivate()

# 旋转要素 mapTool
class RotatePolygonMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,otherCanvas=None):
        super(RotatePolygonMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.editLayer:QgsVectorLayer = editLayer
        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setLineStyle(2) # Qt::PenStyle 1实线 2虚线 3点线
        self.rubberBand.setColor(QColor(255, 0, 0, 100))

        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.editLayer.removeSelection()
        self.otherCanvas = otherCanvas
        self.reset()
    
    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.featureTempCentroid = None #当前选中要素的质心
        self.featureTempGeo = None #当前选中要素的Geometry
        self.tempDegree = 0.0
    
    # 重新渲染Rubber Band
    def reshapeRubberBand(self,tempGeo:QgsGeometry):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.addGeometry(tempGeo)
    
    def canvasPressEvent(self, e: QgsMapMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
                if resList:
                    self.featureId = resList[0].mFeature.id()
                    self.editLayer.selectByIds([self.featureId])
                    self.featureTempGeo = self.editLayer.getFeature(self.featureId).geometry()
                    self.featureTempCentroid = self.featureTempGeo.centroid().asPoint()
            # 如果选中了要素, 那确定旋转
            else:
                tempGeo = QgsGeometry(self.featureTempGeo)
                tempGeo.rotate(self.tempDegree,self.featureTempCentroid)
                self.editLayer.changeGeometry(self.featureId,tempGeo)
                self.parentWindow.updateShpUndoRedoButton()
                self.editLayer.removeSelection()
                self.reset()
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.removeSelection()
            self.reset()
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        if self.featureId is not None:
            tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
            self.tempDegree = self.featureTempCentroid.azimuth(tempPoint)
            tempGeo = QgsGeometry(self.featureTempGeo)
            tempGeo.rotate(self.tempDegree,self.featureTempCentroid)
            self.reshapeRubberBand(tempGeo)
    
    def deactivate(self):
        self.reset()
        super().deactivate()
        
# 缩放要素 mapTool
class RescalePolygonMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,otherCanvas=None):
        super(RescalePolygonMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.editLayer:QgsVectorLayer = editLayer
        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setLineStyle(2) # Qt::PenStyle 1实线 2虚线 3点线
        self.rubberBand.setColor(QColor(255, 0, 0, 100))

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.editLayer.removeSelection()
        self.otherCanvas = otherCanvas
        self.reset()
    
    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.featureTempCentroid = None #质心
        self.featureTempGeo = None #当前选中要素的Geometry
        self.factorDistance = None #选中点和质心的距离
        self.tempFactorScale = 1.0 
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)
    
    # 重新渲染Rubber Band
    def reshapeRubberBand(self,tempGeo:QgsGeometry):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.addGeometry(tempGeo)
    
    def canvasPressEvent(self, e: QgsMapMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
                if resList:
                    self.featureId = resList[0].mFeature.id()
                    self.editLayer.selectByIds([self.featureId])
                    self.featureTempGeo = self.editLayer.getFeature(self.featureId).geometry()
                    self.featureTempCentroid = self.featureTempGeo.centroid().asPoint()
                    tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
                    self.factorDistance = tempPoint.distance(self.featureTempCentroid)
                    if self.factorDistance < 0.00001:
                        self.factorDistance = 0.00001
            # 如果选中了要素, 那确定缩放
            else:
                shapelyPolygon = wkt.loads(self.featureTempGeo.asWkt())
                newPolygon = affinity.scale(shapelyPolygon,self.tempFactorScale,self.tempFactorScale)
                tempGeo = QgsGeometry().fromWkt(newPolygon.wkt)
                self.editLayer.changeGeometry(self.featureId,tempGeo)
                self.parentWindow.updateShpUndoRedoButton()
                self.editLayer.removeSelection()
                self.reset()
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.removeSelection()
            self.reset()
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        if self.featureId is not None:
            tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
            snapMatch = self.snapper.snapToMap(e.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                tempPoint = snapMatch.point()
            tempDistance = tempPoint.distance(self.featureTempCentroid)
            self.tempFactorScale = tempDistance / self.factorDistance
            
            shapelyPolygon = wkt.loads(self.featureTempGeo.asWkt())
            newPolygon = affinity.scale(shapelyPolygon,self.tempFactorScale,self.tempFactorScale)
            tempGeo = QgsGeometry().fromWkt(newPolygon.wkt)
            self.reshapeRubberBand(tempGeo)
    
    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()
    

# 裁剪要素 mapTool
class SplitPolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,editLayer,parentWindow,otherCanvas=None):
        super(SplitPolygonMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        # qgisFeature 待裁剪的feature
        self.editLayer : QgsVectorLayer = editLayer
        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 100))
        self.rubberBand.setLineStyle(1)
        self.rubberBand.setWidth(3)

        self.rubberBand2 = QgsRubberBand(self.mapCanvas)
        self.rubberBand2.setColor(QColor(255, 0, 0, 100))
        self.rubberBand2.setLineStyle(3)
        self.rubberBand2.setWidth(3)
        self.otherCanvas = otherCanvas

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.reset()
        self.tempLine : QgsGeometry = None

    def reset(self):
        self.points = []
        self.is_start = False  # 开始绘图
        self.cursor_point = None
        self.cursor_pos = None
        self.isEmittingPoint = False

        self.autoLong = -1 # 1 0 是缓冲区  -1 是真死了
        self.autoLongLastIndex = -1

        self.rubberBand.reset()
        self.rubberBand2.reset()
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)
        #stream tolerance
        self.lastPixelPos = None
        self.streamTolerance = appConfig.yoyiSetting().configSettingReader.value('streamTolerance',type=int)


    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,100))
        self.rubberBand2.setColor(QColor(r,g,b,100))
    
    def addPoint(self,point,streamCheck=False):
        if self.lastPixelPos:
            tempPosDis = math.sqrt((self.cursor_pos.x()-self.lastPixelPos.x())**2 + (self.cursor_pos.y()-self.lastPixelPos.y())**2)
            # 距离过近 小于根号2 删除
            if tempPosDis<1.415:
                return
            # 小于 流的容差 删除
            if streamCheck and self.lastPixelPos and tempPosDis<self.streamTolerance:
                return
        self.lastPixelPos : QPoint = self.cursor_pos
        self.points.append(point)
        self.is_start = True 
    
    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key_Backspace:
            if self.autoLong >= 0 and self.autoLongLastIndex >= 0 and len(self.points)>=1:
                self.points = self.points[:self.autoLongLastIndex]
                self.showPolygon()
            elif self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                self.showPolygon()
            else:
                self.reset()
    
    def canvasDoubleClickEvent(self, e: QgsMapMouseEvent) -> None:
        #print(e.button())
        if e.button() == Qt.LeftButton:
            self.autoLong = 1
            if self.points and len(self.points) >=1:
                self.autoLongLastIndex = len(self.points)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.cursor_pos:
                self.cursor_pos = event.pos()
                self.cursor_point = event.mapPoint()
                snapMatch = self.snapper.snapToMap(event.pos())
                self.snapIndicator.setMatch(snapMatch)
                if snapMatch.isValid():
                    self.cursor_point = snapMatch.point()
                    self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
            self.addPoint(self.cursor_point)
            if self.autoLong >= 0:
                self.autoLong -= 1

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.RightButton:
            # 右键结束
            self.tempLine: QgsGeometry = self.createTempPolyLine()
            if self.tempLine is not None:
                self.splitPolygonByTempLine()
            self.points = []
            self.isEmittingPoint = False

    def canvasMoveEvent(self, event):
        try:
            self.cursor_pos = event.pos()
            self.cursor_point = event.mapPoint()
            snapMatch = self.snapper.snapToMap(event.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                self.cursor_point = snapMatch.point()
                self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
                
            if self.autoLong == 1:
                self.addPoint(self.cursor_point,streamCheck=True)

            if not self.is_start:
                return
            self.showPolygon()
        except Exception as e:
            print(traceback.format_exc())
            MessageBox('提示', "缓存过多，已自动清除", self.parentWindow).exec_()
            self.reset()

    def showPolygon(self):
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        self.rubberBand2.reset(QgsWkbTypes.LineGeometry)  # 防止拖影
        first_point = self.points[0]
        last_point = self.points[-1]
        if first_point and last_point:
            self.rubberBand.addPoint(first_point, False)
            for point in self.points[1:-1]:
                self.rubberBand.addPoint(point, False)
            if self.cursor_point:
                self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), False)
            else:
                self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), True)
                self.rubberBand.show()
                return
            self.rubberBand.addPoint(self.cursor_point, True)
            self.rubberBand.show()
        
        if len(self.points) > 1 and self.cursor_point:
            print(len(self.points))
            self.rubberBand2.addPoint(self.points[0],False)
            self.rubberBand2.addPoint(self.cursor_point,True)
            self.rubberBand2.show()

    # 根据point数组创建线
    def createTempPolyLine(self):
        if self.points == []:
            return None
        res = QgsLineString()
        points = []
        for point in self.points:
            points.append(QgsPoint(point.x(),point.y()))
        res.setPoints(points)
        return res

    # 判断能不能裁剪 能的话就进行裁剪
    def splitPolygonByTempLine(self):
        self.beSplitFeatures = self.editLayer.selectedFeatures()
        tempLine = makeGeoIsVectorCrs( QgsLineString.fromQPolygonF(self.tempLine.asQPolygonF()),self.mapCanvasCrs,self.editLayer.crs() )

        if len(self.beSplitFeatures) == 0:
            tempRec : QgsRectangle = tempLine.boundingBox()
            self.beSplitFeatures = list(self.editLayer.getFeatures(tempRec))
        
        if len(self.beSplitFeatures) > 0:
            self.parentWindow.editStack.beginMacro("splitPolygon")
            for feature in self.beSplitFeatures:
                # Save the original geometry
                feature : QgsFeature
                featureGemtry : QgsGeometry = feature.geometry()
                featureGemtry = makeGeoIsVectorCrs( featureGemtry,self.mapCanvasCrs,self.editLayer.crs(),True )
                if featureGemtry:
                    if featureGemtry.wkbType() == 6:  # multipolygon 6
                        geometry = QgsGeometry.fromMultiPolygonXY(feature.geometry().asMultiPolygon())
                    else:  # polygon 3
                        geometry = QgsGeometry.fromMultiPolygonXY([feature.geometry().asPolygon()])

                    t,geos,_ = geometry.splitGeometry(self.points,True,False)
                    #t = geometry.reshapeGeometry(self.tempLine)
                    if t == 0:
                        self.editLayer.deleteFeature(feature.id())
                        for tempGeo in geos:
                            tempGeo = makeGeoIsVectorCrs( tempGeo,self.mapCanvasCrs,self.editLayer.crs() )
                            tempFeature = QgsFeature(self.editLayer.fields())
                            tempFeature.setGeometry(tempGeo)
                            tempFeature.setAttributes(feature.attributes())
                            self.editLayer.addFeature(tempFeature)
                    elif len(self.points) > 2:
                        points = [point for point in self.points]
                        points.append(self.points[0])
                        t2 = geometry.addRing(points)
                        print("addRing状态",t2)
                        if t2 == 0:
                            geometry = makeGeoIsVectorCrs( geometry,self.mapCanvasCrs,self.editLayer.crs() )
                            self.editLayer.changeGeometry(feature.id(),geometry)
                            pointList = []
                            for point in self.points:
                                pointList.append(QgsPointXY(point[0],point[1]))
                            tempPolygon : QgsGeometry = QgsGeometry.fromMultiPolygonXY([[pointList]])
                            resPolygon = tempPolygon.makeValid()
                            if resPolygon.type() == 2: #PolygonGeometry type: QgsWkbTypes.GeometryType
                                resPolygon = makeGeoIsVectorCrs( resPolygon,self.mapCanvasCrs,self.editLayer.crs() )
                                tempFeature = QgsFeature(self.editLayer.fields())
                                tempFeature.setGeometry(resPolygon)
                                tempFeature.setAttributes(feature.attributes())
                                self.editLayer.addFeature(tempFeature)
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.reset()

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super(SplitPolygonMapTool, self).deactivate()

# 重塑要素 mapTool
class ReShapePolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,editLayer, parentWindow,otherCanvas=None):
        super(ReShapePolygonMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.editLayer : QgsVectorLayer = editLayer
        self.parentWindow = parentWindow

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 100))
        self.rubberBand.setLineStyle(1)
        self.rubberBand.setWidth(3)

        self.rubberBand2 = QgsRubberBand(self.mapCanvas)
        self.rubberBand2.setColor(QColor(255, 0, 0, 100))
        self.rubberBand2.setLineStyle(3)
        self.rubberBand2.setWidth(3)
        self.otherCanvas = otherCanvas
        self.reset()
        self.tempLine: QgsGeometry = None

    def reset(self):
        self.points = []
        self.is_start = False  # 开始绘图
        self.cursor_point = None
        self.cursor_pos = None
        self.isEmittingPoint = False

        self.autoLong = -1 # 1 0 是缓冲区  -1 是真死了
        self.autoLongLastIndex = -1

        self.rubberBand.reset()
        self.rubberBand2.reset()
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)
        #stream tolerance
        self.lastPixelPos = None
        self.streamTolerance = appConfig.yoyiSetting().configSettingReader.value('streamTolerance',type=int)


    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,100))
        self.rubberBand2.setColor(QColor(r,g,b,100))
    
    def keyReleaseEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key_Backspace:
            if self.autoLong >= 0 and self.autoLongLastIndex >= 0 and len(self.points)>=1:
                self.points = self.points[:self.autoLongLastIndex]
                self.showPolygon()
                self.autoLong = -1
            elif self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                self.showPolygon()
            else:
                self.reset()
    
    def canvasDoubleClickEvent(self, e: QgsMapMouseEvent) -> None:
        if e.button() == Qt.LeftButton:
            self.autoLong = 1
            if self.points and len(self.points) >=1:
                self.autoLongLastIndex = len(self.points)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.cursor_pos:
                self.cursor_pos = event.pos()
                self.cursor_point = event.mapPoint()
                snapMatch = self.snapper.snapToMap(event.pos())
                self.snapIndicator.setMatch(snapMatch)
                if snapMatch.isValid():
                    self.cursor_point = snapMatch.point()
                    self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
            self.addPoint(self.cursor_point)
            if self.autoLong >= 0:
                self.autoLong -= 1

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.RightButton:
            # 右键结束
            #self.points.append(self.cursor_point)
            self.tempLine: QgsGeometry = self.createTempPolyLine()
            if self.tempLine is not None:
                self.splitPolygonByTempLine()
            self.points = []
            self.isEmittingPoint = False

    def addPoint(self,point,streamCheck=False):
        if self.lastPixelPos:
            tempPosDis = math.sqrt((self.cursor_pos.x()-self.lastPixelPos.x())**2 + (self.cursor_pos.y()-self.lastPixelPos.y())**2)
            # 距离过近 小于根号2 删除
            if tempPosDis<1.415:
                return
            # 小于 流的容差 删除
            if streamCheck and self.lastPixelPos and tempPosDis<self.streamTolerance:
                return
        self.lastPixelPos : QPoint = self.cursor_pos
        self.points.append(point)
        self.is_start = True

    def canvasMoveEvent(self, event):
        try:
            self.cursor_pos = event.pos()
            self.cursor_point = event.mapPoint()
            snapMatch = self.snapper.snapToMap(event.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                self.cursor_point = snapMatch.point()
                self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
                
            if self.autoLong == 1:
                self.addPoint(self.cursor_point,streamCheck=True)
            if not self.is_start:
                return
            self.showPolygon()
        except Exception as e:
            MessageBox('提示', "缓存过多，已自动清除", self.parentWindow).exec_()
            self.reset()

    def showPolygon(self):
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)  # 防止拖影
        self.rubberBand2.reset(QgsWkbTypes.LineGeometry)  # 防止拖影
        first_point = self.points[0]
        last_point = self.points[-1]
        if first_point and last_point:
            self.rubberBand.addPoint(first_point, False)
            for point in self.points[1:-1]:
                self.rubberBand.addPoint(point, False)
            if self.cursor_point:
                self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), False)
            else:
                self.rubberBand.addPoint(QgsPointXY(last_point.x(), last_point.y()), True)
                self.rubberBand.show()
                return
            self.rubberBand.addPoint(self.cursor_point, True)
            self.rubberBand.show()
        
        if len(self.points) > 1 and self.cursor_point:
            print(len(self.points))
            self.rubberBand2.addPoint(self.points[0],False)
            self.rubberBand2.addPoint(self.cursor_point,True)
            self.rubberBand2.show()

    # 根据point数组创建线
    def createTempPolyLine(self):
        if self.points == []:
            return None
        res = QgsGeometry.fromPolylineXY(self.points)
        return res

    # 判断能不能裁剪 能的话就进行裁剪
    # 如果裁剪失败，则尝试添加环，如果还失败就GG
    def splitPolygonByTempLine(self):
        self.beSplitFeatures = self.editLayer.selectedFeatures()
        tempLine = makeGeoIsVectorCrs( QgsLineString.fromQPolygonF(self.tempLine.asQPolygonF()),self.mapCanvas.mapSettings().destinationCrs(),self.editLayer.crs() )
        
        if len(self.beSplitFeatures) == 0:
            tempRec : QgsRectangle = tempLine.boundingBox()
            self.beSplitFeatures = list(self.editLayer.getFeatures(tempRec))
        
        if len(self.beSplitFeatures) > 0:
            self.parentWindow.editStack.beginMacro("reshapePolygon")
            for feature in self.beSplitFeatures:
                # Save the original geometry
                feature: QgsFeature
                featureGemtry: QgsGeometry = feature.geometry()
                #QgsWkbTypes.GeometryType
                #print(featureGemtry.wkbType(),featureGemtry.type())
                if featureGemtry:
                    if featureGemtry.wkbType() == 6: # multipolygon 6
                        geometry = QgsGeometry.fromMultiPolygonXY(feature.geometry().asMultiPolygon())
                    else: # polygon 3
                        geometry = QgsGeometry.fromMultiPolygonXY([feature.geometry().asPolygon()])
                    # t = feature.geometry().reshapeGeometry(QgsLineString.fromQPolygonF(self.tempLine.asQPolygonF()))
                    t = geometry.reshapeGeometry(tempLine)
                    print("reshape状态",t)
                    if t == 0:
                        self.editLayer.changeGeometry(feature.id(),geometry)
                    elif len(self.points) > 2:
                        #if featureGemtry.wkbType() == 3:
                        #     geometry = QgsGeometry.fromMultiPolygonXY([feature.geometry().asPolygon()])
                        mapcanvasCrsGeo = makeGeoIsVectorCrs( featureGemtry,self.mapCanvas.mapSettings().destinationCrs(),self.editLayer.crs(),True )
                        points = [point for point in self.points]
                        points.append(self.points[0])
                        t2 = mapcanvasCrsGeo.addRing(points)
                        print("addRing状态",t2)
                        if t2 == 0:
                            mapcanvasCrsGeoNew = makeGeoIsVectorCrs(featureGemtry,self.mapCanvas.mapSettings().destinationCrs(),self.editLayer.crs() )
                            self.editLayer.changeGeometry(feature.id(),mapcanvasCrsGeoNew)
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.reset()

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super(ReShapePolygonMapTool, self).deactivate()
        

# 粘贴要素 mapTool
class PastePolygonMapTool(QgsMapToolIdentify):
    def __init__(self, canvas, editLayer, parentWindow, otherCanvas=None):
        super(PastePolygonMapTool, self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.editLayer: QgsVectorLayer = editLayer
        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setLineStyle(2)
        self.rubberBand.setColor(QColor(255, 200, 0, 100))
        self.rubberBand.setWidth(3)

        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.editLayer.removeSelection()
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.tempMoveCenter = None #当前选中要素的质心

    # 重新渲染Rubber Band
    def reshapeRubberBand(self,tempGeo:QgsGeometry):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.addGeometry(tempGeo)

    def showMoveShape(self,tempPoint,trueChange=False):
        if trueChange:
            self.parentWindow.editStack.beginMacro("pastePolygon")
        
        feature : QgsFeature = self.editLayer.getFeature(self.featureId)
        newGeometry = feature.geometry()
        newGeometry.translate(tempPoint.x() - self.tempMoveCenter.x(), tempPoint.y() - self.tempMoveCenter.y())
        if trueChange:
            newFeature = QgsFeature(self.editLayer.fields())
            newFeature.setGeometry(newGeometry)
            newFeature.setAttributes(feature.attributes())
            self.editLayer.addFeature(newFeature)

        if trueChange:
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
        else:
            self.reshapeRubberBand(newGeometry)
    
    def canvasPressEvent(self, e: QgsMapMouseEvent):
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
                if resList:
                    self.featureId = resList[0].mFeature.id()
                    self.editLayer.selectByIds([self.featureId])
                    featureTempGeo = self.editLayer.getFeature(self.featureId).geometry()
                    self.tempMoveCenter = featureTempGeo.centroid().asPoint()
            # 如果选中了要素, 那确定复制
            else:
                self.showMoveShape(tempPoint, True)
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.removeSelection()
            self.reset() 

    def canvasMoveEvent(self, e):
        if self.featureId is not None:
            tempPoint = self.toMapCoordinates(e.pos())
            self.showMoveShape(tempPoint)

    def deactivate(self):
        self.reset()
        super().deactivate()

# 移动要素 mapTool
class MovePolygonMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,otherCanvas=None):
        super(MovePolygonMapTool,self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.editLayer: QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setLineStyle(2)
        self.rubberBand.setColor(QColor(255, 200, 0, 100))
        self.rubberBand.setWidth(3)
        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.otherCanvas = otherCanvas
        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.isEmittingPoint = False  # 有没有点击左键
        self.selectFeatureId = None # 选择的要素的id
        self.selectFeature : QgsFeature = None # 选择的要素的Geometry
        self.tempPoint = None

    # 重新渲染Rubber Band
    def reshapeRubberBand(self,geometry):
        self.rubberBand.reset()
        self.rubberBand.addGeometry(geometry)
        # for point in points:
        #     self.rubberBand.addPoint(point)

    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if not self.isEmittingPoint:
            resList : list = self.identify(e.x(),e.y(),layerList=[self.editLayer],mode=self.mode)
            if len(resList) >0:
                self.selectFeatureId = resList[0].mFeature.id()
                self.selectFeature : QgsFeature = self.editLayer.getFeature(self.selectFeatureId)
                self.tempPoint = tempPoint
                self.isEmittingPoint = True
        else:
            newGeometry = self.selectFeature.geometry()
            newGeometry.translate(tempPoint.x() - self.tempPoint.x(), tempPoint.y() - self.tempPoint.y())
            self.editLayer.changeGeometry(self.selectFeatureId,newGeometry)
            self.parentWindow.updateShpUndoRedoButton()
            self.reset()
            self.mapCanvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()


    def canvasMoveEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if self.isEmittingPoint:
            newGeometry = self.selectFeature.geometry()
            newGeometry.translate(tempPoint.x()-self.tempPoint.x(),tempPoint.y()-self.tempPoint.y())
            self.reshapeRubberBand(newGeometry)

    def deactivate(self):
        self.reset()
        super().deactivate()

# 框选勾选矢量 -- mapTool
class RecTangleSelectFeatureMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,alwaysUpdate=False,otherCanvas=None,selector=None,labelField=None,allowCopy=False):
        super(RecTangleSelectFeatureMapTool,self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.editLayer: QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.alwaysUpdate = alwaysUpdate
        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setLineStyle(Qt.DashLine)
        #self.rubberBand.setBrushStyle(Qt.CrossPattern)
        self.rubberBand.setWidth(3)
        self.mode = QgsMapToolIdentify.TopDownAll
        self.otherCanvas = otherCanvas
        self.selector = selector
        self.labelField = labelField
        self.allowCopy = allowCopy
        
        self.refreshForm()
        self.reset()
    
    def refreshForm(self):
        mapSetting : QgsMapSettings = self.mapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        crs : QgsCoordinateReferenceSystem = self.editLayer.crs()
        if crs.srsid() == "EPSG:4326":
            self.xform = None
        else:
            crsDest = QgsCoordinateReferenceSystem("EPSG:4326")
            transformContext = PROJECT.transformContext()
            self.xform = QgsCoordinateTransform(crs, crsDest, transformContext)
        
        if crs.authid() == mapCrs.authid():
            self.selectform = None
        else:
            transformContext = PROJECT.transformContext()
            self.selectform = QgsCoordinateTransform(mapCrs, crs, transformContext)

    def reset(self,resetIds=True):
        # 是否允许移动要素
        self.allowMoveFeature = appConfig.yoyiSetting().configSettingReader.value('allowMoveFeature',type=bool)
        # 允许移动的最小距离
        self.minMoveDistance = appConfig.yoyiSetting().configSettingReader.value('minMovementDistance',type=int)
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.tempMoveCenter = None # 移动要素的基点
        self.tempMoveCenterPos = None #移动要素的屏幕位置点
        self.mapToolMode = 0 # 0 画框选择要素 1 拖动要素 2 编辑要素
        if resetIds:
            self.tempSelectedIds = None
        self.rubberBand.reset()
        

    def deleteSelectedTriggered(self):
        print(self.tempSelectedIds)
        if self.tempSelectedIds:
            self.parentWindow.editStack.beginMacro("deletePolygon")
            self.editLayer.deleteSelectedFeatures()
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.mapCanvas.refresh()
            
    def simplifySelectedTriggered(self):
        if self.tempSelectedIds:
            features = self.editLayer.getFeatures(self.tempSelectedIds)
            self.parentWindow.editStack.beginMacro("simplify")
            for feature in features:
                feature : QgsFeature
                tempGeo : QgsGeometry = feature.geometry()
                if self.xform:
                    tempGeo.transform(self.xform)
                newGeo : QgsGeometry = tempGeo.simplify(0.00001)
                newGeo.transform(self.xform,self.xform.ReverseTransform)
                if newGeo.isGeosValid():
                    self.editLayer.changeGeometry(feature.id(),newGeo)
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.mapCanvas.refresh()

    def splitPartTriggered(self):
        if self.tempSelectedIds:
            features = self.editLayer.getFeatures(self.tempSelectedIds)
            self.parentWindow.editStack.beginMacro("splitFeatures")
            for feature in features:
                feature : QgsFeature
                tempGeo : QgsGeometry = feature.geometry()
                partList = []
                for part in tempGeo.parts():
                    partList.append(part)
                if len(partList) > 1:
                    for part in partList:
                        part: QgsPolygon
                        # print(part.isGeosValid())
                        feat = QgsFeature(self.editLayer.fields())
                        feat.setAttributes(feature.attributes())
                        feat.setGeometry(QgsGeometry.fromWkt(part.asWkt()))
                        self.editLayer.addFeature(feat)
                    self.editLayer.deleteFeature(feature.id())
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.mapCanvas.refresh()

    def fillHoleTriggered(self):
        if self.tempSelectedIds:
            features = self.editLayer.getFeatures(self.tempSelectedIds)
            self.parentWindow.editStack.beginMacro("simplify")
            for feature in features:
                feature : QgsFeature
                tempGeo : QgsGeometry = feature.geometry()
                newGeo : QgsGeometry = tempGeo.removeInteriorRings()
                if newGeo.isGeosValid():
                    self.editLayer.changeGeometry(feature.id(),newGeo)
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
            self.mapCanvas.refresh()
    
    def copyFeaturesTriggered(self):
        if self.tempSelectedIds:
            features = self.editLayer.getFeatures(self.tempSelectedIds)
            geomList = []
            for feature in features:
                geom = feature.geometry()
                geom.transform(self.selectform)
                geomList.append(geom)
            
            self.parentWindow.copyFeatures(geomList)

    # 右键窗口触发事件
    def on_custom_menu_requested(self):
        cusMenu = RoundMenu(parent=self.parentWindow)
        cusMenu.setItemHeight(50)
        if self.editLayer.isEditable():
            deleteSelected = Action(QIcon(":/img/resources/gis/shp_delete_select.png"), '删除所选要素')
            deleteSelected.triggered.connect(self.deleteSelectedTriggered)
            cusMenu.addAction(deleteSelected)
            simplifySelected = Action(QIcon(":/img/resources/shpProcess/shp_simply.png"), '简化所选要素')
            simplifySelected.triggered.connect(self.simplifySelectedTriggered)
            cusMenu.addAction(simplifySelected)
            splitParts = Action(QIcon(":/img/resources/shpProcess/shp_split.png"), '拆分所选要素组件')
            splitParts.triggered.connect(self.splitPartTriggered)
            cusMenu.addAction(splitParts)
            fillHole = Action(QIcon(":/img/resources/shpProcess/shp_removeHole.png"), '填充所选要素孔洞')
            fillHole.triggered.connect(self.fillHoleTriggered)
            cusMenu.addAction(fillHole)
        if self.allowCopy:
            copyFeatures = Action(FIF.COPY, '复制选中要素...')
            copyFeatures.triggered.connect(self.copyFeaturesTriggered)
            cusMenu.addAction(copyFeatures)
        
        curPos : QPoint = QCursor.pos()
        #cusMenu.menuActions()[0].setShortcut("1")
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)

    def isIntersectSelectedIds(self,e):
        #print(self.tempBoundingBox)
        if self.tempSelectedIds:
            resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
            ids = [i.mFeature.id() for i in resList]
            if ids and ids[0] in self.tempSelectedIds:
                #print(ids[0],self.tempSelectedIds)
                return True
        return False

    def canvasPressEvent(self,e):
        tempPoint : QgsPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.LeftButton and not self.isEmittingPoint:
            if self.editLayer.isEditable() and self.isIntersectSelectedIds(e):
                if self.allowMoveFeature:
                    self.mapToolMode = 1
                    self.isEmittingPoint = True
                    self.tempMoveCenter = tempPoint
                    self.tempMoveCenterPos = e.pos()
                    self.mapCanvas.setCursor(Qt.SizeAllCursor)
                else:
                    self.mapToolMode = 0
                    self.startPoint = tempPoint
                    self.endPoint = self.startPoint
                    self.isEmittingPoint = True
                    self.mapCanvas.setCursor(Qt.ArrowCursor)
            else:
                self.startPoint = tempPoint
                self.endPoint = self.startPoint
                self.isEmittingPoint = True
                self.mapCanvas.setCursor(Qt.ArrowCursor)
        if e.button() == Qt.RightButton:
            if self.tempSelectedIds:
                self.on_custom_menu_requested()

    def canvasMoveEvent(self, e):
        tempPos = e.pos()
        tempPoint: QgsPoint = self.toMapCoordinates(tempPos)

        if self.mapToolMode == 0 and self.isEmittingPoint:
            self.endPoint = tempPoint
            self.showRect(self.startPoint, self.endPoint)
        elif self.mapToolMode == 1 and self.tempMoveCenter and self.isEmittingPoint:
            self.showMoveShape(tempPoint,tempPos)

    def canvasReleaseEvent(self, e):
        tempPos = e.pos()
        tempPoint: QgsPoint = self.toMapCoordinates(tempPos)
        if self.mapToolMode == 0:
            res = self.rectangle()
            if res == 1:
                #print(f"QgsPointXY")
                resList : list = self.identify(e.x(),e.y(),layerList=[self.editLayer],mode=self.mode)
                ids = [i.mFeature.id() for i in resList]
            elif type(res) == QgsRectangle:
                if self.selectform:
                    tempGeo = QgsGeometry.fromRect(res)
                    tempGeo.transform(self.selectform)
                    res = tempGeo.boundingBox()
                print(res)
                self.editLayer.selectByRect(res)
                ids = ""
            else:
                ids = []
            if type(ids) == str:
                self.tempSelectedIds = self.editLayer.selectedFeatureIds()
            elif len(ids) > 0:
                if e.modifiers() & Qt.ControlModifier:
                    ids = list(set(self.editLayer.selectedFeatureIds() + ids))
                self.editLayer.selectByIds(ids)
                self.tempSelectedIds = self.editLayer.selectedFeatureIds()
            else:
                self.editLayer.removeSelection()
                self.tempSelectedIds = None
        elif self.mapToolMode == 1:
            self.showMoveShape(tempPoint,tempPos,True)
            #self.editLayer.changeGeometry(self.selectFeatureId,newGeometry)
        self.reset(False)
        self.mapCanvas.refresh()
        self.mapCanvas.setCursor(Qt.ArrowCursor)
        if self.otherCanvas:
            self.otherCanvas.refresh()

    # 重新渲染Rubber Band
    def reshapeRubberBand(self, geometryList):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        for geometry in geometryList:
            self.rubberBand.addGeometry(geometry)

    def showMoveShape(self,tempPoint,tempPos,trueChange=False):
        
        tempPosDis = math.sqrt((self.tempMoveCenterPos.x()-tempPos.x())**2 + (self.tempMoveCenterPos.y()-tempPos.y())**2)
        if tempPosDis <= self.minMoveDistance:
            return

        if trueChange:
            self.parentWindow.editStack.beginMacro("movePolygon")
        else:
            geometryList = []
        for id in self.tempSelectedIds:
            newGeometry = makeGeoIsVectorCrs(self.editLayer.getFeature(id).geometry(),
                                             self.mapCanvas.mapSettings().destinationCrs(),
                                             self.editLayer.crs(),True) 
            newGeometry.translate(tempPoint.x() - self.tempMoveCenter.x(), tempPoint.y() - self.tempMoveCenter.y())
            if trueChange:
                newGeometry = makeGeoIsVectorCrs(newGeometry,
                                                self.mapCanvas.mapSettings().destinationCrs(),
                                                self.editLayer.crs())
                self.editLayer.changeGeometry(id, newGeometry)
            else:
                geometryList.append(newGeometry)
        if trueChange:
            self.parentWindow.editStack.endMacro()
            self.parentWindow.updateShpUndoRedoButton()
        else:
            self.reshapeRubberBand(geometryList)

    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())
        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)  # true to update canvas
        self.rubberBand.show()

    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return 1
        return QgsRectangle(self.startPoint, self.endPoint)

    def deactivate(self):
        self.reset()
        super().deactivate()

# 删除环 -- mapTool
class FillHoleMapTool(QgsMapToolIdentify):
    def __init__(self, canvas, drawLayer,parentWindow,otherCanvas=None):
        super(FillHoleMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.drawLayer: QgsVectorLayer = drawLayer
        self.caps = self.drawLayer.dataProvider().capabilities()
        self.parentWindow = parentWindow
        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.otherCanvas = otherCanvas

    def canvasPressEvent(self, e):
        resList: list = self.identify(e.x(), e.y(), layerList=[self.drawLayer], mode=self.mode)
        if len(resList) >0 :
            selectFeatureId = resList[0].mFeature.id()
            selectFeature : QgsFeature = self.drawLayer.getFeature(selectFeatureId)
            tempGeo : QgsGeometry = selectFeature.geometry()
            self.drawLayer.changeGeometry(selectFeatureId, tempGeo.removeInteriorRings())
            #self.drawLayer.changeAttributeValue()
            self.parentWindow.updateShpUndoRedoButton()
            self.mapCanvas.refresh()
            if self.otherCanvas:
                self.otherCanvas.refresh()

    def deactivate(self):
        super().deactivate()

# 分离部件 -- mapTool
class SplitPartsMapTool(QgsMapToolIdentify):
    def __init__(self, canvas, drawLayer,parentWindow,otherCanvas=None):
        super(SplitPartsMapTool, self).__init__(canvas)
        self.mapCanvas = canvas
        self.drawLayer: QgsVectorLayer = drawLayer
        self.caps = self.drawLayer.dataProvider().capabilities()
        self.parentWindow = parentWindow
        self.mode = QgsMapToolIdentify.TopDownStopAtFirst
        self.otherCanvas = otherCanvas

    def canvasPressEvent(self, e):
        resList: list = self.identify(e.x(), e.y(), layerList=[self.drawLayer], mode=self.mode)
        if len(resList) >0 :
            selectFeatureId = resList[0].mFeature.id()
            selectFeature : QgsFeature = self.drawLayer.getFeature(selectFeatureId)
            tempGeo : QgsGeometry = selectFeature.geometry()
            self.parentWindow.editStack.beginMacro("splitFeatures")
            partList = []
            for part in tempGeo.parts():
                partList.append(part)
            if len(partList) > 1:
                for part in partList:
                    part : QgsPolygon
                    #print(part.isGeosValid())
                    feat = QgsFeature(self.drawLayer.fields())
                    feat.setAttributes(selectFeature.attributes())
                    feat.setGeometry(QgsGeometry.fromWkt(part.asWkt()))
                    self.drawLayer.addFeature(feat)
                self.drawLayer.deleteFeature(selectFeature.id())
                self.parentWindow.editStack.endMacro()
                #self.drawLayer.changeAttributeValue()
                self.parentWindow.updateShpUndoRedoButton()
                self.mapCanvas.refresh()
                if self.otherCanvas:
                    self.otherCanvas.refresh()

    def deactivate(self):
        super().deactivate()

class RectangleSelectExtentMapTool(QgsMapToolEmitPoint):
    drawed = pyqtSignal(str)
    def __init__(self,canvas,containExtent=None,minArea=None,extraCrs=None,parent=None):
        super(RectangleSelectExtentMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.parentWindow = parent
        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(3)
        self.crossVertex = QgsVertexMarker(self.mapCanvas)
        self.crossVertex.setIconType(QgsVertexMarker.ICON_CROSS)
        self.crossVertex.setIconSize(2000)
        self.reset()

        self.containExtent : QgsRectangle = containExtent
        self.minArea = minArea
        self.extraCrs : QgsCoordinateReferenceSystem = extraCrs
        self.mapSetting : QgsMapSettings = self.mapCanvas.mapSettings()
        self.distanceArea = QgsDistanceArea()
        self.distanceArea.setSourceCrs(self.mapSetting.destinationCrs(),PROJECT.transformContext())
        self.distanceArea.setEllipsoid("EPSG:7030")
    
    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.r : QgsRectangle = None
        self.rubberBand.reset()
    
    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.LeftButton:
            if not self.isEmittingPoint:
                self.startPoint = self.toMapCoordinates(e.pos())
                self.endPoint = self.startPoint
                self.isEmittingPoint = True
                self.showRect(self.startPoint, self.endPoint)
        elif e.button() == Qt.RightButton:
            if self.isEmittingPoint and self.rectangle():
                self.r = self.rectangle()
                self.isEmittingPoint = False
                self.addFeature()
    
    def canvasMoveEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        self.crossVertex.setCenter(tempPoint)
        if not self.isEmittingPoint:
            if self.r:
                pass
            elif self.startPoint:
                self.showLine([self.startPoint, tempPoint])
        else:
            self.endPoint = tempPoint
            self.showRect(self.startPoint, self.endPoint)
    
    def showLine(self,points):
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
        for point in points:
            self.rubberBand.addPoint(point, False)
        self.rubberBand.show()
    
    def showRect(self, startPoint, endPoint):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
            return
        point1 = QgsPointXY(startPoint.x(), startPoint.y())
        point2 = QgsPointXY(startPoint.x(), endPoint.y())
        point3 = QgsPointXY(endPoint.x(), endPoint.y())
        point4 = QgsPointXY(endPoint.x(), startPoint.y())
        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)  # true to update canvas
        self.rubberBand.show()
    
    def addFeature(self):
        if self.containExtent:
            if not self.containExtent.contains(self.r):
                MessageBox('错误', "未与图层相交", self.parentWindow).exec_()
                return
        if self.minArea:
            tempGeo = QgsGeometry.fromRect(self.r)
            area = self.distanceArea.measureArea(tempGeo)
            if self.minArea > area:
                MessageBox('错误', f"当前面积：{(area/1000000):.4f}平方公里。面积过小！", self.parentWindow).exec_()
                return
        mapSetting : QgsMapSettings = self.mapCanvas.mapSettings()
        crs = mapSetting.destinationCrs().authid()
        extentStr = f"{self.r.xMinimum():.4f},{self.r.xMaximum():.4f},{self.r.yMinimum():.4f},{self.r.yMaximum():.4f} [{crs}]"
        
        if self.extraCrs:
            if crs == self.extraCrs.authid():
                extraRectangle = self.r
                self.extraTuple = (extraRectangle.xMinimum(),extraRectangle.yMinimum(),extraRectangle.xMaximum(),extraRectangle.yMaximum())
            else:
                xform = QgsCoordinateTransform(mapSetting.destinationCrs(),self.extraCrs,PROJECT.transformContext())
                tempGeo = QgsGeometry.fromRect(self.r)
                tempGeo.transform(xform)
                extraRectangle = tempGeo.boundingBox()
                self.extraTuple = (extraRectangle.xMinimum(),extraRectangle.yMinimum(),extraRectangle.xMaximum(),extraRectangle.yMaximum())
            
        self.reset()
        
        self.drawed.emit(extentStr)
        
    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return None
        res = QgsRectangle(self.startPoint, self.endPoint)
        return res

    def deactivate(self):
        try:
            self.mapCanvas.scene().removeItem(self.crossVertex)
        except:
            pass
        self.reset()
        super().deactivate()

# 识别栅格图层
class IdentifyRasterMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,rasterLayer,parentWindow):
        super(IdentifyRasterMapTool, self).__init__(canvas)
        self.mapCanvas:QgsMapCanvas = canvas
        self.rasterLayer : QgsRasterLayer = rasterLayer
        self.parentWindow = parentWindow
        
        mapSetting : QgsMapSettings = self.mapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        crs : QgsCoordinateReferenceSystem = self.rasterLayer.crs()
        if crs.authid() == mapCrs.authid():
            self.selectform = None
        else:
            transformContext = PROJECT.transformContext()
            self.selectform = QgsCoordinateTransform(mapCrs, crs, transformContext)
    
    def changeRasterLayer(self,rasterLayer):
        self.rasterLayer : QgsRasterLayer = rasterLayer

    def canvasPressEvent(self, e):
        self.point : QgsPointXY = self.toMapCoordinates(e.pos())
        
        if self.selectform:
            tempGeo = QgsGeometry.fromPointXY(self.point)
            tempGeo.transform(self.selectform)
            tempPoint = tempGeo.asPoint()
            x = tempPoint.x()
            y = tempPoint.y()
        else:
            x = self.point.x()
            y = self.point.y()
        

        bandInfo  = {}
        for band in range(self.rasterLayer.bandCount()):
            val, res = self.rasterLayer.dataProvider().sample(QgsPointXY(x, y), band+1)
            if res:
                bandInfo[band+1] = val
            else:
                bandInfo[band+1] = 0
        self.parentWindow.showFeatureByTif(bandInfo,x,y)
        #self.marker.setCenter(self.point)

    def deactivate(self):
        super().deactivate()


# 测量距离工具
class MeasureDistanceMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas: QgsMapCanvas,parentWindow=None) -> None:
        super().__init__(canvas)
        self.mapCanvas = canvas
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()

        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas,QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(5)
        
        self.markList = []

        self.distanceArea = QgsDistanceArea()
        self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
        self.measureDialog = MeasureDistanceMapToolDialogClass(self.distanceArea,self.parentWindow)
        self.measureDialog.listCleared.connect(self.reset)
        self.measureDialog.ellipsoidChanged.connect(self.changeEllipsoid)
        self.measureDialog.show()

        self.reset()
    
    def reset(self):
        for mark in self.markList:
            self.mapCanvas.scene().removeItem(mark)

        self.markList = []

        self.is_start = False  # 开始绘图
        self.is_finished = False # 绘图已经结束了 下次画需要把之前的都清空
        self.have_temp_point = False #左键点击后，没有临时的rubberband点
        self.cursor_point = None

        
        self.rubberBand.reset(QgsWkbTypes.LineGeometry)
    
    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))
    
    def changeEllipsoid(self,mode):
        if mode == 0:
            self.distanceArea = QgsDistanceArea()
            self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
        else:
            self.distanceArea = QgsDistanceArea()
            self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
            self.distanceArea.setEllipsoid("EPSG:7030")
        
        self.measureDialog.itemsClear()
    
    def canvasPressEvent(self, event: QgsMapMouseEvent) -> None:
        
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_finished:
                self.measureDialog.itemsClear()
            self.rubberBand.addPoint(event.mapPoint())

            tempPointVertex = QgsVertexMarker(self.mapCanvas)
            tempPointVertex.setIconType(QgsVertexMarker.ICON_CIRCLE)
            tempPointVertex.setIconSize(10)
            tempPointVertex.setFillColor(QColor("yellow"))
            tempPointVertex.setCenter(event.mapPoint())
            self.markList.append(tempPointVertex)
            self.have_temp_point = False

            self.measureDialog.addTempListWidget()
            self.is_start = True

        elif event.button() == Qt.MouseButton.RightButton:
            if self.have_temp_point:
                self.rubberBand.removeLastPoint(doUpdate=True)
                self.have_temp_point = False
            self.is_start = False
            self.is_finished = True
        
        super().canvasPressEvent(event)
    
    def canvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        if not self.is_start:
            return
        self.cursor_point = event.mapPoint()
        self.showLine()
    
    def showLine(self):
        
        if self.rubberBand.numberOfVertices() == 0:
            return
        elif self.rubberBand.numberOfVertices() == 1:
            pass
        else:
            self.rubberBand.removeLastPoint(doUpdate=True)

        self.rubberBand.addPoint(self.cursor_point,True)
        self.have_temp_point = True

        tempGeo = self.rubberBand.asGeometry()
        point1 = tempGeo.vertexAt(self.rubberBand.numberOfVertices()-2)
        point2 = tempGeo.vertexAt(self.rubberBand.numberOfVertices()-1)
        distance = self.distanceArea.measureLine(QgsPointXY(point1),QgsPointXY(point2))
        self.measureDialog.changeLastItem(distance)


    def deactivate(self) -> None:
        self.reset()
        try:
            self.measureDialog.close()
        except:
            pass
        super().deactivate()

# 测量面积工具
class MeasureAreaMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas: QgsMapCanvas,parentWindow=None) -> None:
        super().__init__(canvas)
        self.mapCanvas = canvas
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()

        self.parentWindow = parentWindow

        self.rubberBand = QgsRubberBand(self.mapCanvas,QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(5)

        self.markList = []

        self.distanceArea = QgsDistanceArea()
        self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
        self.measureDialog = MeasureAreaMapToolDialogClass(self.distanceArea,self.parentWindow)
        self.measureDialog.cleared.connect(self.reset)
        self.measureDialog.ellipsoidChanged.connect(self.changeEllipsoid)
        self.measureDialog.show()
        self.reset()
    
    def reset(self):
        for mark in self.markList:
            self.mapCanvas.scene().removeItem(mark)

        self.markList = []

        self.is_start = False  # 开始绘图
        self.is_finished = False # 绘图已经结束了 下次画需要把之前的都清空
        self.have_temp_point = False #左键点击后，没有临时的rubberband点
        self.cursor_point = None

        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
    
    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))
    
    def changeEllipsoid(self,mode):
        if mode == 0:
            self.distanceArea = QgsDistanceArea()
            self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
        else:
            self.distanceArea = QgsDistanceArea()
            self.distanceArea.setSourceCrs(self.mapCanvasCrs,PROJECT.transformContext())
            self.distanceArea.setEllipsoid("EPSG:7030")
        
        self.measureDialog.itemClear()
    
    def canvasPressEvent(self, event: QgsMapMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_finished:
                self.measureDialog.itemClear()
            self.rubberBand.addPoint(event.mapPoint())

            tempPointVertex = QgsVertexMarker(self.mapCanvas)
            tempPointVertex.setIconType(QgsVertexMarker.ICON_CIRCLE)
            tempPointVertex.setIconSize(10)
            tempPointVertex.setFillColor(QColor("yellow"))
            tempPointVertex.setCenter(event.mapPoint())
            self.markList.append(tempPointVertex)
            self.have_temp_point = False

            self.is_start = True
        
        elif event.button() == Qt.MouseButton.RightButton:
            if self.have_temp_point:
                self.rubberBand.removeLastPoint(doUpdate=True)
                self.have_temp_point = False
            self.is_start = False
            self.is_finished = True
        
        super().canvasPressEvent(event)
    
    def canvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        if not self.is_start:
            return
        self.cursor_point = event.mapPoint()
        self.showPolygon()
    
    def showPolygon(self):
        if self.rubberBand.numberOfVertices() == 0:
            return
        elif self.rubberBand.numberOfVertices() == 1:
            pass
        else:
            self.rubberBand.removeLastPoint(doUpdate=True)
        
        self.rubberBand.addPoint(self.cursor_point,True)
        self.have_temp_point = True

        tempGeo = self.rubberBand.asGeometry()
        area = self.distanceArea.measureArea(tempGeo)
        self.measureDialog.changeItem(area)
    
    def deactivate(self):
        self.reset()
        try:
            self.measureDialog.close()
        except:
            pass
        super().deactivate()



        



