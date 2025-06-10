# -*- coding: utf-8 -*-
# @Author  : yoyi
# @Time    : 2022/6/7 15:30
import numpy as np
import math
import traceback
from PyQt5.QtGui import QIcon, QKeyEvent,QKeySequence,QCursor,QPixmap,QPen, QColor,QFont,QMouseEvent
from PyQt5.QtCore import Qt,QRectF, QPointF,QPoint,pyqtSignal
from PyQt5.QtWidgets import QMainWindow,QUndoStack,QComboBox,QMenu,QAction,QApplication, QWidget
from qgis._gui import QgsMapCanvas, QgsMapMouseEvent
from qgis.core import QgsMapLayer,QgsRectangle,QgsPoint,QgsCircle,QgsPointXY, QgsWkbTypes,QgsVectorLayer,\
    QgsVectorDataProvider,QgsFeature,QgsGeometry,QgsLineString,QgsRasterLayer,QgsProject,QgsMapSettings, \
    QgsDistanceArea,QgsWkbTypes,QgsFeatureRequest,QgsMultiPolygon,QgsMapToPixel,QgsMultiLineString,QgsCoordinateReferenceSystem, \
    QgsCoordinateTransform,Qgis,QgsJsonUtils,QgsFields,QgsSnappingConfig,Qgis,QgsTolerance
from qgis.gui import QgsMapCanvas, QgsMapMouseEvent,QgsProjectionSelectionDialog,QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker,QgsMapToolIdentify,QgsSnapIndicator,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapCanvasItem,QgsMapToolPan,QgsMapMouseEvent

from widgets.mapToolRectangleDialog import mapToolRectangleWindowClass
from widgets.mapToolInputAttrWindow import inputAttrWindowClass
from widgets.mapToolSingleAttrSelectWindow import selectSingleAttrWindowClass
from widgets.mapToolAttrSelectWindow import selectAttrWindowClass

from widgets.mapToolMeasureDistanceDialog import MeasureDistanceMapToolDialogClass
from widgets.mapToolMeasureAreaDialog import MeasureAreaMapToolDialogClass

from widgets.draw_dialog_webAttrEditDialog import WebAttrEditDialogClass,getAttrByDefault

from qfluentwidgets import MessageBox,RoundMenu, setTheme, Theme, Action, MenuAnimationType, MenuItemDelegate, CheckableMenu, MenuIndicatorType
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.yoyiSamRequest import rsdmWeber,samWeber
from yoyiUtils.plot_rectangle import plot_rectangle,update_orth
from yoyiUtils.yoyiTranslate import yoyiTrans

from shapely import affinity,wkt

import appConfig
import yoyirs_rc

PROJECT = QgsProject.instance()

snapTypeDict = {
    0 : QgsSnappingConfig.SnappingType.Vertex,
    1 : QgsSnappingConfig.SnappingType.Segment,
    2 : QgsSnappingConfig.SnappingType.VertexAndSegment,
}

class PolygonMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,layer,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(PolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

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

        self.recExtent = None

        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()
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
                self.p : QgsGeometry = self.polygon()

                if self.recExtent and not QgsGeometry.fromRect(self.recExtent).contains(self.p):
                    MessageBox('提示', "面矢量与图层范围不相交", self.parentWindow).exec_()
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
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""

        tempWkt = self.p.asWkt()

        if not self.parentWindow.isOpenAttrWindowSB.isChecked():
            remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                        self.parentWindow.remark1Type,
                                        self.parentWindow.remark2Type,
                                        self.parentWindow.remark3Type,
                                        self.parentWindow.remark1List,
                                        self.parentWindow.remark2List,
                                        self.parentWindow.remark3List,
                                        self.parentWindow.remark2String,
                                        self.parentWindow.remark3String
                                        )
            self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                remark1Content,remark2Content,remark3Content,fishnetId)
        else:
            dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                            remark1Type=self.parentWindow.remark1Type,
                                            remark1List=self.parentWindow.remark1List,
                                            remark1PreAttr=None,
                                            remark2String=self.parentWindow.remark2String,
                                            remark2Type=self.parentWindow.remark2Type,
                                            remark2List=self.parentWindow.remark2List,
                                            remark2PreAttr=None,
                                            remark3String=self.parentWindow.remark3String,
                                            remark3Type=self.parentWindow.remark3Type,
                                            remark3List=self.parentWindow.remark3List,
                                            remark3PreAttr=None,
                                            parent=self.parentWindow
                                            )
            dialog.exec()
            if dialog.remark1Attr is not None:
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
            dialog.deleteLater()
        self.reset()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.parentWindow.updateFeatureTable()

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
            print(traceback.format_exc())
            MessageBox('提示', "缓存过多，已自动清除", self.parentWindow).exec_()
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
        if resPolygon.type() == 2:
            return resPolygon
        else:
            print("error resPolygon.type():",resPolygon.type())
            return tempPolygon

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()

class RectangleMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,layer,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(RectangleMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(3)

        self.crossVertex = QgsVertexMarker(self.mapCanvas)
        self.crossVertex.setIconType(QgsVertexMarker.ICON_CROSS)
        self.crossVertex.setIconSize(2000)

        self.wkbType = "rectangle"
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        self.recExtent = None

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.distanceArea = QgsDistanceArea()
        self.distanceArea.setSourceCrs(self.editLayer.crs(),self.editLayer.transformContext())
        self.distanceArea.setEllipsoid("EPSG:7030")
        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()

        isHorizontal = appConfig.yoyiSetting().configSettingReader.value('horizontalRectangle',type=bool)
        self.drawType = 0 if isHorizontal else 1 # 0 水平矩形 1 旋转矩形

        self.reset()
    
    def reset(self):
        self.startPoint = self.startPointII = self.endPoint = None
        self.isEmittingPoint = False
        self.miniBoxGeo = None
        self.r : QgsGeometry = None
        self.rubberBand.reset()
        self.parentWindow.tempStatusLabel.setText("")
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)
    
    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))
    
    def changeDrawType(self,mode):
        self.drawType = mode
        if mode == 0:
            appConfig.yoyiSetting().changeSetting('horizontalRectangle', True)
        else:
            appConfig.yoyiSetting().changeSetting('horizontalRectangle', False)
        self.reset()

    # 右键窗口触发事件
    def on_custom_menu_requested(self):
        cusMenu = CheckableMenu(parent=self.parentWindow)
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
    
    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
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

        distance = self.distanceArea.measureLine(point1,point3)
        distanceFormat = self.distanceArea.formatDistance(distance,4,0,False)

        area = self.distanceArea.measureArea(self.rubberBand.asGeometry())
        areaFormat = self.distanceArea.formatArea(area,4,0,True)
        self.parentWindow.tempStatusLabel.setText(f"对角线距离：{distanceFormat}; 面积： {areaFormat}")
    
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
            try:
                fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            
            tempWkt = self.r.asWkt()

            if not self.parentWindow.isOpenAttrWindowSB.isChecked():
                remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                            self.parentWindow.remark1Type,
                                            self.parentWindow.remark2Type,
                                            self.parentWindow.remark3Type,
                                            self.parentWindow.remark1List,
                                            self.parentWindow.remark2List,
                                            self.parentWindow.remark3List,
                                            self.parentWindow.remark2String,
                                            self.parentWindow.remark3String
                                            )
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    remark1Content,remark2Content,remark3Content,fishnetId)
            else:
                dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                                remark1Type=self.parentWindow.remark1Type,
                                                remark1List=self.parentWindow.remark1List,
                                                remark1PreAttr=None,
                                                remark2String=self.parentWindow.remark2String,
                                                remark2Type=self.parentWindow.remark2Type,
                                                remark2List=self.parentWindow.remark2List,
                                                remark2PreAttr=None,
                                                remark3String=self.parentWindow.remark3String,
                                                remark3Type=self.parentWindow.remark3Type,
                                                remark3List=self.parentWindow.remark3List,
                                                remark3PreAttr=None,
                                                parent=self.parentWindow
                                                )
                dialog.exec()
                if dialog.remark1Attr is not None:
                    
                    self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                        dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
                dialog.deleteLater()
            self.reset()
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()

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
        super().deactivate()

class CircleMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,layer,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(CircleMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(3)

        self.wkbType = "rectangle"
        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.recExtent = None
        self.distanceArea = QgsDistanceArea()
        self.distanceArea.setSourceCrs(self.editLayer.crs(),self.editLayer.transformContext())
        self.distanceArea.setEllipsoid("EPSG:7030")
        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()

        self.reset()  
    
    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset()
        self.parentWindow.tempStatusLabel.setText("")
        #snap
        self.snapConfig.setEnabled(appConfig.yoyiSetting().configSettingReader.value('allowSnap',type=bool))
        self.snapConfig.setType( snapTypeDict[appConfig.yoyiSetting().configSettingReader.value('snapType',type=int)]  )
        self.snapConfig.setUnits(QgsTolerance.UnitType.Pixels)
        self.snapConfig.setTolerance( appConfig.yoyiSetting().configSettingReader.value('snapDistance',type=int) )
        self.snapConfig.setMode(Qgis.SnappingMode.AllLayers)
        self.snapper.setConfig(self.snapConfig)

    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))
    
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
        
        circle = QgsCircle(QgsPoint(startPoint.x(), startPoint.y()),A.distance(B))
        self.points = circle.points()

        distanceAB = self.distanceArea.measureLine(A,B)
        distanceFormat = self.distanceArea.formatDistance(distanceAB,4,0,False)
        areaFormat = self.distanceArea.formatArea(math.pi * distanceAB ** 2 ,4,0,True)
        self.parentWindow.tempStatusLabel.setText(f"半径：{distanceFormat}; 面积： {areaFormat}")

        for point in self.points[0:-1]:
            self.rubberBand.addPoint(QgsPointXY(point), False)
        self.rubberBand.addPoint(QgsPointXY(self.points[-1]), True)
        self.rubberBand.show()

    def addFeature(self):
        pointsXY = [[]]
        for point in self.points[0:-1]:
            pointsXY[0].append(QgsPointXY(point))
        tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
        if self.caps & QgsVectorDataProvider.AddFeatures:
            try:
                fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            tempWkt = tempGeo.asWkt()
            if not self.parentWindow.isOpenAttrWindowSB.isChecked():
                remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                            self.parentWindow.remark1Type,
                                            self.parentWindow.remark2Type,
                                            self.parentWindow.remark3Type,
                                            self.parentWindow.remark1List,
                                            self.parentWindow.remark2List,
                                            self.parentWindow.remark3List,
                                            self.parentWindow.remark2String,
                                            self.parentWindow.remark3String
                                            )
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    remark1Content,remark2Content,remark3Content,fishnetId)
            else:
                dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                                remark1Type=self.parentWindow.remark1Type,
                                                remark1List=self.parentWindow.remark1List,
                                                remark1PreAttr=None,
                                                remark2String=self.parentWindow.remark2String,
                                                remark2Type=self.parentWindow.remark2Type,
                                                remark2List=self.parentWindow.remark2List,
                                                remark2PreAttr=None,
                                                remark3String=self.parentWindow.remark3String,
                                                remark3Type=self.parentWindow.remark3Type,
                                                remark3List=self.parentWindow.remark3List,
                                                remark3PreAttr=None,
                                                parent=self.parentWindow
                                                )
                dialog.exec()
                if dialog.remark1Attr is not None:
                    self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                        dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
                dialog.deleteLater()
   
            self.reset()
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()
    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()

# 画点
class PointMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,layer,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(PointMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.editLayer: QgsVectorLayer = layer
        self.caps = self.editLayer.dataProvider().capabilities()

        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()
    
    def reset(self):
        pass

    def changeRubberBandColor(self,r,g,b):
        pass
    
    def canvasPressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.startPoint = self.toMapCoordinates(e.pos())
            self.addFeature()

    def addFeature(self):
        circle = QgsCircle(QgsPoint(self.startPoint.x(), self.startPoint.y()),0.00004)
        pointsXY =  [[]]
        for point in circle.points():
            pointsXY[0].append(QgsPointXY(point))
        tempGeo = QgsGeometry.fromPolygonXY(pointsXY)
        tempWkt = tempGeo.asWkt()
        if self.caps & QgsVectorDataProvider.AddFeatures:
            try:
                fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            
            if not self.parentWindow.isOpenAttrWindowSB.isChecked():
                remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                            self.parentWindow.remark1Type,
                                            self.parentWindow.remark2Type,
                                            self.parentWindow.remark3Type,
                                            self.parentWindow.remark1List,
                                            self.parentWindow.remark2List,
                                            self.parentWindow.remark3List,
                                            self.parentWindow.remark2String,
                                            self.parentWindow.remark3String
                                            )
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    remark1Content,remark2Content,remark3Content,fishnetId,isPoint=1)
            else:
                dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                                remark1Type=self.parentWindow.remark1Type,
                                                remark1List=self.parentWindow.remark1List,
                                                remark1PreAttr=None,
                                                remark2String=self.parentWindow.remark2String,
                                                remark2Type=self.parentWindow.remark2Type,
                                                remark2List=self.parentWindow.remark2List,
                                                remark2PreAttr=None,
                                                remark3String=self.parentWindow.remark3String,
                                                remark3Type=self.parentWindow.remark3Type,
                                                remark3List=self.parentWindow.remark3List,
                                                remark3PreAttr=None,
                                                parent=self.parentWindow
                                                )
                dialog.exec()
                if dialog.remark1Attr is not None:
                    self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                        dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId,isPoint=1)
                dialog.deleteLater()
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()

    def deactivate(self):
        super().deactivate()

# 错误点位勾画
class RejectPointMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self,canvas,parentWindow,taskId,userId,taskProjectType:appConfig.WebDrawQueryType,otherCanvas=None):
        super(RejectPointMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        if taskProjectType == appConfig.WebDrawQueryType.Draw:
            self.rejectType = appConfig.RejectPointDrawType.Review.value
        elif taskProjectType == appConfig.WebDrawQueryType.Review:
            self.rejectType = appConfig.RejectPointDrawType.Review.value
        elif taskProjectType == appConfig.WebDrawQueryType.Random:
            self.rejectType = appConfig.RejectPointDrawType.Random.value 

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setLineStyle(Qt.DashLine)
        self.rubberBand.setWidth(3)

        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()
        self.reset()
    
    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset()

    def changeRubberBandColor(self,r,g,b):
        pass

    def canvasPressEvent(self, e):
        tempPoint : QgsPoint = self.toMapCoordinates(e.pos())

        if e.button() == Qt.LeftButton:
            if e.modifiers() & Qt.ControlModifier:
                reason = appConfig.RejectPointReason.NeedAdd.value
            else:
                reason = appConfig.RejectPointReason.NeedDelete.value
            self.addFeature(tempPoint.x(),tempPoint.y(),reason)
        elif e.button() == Qt.MouseButton.RightButton and not self.isEmittingPoint:
            self.startPoint = tempPoint
            self.endPoint = self.startPoint
            self.isEmittingPoint = True
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        tempPoint: QgsPoint = self.toMapCoordinates(e.pos())
        if self.isEmittingPoint:
            self.endPoint = tempPoint
            self.showRect(self.startPoint, self.endPoint)
    
    def canvasReleaseEvent(self, e: QgsMapMouseEvent):
        if self.isEmittingPoint:
            res = self.rectangle()
            if type(res) == QgsRectangle:
                queryCode,queryRes = self.pgw.queryRejectPointsByExtent(res.xMinimum(),res.yMinimum(),res.xMaximum(),res.yMaximum(),self.taskId)
            else:
                queryCode = False
            
            if queryCode:
                beDeleteIds = []
                for feature in queryRes:
                    tempId = feature['properties']['id']
                    beDeleteIds.append(tempId)
                if len(beDeleteIds) > 0:
                    self.pgw.deleteRejectPoint(beDeleteIds)
            self.parentWindow.rejectPointLayer.triggerRepaint()
        self.reset()

    
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
            return None
        return QgsRectangle(self.startPoint, self.endPoint)

    def addFeature(self,x,y,reason):
        tempGeo = QgsGeometry().fromPointXY(QgsPointXY(x,y))

        tempWkt = tempGeo.asWkt()

        self.pgw.addRejectPoint(tempWkt,self.userId,self.taskId,reason,self.rejectType)
        self.parentWindow.rejectPointLayer.triggerRepaint()

# 旋转要素 mapTool
class RotatePolygonMapTool_Web(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,taskId,userId,otherCanvas=None):
        super(RotatePolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.editLayer:QgsVectorLayer = editLayer

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

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
        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()
        self.reset()
    
    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.remark1 = None
        self.remark2 = None
        self.remark3 = None
        self.featureTempCentroid = None #当前选中要素的质心
        self.featureTempGeo = None #当前选中要素的Geometry
        self.tempDegree = 0.0

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
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
                if queryCode and len(queryRes)>0:
                    self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                    tempDict = queryRes[0]
                    tempWkt = str(tempDict['geometry']).replace('\'','\"')
                    tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                    tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                    tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                    tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                    tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                    self.editLayer.addFeature(tempFeature)
                    self.editLayer.selectAll()
                    self.featureId = tempDict['properties']['id']
                    self.remark1 = tempDict['properties']['remark1']
                    self.remark2 = tempDict['properties']['remark2']
                    self.remark3 = tempDict['properties']['remark3']
                    self.featureTempGeo = tempFeature.geometry()
                    self.featureTempCentroid = self.featureTempGeo.centroid().asPoint()
            # 如果选中了要素, 那确定旋转
            else:
                try:
                    fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
                except Exception as e:
                    fishnetId = ""
                tempGeo = QgsGeometry(self.featureTempGeo)
                tempGeo.rotate(self.tempDegree,self.featureTempCentroid)
                self.pgw.updateFeature(self.featureId,tempGeo.asWkt(),self.userId,self.taskId,
                                       self.remark1,self.remark2,self.remark3,fishnetId)
                self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                self.reset()
                self.parentWindow.drawServerLayer.triggerRepaint()
                self.parentWindow.updateFeatureTable()
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
            self.reset()
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        if self.featureId is not None:
            tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
            snapMatch = self.snapper.snapToMap(e.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                tempPoint = snapMatch.point()
            self.tempDegree = self.featureTempCentroid.azimuth(tempPoint)
            tempGeo = QgsGeometry(self.featureTempGeo)
            tempGeo.rotate(self.tempDegree,self.featureTempCentroid)
            self.reshapeRubberBand(tempGeo)
    
    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()

# 缩放要素 mapTool
class RescalePolygonMapTool_Web(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,taskId,userId,otherCanvas=None):
        super(RescalePolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.editLayer:QgsVectorLayer = editLayer

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setLineStyle(2) # Qt::PenStyle 1实线 2虚线 3点线
        self.rubberBand.setColor(QColor(255, 0, 0, 100))

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()
        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素
        self.remark1 = None
        self.remark2 = None
        self.remark3 = None
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
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
                if queryCode and len(queryRes)>0:
                    self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                    tempDict = queryRes[0]
                    tempWkt = str(tempDict['geometry']).replace('\'','\"')
                    tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                    tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                    tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                    tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                    tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                    self.editLayer.addFeature(tempFeature)
                    self.editLayer.selectAll()
                    self.featureId = tempDict['properties']['id']
                    self.remark1 = tempDict['properties']['remark1']
                    self.remark2 = tempDict['properties']['remark2']
                    self.remark3 = tempDict['properties']['remark3']
                    self.featureTempGeo = tempFeature.geometry()
                    self.featureTempCentroid = self.featureTempGeo.centroid().asPoint()
                    tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
                    self.factorDistance = tempPoint.distance(self.featureTempCentroid)
                    if self.factorDistance < 0.00001:
                        self.factorDistance = 0.00001
            # 如果选中了要素, 那确定缩放
            else:
                try:
                    fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
                except Exception as e:
                    fishnetId = ""
                shapelyPolygon = wkt.loads(self.featureTempGeo.asWkt())
                newPolygon = affinity.scale(shapelyPolygon,self.tempFactorScale,self.tempFactorScale)
                self.pgw.updateFeature(self.featureId,newPolygon.wkt,self.userId,self.taskId,
                                       self.remark1,self.remark2,self.remark3,fishnetId)
                self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                self.reset()
                self.parentWindow.drawServerLayer.triggerRepaint()
                self.parentWindow.updateFeatureTable()
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
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

# 轨迹化面 mapTool
class Line2PolygonMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(Line2PolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0))
        self.rubberBand.setWidth(3)

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.recExtent = None

        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()
        self.reset()
    
    def reset(self):
        self.is_start = False #开始绘图
        self.is_end = False #结束绘图  开始进行轨迹生面的预览
        self.cursor_point = None  #当前鼠标的轨迹点
        self.cursor_pos = None

        self.autoLong = -1 # 1 0 是缓冲区  -1 是真死了
        self.autoLongLastIndex = -1

        self.points = []
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
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
    
    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Backspace:
            if self.is_end:
                self.reset()
                return
            if self.autoLong >= 0 and self.autoLongLastIndex >= 0 and len(self.points)>=1:
                self.points = self.points[:self.autoLongLastIndex]
                self.show_line()
                self.autoLong = -1
            elif self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                self.show_line()
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
            if self.is_end:
                return
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
            if not self.is_start:
                self.reset()
            if len(self.points) < 2:
                self.reset()
            if not self.is_end:
                self.is_end = True
            else:
                self.addFeature()
    
    def addFeature(self):
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        
        lastPoint : QgsPointXY = self.points[-1]
        print(lastPoint.distance(self.cursor_point))
        if lastPoint.distance(self.cursor_point) <= 0.000001:
            MessageBox('提示', "距离过小，请重画", self.parentWindow).exec_()
            return
        tempLineGeo = QgsGeometry.fromPolylineXY(self.points)
        tempLineGeo.translate(self.cursor_point.x()-lastPoint.x(),self.cursor_point.y()-lastPoint.y())
        newPoints = [QgsPointXY(point) for point in tempLineGeo.constGet()] 
        newPoints.reverse()
        points = self.points + newPoints
        tempPolygon : QgsGeometry = QgsGeometry.fromMultiPolygonXY([[points]])
        resPolygon = tempPolygon.makeValid()
        tempWkt = resPolygon.asWkt()

        if not self.parentWindow.isOpenAttrWindowSB.isChecked():
            remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                        self.parentWindow.remark1Type,
                                        self.parentWindow.remark2Type,
                                        self.parentWindow.remark3Type,
                                        self.parentWindow.remark1List,
                                        self.parentWindow.remark2List,
                                        self.parentWindow.remark3List,
                                        self.parentWindow.remark2String,
                                        self.parentWindow.remark3String
                                        )
            self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                remark1Content,remark2Content,remark3Content,fishnetId)
        else:
            dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                            remark1Type=self.parentWindow.remark1Type,
                                            remark1List=self.parentWindow.remark1List,
                                            remark1PreAttr=None,
                                            remark2String=self.parentWindow.remark2String,
                                            remark2Type=self.parentWindow.remark2Type,
                                            remark2List=self.parentWindow.remark2List,
                                            remark2PreAttr=None,
                                            remark3String=self.parentWindow.remark3String,
                                            remark3Type=self.parentWindow.remark3Type,
                                            remark3List=self.parentWindow.remark3List,
                                            remark3PreAttr=None,
                                            parent=self.parentWindow
                                            )
            dialog.exec()
            if dialog.remark1Attr is not None:
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
            dialog.deleteLater()
        self.reset()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.parentWindow.updateFeatureTable()

    def canvasMoveEvent(self, event):
        try:
            self.cursor_pos = event.pos()
            self.cursor_point = event.mapPoint()
            snapMatch = self.snapper.snapToMap(event.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                self.cursor_point = snapMatch.point()
                self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
            
            if self.is_end:
                self.show_two_line()
            else:
                if self.autoLong == 1:
                    self.addPoint(self.cursor_point,streamCheck=True)
                if not self.is_start:
                    return
                self.show_line()
        except Exception as e:
            print(e)
            MessageBox('提示', "缓存过多，已自动清除", self.parentWindow).exec_()
            self.reset()
    
    def show_line(self):
        if self.points and len(self.points)>=1:
            self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
            for point in self.points:
                self.rubberBand.addPoint(point, False)
            self.rubberBand.addPoint(self.cursor_point, True)
            self.rubberBand.show()
        else:
            self.reset()
    
    def show_two_line(self):
        lastPoint = self.points[-1]

        oldTempGeo = QgsGeometry.fromPolylineXY(self.points)

        tempGeo = QgsGeometry(oldTempGeo)
        tempGeo.translate(self.cursor_point.x()-lastPoint.x(),self.cursor_point.y()-lastPoint.y())
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)

        self.rubberBand.addGeometry(oldTempGeo,crs=self.mapCanvasCrs,doUpdate=False)
        self.rubberBand.addGeometry(tempGeo,crs=self.mapCanvasCrs,doUpdate=True)
        self.rubberBand.show()
    
    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate() 

# 线buffer化面 mapTool
class LineBuffer2PolygonMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas:QgsMapCanvas,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None):
        super(LineBuffer2PolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas 
        self.mapCanvasCrs = self.mapCanvas.mapSettings().destinationCrs()
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.LineGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0,50))
        self.rubberBand.setWidth(3)

        self.recExtent = None

        self.otherCanvas = otherCanvas
        self.fieldValueDict = fieldValueDict
        self.pgw = rsdmWeber()
        self.reset()
    
    def reset(self):
        self.is_start = False #开始绘图
        self.is_end = False #结束绘图  开始进行轨迹生面的预览
        self.cursor_point = None  #当前鼠标的轨迹点

        self.autoLong = -1 # 1 0 是缓冲区  -1 是真死了
        self.autoLongLastIndex = -1

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

        self.points = []
        self.tempGeo = None
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
    
    def changeRubberBandColor(self,r,g,b):
        self.rubberBand.setColor(QColor(r,g,b,50))
    
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
    
    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Backspace:
            if self.is_end:
                self.reset()
                return
            if self.autoLong >= 0 and self.autoLongLastIndex >= 0 and len(self.points)>=1:
                self.points = self.points[:self.autoLongLastIndex]
                self.show_line()
                self.autoLong = -1
            elif self.points and len(self.points)>=1:
                self.points = self.points[:-1]
                self.show_line()
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
            if self.is_end:
                return
            
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
            if not self.is_start:
                self.reset()
            if len(self.points) < 2:
                self.reset()
            if not self.is_end:
                self.is_end = True
            else:
                self.addFeature()
    
    def addFeature(self):
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        
        resPolygon = self.tempGeo.makeValid()
        tempWkt = resPolygon.asWkt()

        if not self.parentWindow.isOpenAttrWindowSB.isChecked():
            remark1Content,remark2Content,remark3Content = getAttrByDefault(None,None,None,
                                        self.parentWindow.remark1Type,
                                        self.parentWindow.remark2Type,
                                        self.parentWindow.remark3Type,
                                        self.parentWindow.remark1List,
                                        self.parentWindow.remark2List,
                                        self.parentWindow.remark3List,
                                        self.parentWindow.remark2String,
                                        self.parentWindow.remark3String
                                        )
            self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                remark1Content,remark2Content,remark3Content,fishnetId)
        else:
            dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                            remark1Type=self.parentWindow.remark1Type,
                                            remark1List=self.parentWindow.remark1List,
                                            remark1PreAttr=None,
                                            remark2String=self.parentWindow.remark2String,
                                            remark2Type=self.parentWindow.remark2Type,
                                            remark2List=self.parentWindow.remark2List,
                                            remark2PreAttr=None,
                                            remark3String=self.parentWindow.remark3String,
                                            remark3Type=self.parentWindow.remark3Type,
                                            remark3List=self.parentWindow.remark3List,
                                            remark3PreAttr=None,
                                            parent=self.parentWindow
                                            )
            dialog.exec()
            if dialog.remark1Attr is not None:
                self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                    dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
            dialog.deleteLater()
        self.reset()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.parentWindow.updateFeatureTable()

    def canvasMoveEvent(self, event):
        try:
            self.cursor_pos = event.pos()
            self.cursor_point = event.mapPoint()
            snapMatch = self.snapper.snapToMap(event.pos())
            self.snapIndicator.setMatch(snapMatch)
            if snapMatch.isValid():
                self.cursor_point = snapMatch.point()
                self.cursor_pos = QPoint(self.mapCanvasTransform.transform(self.cursor_point)[0],self.mapCanvasTransform.transform(self.cursor_point)[1])
            
            if self.is_end:
                self.showBufferPoly()
            else:
                if self.autoLong == 1:
                    self.addPoint(self.cursor_point,streamCheck=True)
                if not self.is_start:
                    return
                self.show_line()
        except Exception as e:
            print(e)
            MessageBox('提示', "缓存过多，已自动清除", self.parentWindow).exec_()
            self.reset()
    
    def show_line(self):
        if self.points and len(self.points)>=1:
            self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
            for point in self.points:
                self.rubberBand.addPoint(point, False)
            self.rubberBand.addPoint(self.cursor_point, True)
            self.rubberBand.show()
        else:
            self.reset()
    
    def showBufferPoly(self):
        lastPoint = self.points[-1]
        distance = self.cursor_point.distance(lastPoint)

        oldTempGeo = QgsGeometry.fromPolylineXY(self.points)
        self.tempGeo = oldTempGeo.buffer(distance,segments=20,
                                         endCapStyle=Qgis.EndCapStyle.Flat,
                                         joinStyle=Qgis.JoinStyle.Miter,
                                         miterLimit=2.0)
        self.rubberBand.reset(QgsWkbTypes.GeometryType.PolygonGeometry)
        self.rubberBand.addGeometry(self.tempGeo,crs=self.mapCanvasCrs,doUpdate=True)
        self.rubberBand.show()
        
    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate() 


# 裁剪要素 mapTool
class SplitPolygonMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas,editLayer,parentWindow,taskId,userId,otherCanvas=None):
        super(SplitPolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        self.editLayer : QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setColor(QColor(255, 0, 0, 100))
        self.rubberBand.setLineStyle(1)
        self.rubberBand.setWidth(3)

        self.rubberBand2 = QgsRubberBand(self.mapCanvas)
        self.rubberBand2.setColor(QColor(255, 0, 0, 100))
        self.rubberBand2.setLineStyle(3)
        self.rubberBand2.setWidth(3)

        # snap 为地图工具增加 snap功能， 在指定的tolerance中会捕捉到顶点
        self.snapIndicator = QgsSnapIndicator(self.mapCanvas)
        self.snapper = self.mapCanvas.snappingUtils()
        self.snapConfig = QgsSnappingConfig()
        self.snapConfig.setEnabled(False)
        self.snapper.setConfig(self.snapConfig)

        self.otherCanvas = otherCanvas
        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.pgw = rsdmWeber()
        self.reset()
        self.tempLine : QgsGeometry = None

    def reset(self):
        self.points = []
        self.is_start = False  # 开始绘图
        self.cursor_point = None
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
            self.rubberBand2.addPoint(self.points[0],False)
            self.rubberBand2.addPoint(self.cursor_point,True)
            self.rubberBand2.show()

    # 根据point数组创建线
    def createTempPolyLine(self):
        if len(self.points) < 2:
            return None
        res = QgsLineString()
        points = []
        for point in self.points:
            points.append(QgsPoint(point.x(),point.y()))
        res.setPoints(points)
        return res

    # 判断能不能裁剪 能的话就进行裁剪
    def splitPolygonByTempLine(self):
        
        tempRec = self.tempLine.boundingBox()
        queryCode,queryRes = self.pgw.queryFeaturesByExtent(tempRec.xMinimum(),tempRec.yMinimum(),tempRec.xMaximum(),tempRec.yMaximum(),self.taskId)

        if queryCode:
            for tempDict in queryRes:
                tempWkt = str(tempDict['geometry']).replace('\'','\"')
                feature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                featureId = tempDict['properties']['id']
                remark1 = tempDict['properties']['remark1']
                remark2 = tempDict['properties']['remark2']
                remark3 = tempDict['properties']['remark3']
                featureGemtry : QgsGeometry = feature.geometry()
                #featureId = feature.attribute('FeatureId')
                if featureGemtry:
                    try:
                        fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
                    except Exception as e:
                        fishnetId = ""
                    if featureGemtry.wkbType() == 6:  # multipolygon 6
                        geometry = QgsGeometry.fromMultiPolygonXY(feature.geometry().asMultiPolygon())
                    else:  # polygon 3
                        geometry = QgsGeometry.fromMultiPolygonXY([feature.geometry().asPolygon()])

                    t,geos,_ = geometry.splitGeometry(self.points,True,False)
                    #t = geometry.reshapeGeometry(self.tempLine)
                    if t == 0:
                        # 1 删除原来要素
                        self.pgw.deleteFeature([featureId])
                        for tempGeo in geos:
                            # 增加裁剪后的要素
                            self.pgw.addFeature(tempGeo.asWkt(),self.userId,self.taskId,
                                                remark1,remark2,remark3,fishnetId)
                    elif len(self.points) > 2:
                        points = [point for point in self.points]
                        points.append(self.points[0])
                        t2 = geometry.addRing(points)
                        if t2 == 0:
                            # 1 修改原来要素
                            self.pgw.updateFeature(featureId,geometry.asWkt(),self.userId,self.taskId,
                                                   remark1,remark2,remark3,fishnetId)
                            # 2 增加环
                            pointList = []
                            for point in self.points:
                                pointList.append(QgsPointXY(point[0],point[1]))
                            tempPolygon : QgsGeometry = QgsGeometry.fromMultiPolygonXY([[pointList]])
                            resPolygon = tempPolygon.makeValid()
                            if resPolygon.type() == 2:
                                self.pgw.addFeature(resPolygon.asWkt(),self.userId,self.taskId,
                                                    remark1,remark2,remark3,fishnetId)
        # self.mapCanvas.refresh()
        # if self.otherCanvas:
        #     self.otherCanvas.refresh()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.reset()
        self.parentWindow.updateFeatureTable()

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()

# 重塑要素 mapTool
class ReShapePolygonMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self, canvas,editLayer, parentWindow,taskId,userId,otherCanvas=None):
        super(ReShapePolygonMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas
        self.mapCanvasTransform = self.mapCanvas.getCoordinateTransform()
        # qgisFeature 待裁剪的feature
        self.editLayer : QgsVectorLayer = editLayer
        
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

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
        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.pgw = rsdmWeber()
        self.reset()
        self.tempLine : QgsGeometry = None

    def reset(self):
        self.points = []
        self.is_start = False  # 开始绘图
        self.cursor_point = None
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

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.RightButton:
            # 右键结束
            #self.points.append(self.cursor_point)
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
        tempRec = self.tempLine.boundingBox()
        queryCode,queryRes = self.pgw.queryFeaturesByExtent(tempRec.xMinimum(),tempRec.yMinimum(),tempRec.xMaximum(),tempRec.yMaximum(),self.taskId)
        if queryCode:
            for tempDict in queryRes:
                tempWkt = str(tempDict['geometry']).replace('\'','\"')
                feature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                featureId = tempDict['properties']['id']
                remark1 = tempDict['properties']['remark1']
                remark2 = tempDict['properties']['remark2']
                remark3 = tempDict['properties']['remark3']
                featureGemtry : QgsGeometry = feature.geometry()
                print("featureId ",featureId)
                if featureGemtry:
                    try:
                        fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
                    except Exception as e:
                        fishnetId = ""
                    if featureGemtry.wkbType() == 6: # multipolygon 6
                        geometry = QgsGeometry.fromMultiPolygonXY(featureGemtry.asMultiPolygon())
                    else: # polygon 3
                        geometry = QgsGeometry.fromMultiPolygonXY([featureGemtry.asPolygon()])

                    t = geometry.reshapeGeometry(QgsLineString.fromQPolygonF(self.tempLine.asQPolygonF()))
                    print('reshape result:',t)
                    if t == 0:
                        # 1 修改原来要素
                        self.pgw.updateFeature(featureId,geometry.asWkt(),self.userId,self.taskId,
                                               remark1,remark2,remark3,fishnetId)
                    elif len(self.points) > 2:
                        points = [point for point in self.points]
                        points.append(self.points[0])
                        t2 = geometry.addRing(points)
                        print("addRing状态",t2)
                        if t2 == 0:
                            # 2 添加环
                            self.pgw.updateFeature(featureId,geometry.asWkt(),self.userId,self.taskId,
                                                   remark1,remark2,remark3,fishnetId)
        # self.mapCanvas.refresh()
        # if self.otherCanvas:
        #     self.otherCanvas.refresh()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.reset()
        self.parentWindow.updateFeatureTable()

    def deactivate(self):
        self.reset()
        self.snapIndicator.setVisible(False)
        super().deactivate()

# 编辑顶点 mapTool
class EditVertexMapTool_Web(QgsMapToolEmitPoint):
    def __init__(self,canvas,editLayer,parentWindow,taskId,userId,otherCanvas=None,useBbox=False):
        super(EditVertexMapTool_Web, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.editLayer:QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

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

        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()
        self.useBbox = useBbox
        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.featureId = None # 是不是已经开始选中要素
        self.remark1 = None
        self.remark2 = None
        self.remark3 = None
        self.drawLayerFeatureId = None #临时编辑图层的临时ID
        self.featureGeometry = None #存储要素的形状
        self.isEmittingPoint = False #是不是已经开始编辑顶点
        self.changeId = None
        self.isInsert = False
        self.farthestPoint: QgsPointXY = None
        

    # 重新渲染Rubber Band
    def reshapeRubberBand(self,points):
        self.rubberBand.reset()
        for point in points:
            self.rubberBand.addPoint(point)

    def canvasDoubleClickEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if self.featureId:
            queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
            if queryCode and len(queryRes)==0:
                self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                self.reset()
                self.pointVertex.hide()
                self.lineVertex.hide()

    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        if self.featureId is not None:
            # 如果还没开始
            if not self.isEmittingPoint:
                if e.button() == Qt.LeftButton:
                    nearestPoint,self.changeId,self.beforeVertexId,self.afterVertexId,_ = self.featureGeometry.closestVertex(tempPoint)
                    self.isEmittingPoint = True
                    if self.useBbox:
                        maxDis = 0
                        for pointS in self.featureGeometry.vertices():
                            pointSXY = QgsPointXY(pointS.x(), pointS.y())
                            tempDistance = nearestPoint.distance(pointSXY)
                            if tempDistance > maxDis:
                                maxDis = tempDistance
                                self.farthestPoint = pointSXY
                elif e.button() == Qt.RightButton:
                    squaredCartesian,minDistPoint,self.afterVertexId,leftOf = self.featureGeometry.closestSegmentWithContext(tempPoint,0.000000000001)
                    self.beforeVertexId = self.afterVertexId -1
                    self.isEmittingPoint = True
                    self.isInsert = True
            else:
                try:
                    fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
                except Exception as e:
                    fishnetId = ""
                if self.isInsert:
                    self.featureGeometry.insertVertex(tempPoint.x(),tempPoint.y(),self.afterVertexId)
                    if self.useBbox:
                        tempGeo = QgsGeometry.fromRect(self.featureGeometry.boundingBox())
                        self.pgw.updateFeature(self.featureId,tempGeo.asWkt(),self.userId,self.taskId,
                                               self.remark1,self.remark2,self.remark3,fishnetId)
                        self.editLayer.changeGeometry(self.drawLayerFeatureId,tempGeo)
                        self.featureGeometry = tempGeo
                    else:
                        self.pgw.updateFeature(self.featureId,self.featureGeometry.asWkt(),self.userId,self.taskId,
                                               self.remark1,self.remark2,self.remark3,fishnetId)
                        self.editLayer.changeGeometry(self.drawLayerFeatureId, self.featureGeometry)
                else:
                    self.featureGeometry.moveVertex(tempPoint.x(),tempPoint.y(),self.changeId)
                    if self.useBbox:
                        tempGeo = QgsGeometry.fromRect(QgsRectangle(self.farthestPoint,tempPoint))
                        self.pgw.updateFeature(self.featureId,tempGeo.asWkt(),self.userId,self.taskId,
                                               self.remark1,self.remark2,self.remark3,fishnetId)
                        self.editLayer.changeGeometry(self.drawLayerFeatureId,tempGeo)
                        self.featureGeometry = tempGeo
                    else:
                        self.pgw.updateFeature(self.featureId,self.featureGeometry.asWkt(),self.userId,self.taskId,
                                               self.remark1,self.remark2,self.remark3,fishnetId)
                        self.editLayer.changeGeometry(self.drawLayerFeatureId, self.featureGeometry)

                self.rubberBand.reset()
                # self.mapCanvas.refresh()
                # if self.otherCanvas:
                #     self.otherCanvas.refresh()
                self.parentWindow.drawServerLayer.triggerRepaint()
                self.parentWindow.updateFeatureTable()
                self.isInsert = False
                self.isEmittingPoint = False
        else:
            queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
            if queryCode and len(queryRes)>0:
                self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                tempDict = queryRes[0]
                tempWkt = str(tempDict['geometry']).replace('\'','\"')
                tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                self.editLayer.addFeature(tempFeature)
                self.editLayer.selectAll()

                self.featureId = tempDict['properties']['id']
                self.remark1 = tempDict['properties']['remark1']
                self.remark2 = tempDict['properties']['remark2']
                self.remark3 = tempDict['properties']['remark3']
                self.drawLayerFeatureId = tempFeature.id()
                self.featureGeometry = tempFeature.geometry()

                self.pointVertex.show()
                self.lineVertex.show()

    def canvasMoveEvent(self, e):
        if self.featureId is not None:
            tempPoint : QgsPointXY = self.toMapCoordinates(e.pos())
            if self.isEmittingPoint:
                if self.isInsert:
                    pointBefore = self.featureGeometry.vertexAt(self.beforeVertexId)
                    pointAfter = self.featureGeometry.vertexAt(self.afterVertexId)
                    self.reshapeRubberBand([QgsPointXY(pointBefore.x(),pointBefore.y()),tempPoint,QgsPointXY(pointAfter.x(),pointAfter.y())])
                else:
                    pointBefore = self.featureGeometry.vertexAt(self.beforeVertexId)
                    pointAfter = self.featureGeometry.vertexAt(self.afterVertexId)
                    self.reshapeRubberBand([QgsPointXY(pointBefore.x(),pointBefore.y()),tempPoint,QgsPointXY(pointAfter.x(),pointAfter.y())])
            else:
                nearestPoint,vertexId,beforeVertexId,afterVertexId,_ = self.featureGeometry.closestVertex(tempPoint)
                squaredCartesian,minDistPoint,lineVertexId1,leftOf = self.featureGeometry.closestSegmentWithContext(tempPoint,0.000000000001)
                x = (self.featureGeometry.vertexAt(lineVertexId1).x() + self.featureGeometry.vertexAt(lineVertexId1-1).x()) / 2
                y = (self.featureGeometry.vertexAt(lineVertexId1).y() + self.featureGeometry.vertexAt(lineVertexId1-1).y()) / 2
                self.pointVertex.setCenter(nearestPoint)
                self.lineVertex.setCenter(QgsPointXY(x,y))

    def deactivate(self):
        self.reset()
        try:
            self.mapCanvas.scene().removeItem(self.pointVertex)
            self.mapCanvas.scene().removeItem(self.lineVertex)
        except:
            pass
        super().deactivate()

# 粘贴要素 mapTool
class PastePolygonMapToo_Web(QgsMapToolIdentify):
    def __init__(self, canvas, editLayer, parentWindow,taskId,userId,otherCanvas=None):
        super(PastePolygonMapToo_Web, self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.editLayer: QgsVectorLayer = editLayer

        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas)
        self.rubberBand.setLineStyle(2)
        self.rubberBand.setColor(QColor(255, 200, 0, 100))
        self.rubberBand.setWidth(3)

        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()
        self.reset()

    def reset(self):
        self.rubberBand.reset()
        self.featureId = None #是不是已经开始选中要素,这个存的是假的id，临时id
        self.remark1 = None
        self.remark2 = None
        self.remark3 = None
        self.tempMoveCenter = None #当前选中要素的质心

    # 重新渲染Rubber Band
    def reshapeRubberBand(self,tempGeo:QgsGeometry):
        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
        self.rubberBand.addGeometry(tempGeo)

    def showMoveShape(self,tempPoint,trueChange=False):
        feature : QgsFeature = self.editLayer.getFeature(self.featureId)
        newGeometry = feature.geometry()
        newGeometry.translate(tempPoint.x() - self.tempMoveCenter.x(), tempPoint.y() - self.tempMoveCenter.y())
        if trueChange:
            try:
                fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            self.pgw.addFeature(newGeometry.asWkt(),self.userId,self.taskId,
                                self.remark1,self.remark2,self.remark3,fishnetId)
            # self.mapCanvas.refresh()
            # if self.otherCanvas:
            #     self.otherCanvas.refresh()
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()
        else:
            self.reshapeRubberBand(newGeometry)
    
    def canvasPressEvent(self, e: QgsMapMouseEvent):
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton:
            # 如果啥也没选中 那选一下要素
            if self.featureId is None:
                queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
                if queryCode and len(queryRes)>0:
                    self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                    tempDict = queryRes[0]
                    tempWkt = str(tempDict['geometry']).replace('\'','\"')
                    tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                    tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                    tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                    tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                    tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                    self.editLayer.addFeature(tempFeature)
                    self.editLayer.selectAll()

                    self.featureId = tempFeature.id()
                    self.remark1 = tempDict['properties']['remark1']
                    self.remark2 = tempDict['properties']['remark2']
                    self.remark3 = tempDict['properties']['remark3']
                    featureTempGeo = tempFeature.geometry()
                    self.tempMoveCenter = featureTempGeo.centroid().asPoint()
            # 如果选中了要素, 那确定复制
            else:
                self.showMoveShape(tempPoint, True)
        elif e.button() == Qt.MouseButton.RightButton:
            self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
            self.reset() 

    def canvasMoveEvent(self, e):
        if self.featureId is not None:
            tempPoint = self.toMapCoordinates(e.pos())
            self.showMoveShape(tempPoint)

    def deactivate(self):
        self.reset()
        super().deactivate()

# 删除环 -- mapTool
class FillHoleMapTool_Web(QgsMapToolIdentify):
    def __init__(self, canvas, drawLayer,parentWindow,taskId,userId,otherCanvas=None):
        super(FillHoleMapTool_Web, self).__init__(canvas)
        self.mapCanvas = canvas
        self.editLayer: QgsVectorLayer = drawLayer
        
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId
        
        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()

    def canvasPressEvent(self, e):
        tempPoint = self.toMapCoordinates(e.pos())
        queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
        if queryCode and len(queryRes)>0:
            tempDict = queryRes[0]
            tempWkt = str(tempDict['geometry']).replace('\'','\"')
            tempFeatureId = tempDict['properties']['id']
            remark1 = tempDict['properties']['remark1']
            remark2 = tempDict['properties']['remark2']
            remark3 = tempDict['properties']['remark3']
            tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
            tempGeo = tempFeature.geometry().removeInteriorRings()

            try:
                fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            self.pgw.updateFeature(tempFeatureId,tempGeo.asWkt(),self.userId,self.taskId,
                                   remark1,remark2,remark3,fishnetId)
            
            # self.mapCanvas.refresh()
            # if self.otherCanvas:
            #     self.otherCanvas.refresh()
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()

    def deactivate(self):
        super().deactivate()

# 选择要素
class SelectFeatureMapTool_Web(QgsMapToolIdentify):
    def __init__(self,canvas,editLayer,parentWindow,taskId,userId,otherCanvas=None):
        super(SelectFeatureMapTool_Web,self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.editLayer: QgsVectorLayer = editLayer
        self.parentWindow = parentWindow
        self.taskId = taskId
        self.userId = userId

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setLineStyle(Qt.DashLine)
        self.rubberBand.setWidth(3)
        self.mode = QgsMapToolIdentify.TopDownAll
        self.otherCanvas: QgsMapCanvas = otherCanvas 
        self.pgw = rsdmWeber()
        self.reset()
    
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
        tempSelectedIds = self.editLayer.selectedFeatureIds()
        if tempSelectedIds:
            beDeleteIds = []
            for id in tempSelectedIds:
                tempFeature = self.editLayer.getFeature(id)
                beDeleteIds.append(tempFeature.attribute('FeatureId'))
            self.pgw.deleteFeature(beDeleteIds)
        self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.parentWindow.updateFeatureTable()
    
    def simplifySelectedTriggered(self):
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        tempSelectedIds = self.editLayer.selectedFeatureIds()
        if tempSelectedIds:
            for id in tempSelectedIds:
                tempFeature = self.editLayer.getFeature(id)
                tempFeatureId = tempFeature.attribute('FeatureId')
                remark1 = tempFeature.attribute('remark1')
                remark2 = tempFeature.attribute('remark2')
                remark3 = tempFeature.attribute('remark3')
                tempGeo : QgsGeometry = tempFeature.geometry()
                newGeo : QgsGeometry = tempGeo.simplify(0.00001)
                if newGeo.isGeosValid():
                    self.editLayer.changeGeometry(id,newGeo)
                    self.pgw.updateFeature(tempFeatureId,newGeo.asWkt(),self.userId,self.taskId,
                                           remark1,remark2,remark3,fishnetId)
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()
    
    def splitPartTriggered(self):
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        tempSelectedIds = self.editLayer.selectedFeatureIds()
        if tempSelectedIds:
            for id in tempSelectedIds:
                tempFeature = self.editLayer.getFeature(id)
                tempFeatureId = tempFeature.attribute('FeatureId')
                remark1 = tempFeature.attribute('remark1')
                remark2 = tempFeature.attribute('remark2')
                remark3 = tempFeature.attribute('remark3')
                tempGeo : QgsGeometry = tempFeature.geometry()
                partList = []
                for part in tempGeo.parts():
                    partList.append(part)
                if len(partList) > 1:
                    self.pgw.deleteFeature([tempFeatureId])
                    for part in partList:
                        self.pgw.addFeature(part.asWkt(),self.userId,self.taskId,
                                            remark1,remark2,remark3,fishnetId)
            self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()
    
    def fillHoleTriggered(self):
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        tempSelectedIds = self.editLayer.selectedFeatureIds()
        if tempSelectedIds:
            for id in tempSelectedIds:
                tempFeature = self.editLayer.getFeature(id)
                tempFeatureId = tempFeature.attribute('FeatureId')
                remark1 = tempFeature.attribute('remark1')
                remark2 = tempFeature.attribute('remark2')
                remark3 = tempFeature.attribute('remark3')
                tempGeo : QgsGeometry = tempFeature.geometry()
                newGeo : QgsGeometry = tempGeo.removeInteriorRings()
                if newGeo.isGeosValid():
                    self.editLayer.changeGeometry(id,newGeo)
                    self.pgw.updateFeature(tempFeatureId,newGeo.asWkt(),self.userId,self.taskId,
                                           remark1,remark2,remark3,fishnetId)
            self.parentWindow.drawServerLayer.triggerRepaint()
            self.parentWindow.updateFeatureTable()
    
    # 右键窗口触发事件
    def on_custom_menu_requested(self):
        cusMenu = RoundMenu(parent=self.parentWindow)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(QIcon(":/img/resources/gis/shp_delete_select.png"), '删除所选要素')
        deleteSelected.triggered.connect(self.deleteSelectedTriggered)
        cusMenu.addAction(deleteSelected)

        simplifySelected = Action(QIcon(":/img/resources/shpProcess/shp_simply.png"), '简化所选要素')
        simplifySelected.triggered.connect(self.simplifySelectedTriggered)
        cusMenu.addAction(simplifySelected)

        splitParts = Action(QIcon(":/img/resources/shpProcess/shp_split.png"), '拆分所选要素组件')
        splitParts.triggered.connect(self.splitPartTriggered)
        cusMenu.addAction(splitParts)

        fillHole = Action(QIcon(":/img/resources/shpProcess/shp_removeHole.png"),'去除空洞')
        fillHole.triggered.connect(self.fillHoleTriggered)
        cusMenu.addAction(fillHole)

        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    # 判断当前鼠标是否碰到了选择的要素
    def isIntersectSelectedIds(self,e):
        if self.tempSelectedIds:
            resList: list = self.identify(e.x(), e.y(), layerList=[self.editLayer], mode=self.mode)
            ids = [i.mFeature.id() for i in resList]
            if ids and ids[0] in self.tempSelectedIds:
                #print(ids[0],self.tempSelectedIds)
                return True,ids[0]
        return False,-1

    
    def canvasPressEvent(self, e: QgsMapMouseEvent):
        tempPoint : QgsPoint = self.toMapCoordinates(e.pos())
        
        if e.button() == Qt.MouseButton.LeftButton and not self.isEmittingPoint:
            isInter,ids0 = self.isIntersectSelectedIds(e)
            if isInter:
                if e.modifiers() & Qt.ControlModifier:
                    self.editLayer.deleteFeature(ids0)
                    self.tempSelectedIds = self.editLayer.selectedFeatureIds()
                    self.mapToolMode = 2
                elif self.allowMoveFeature:
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
                self.mapToolMode = 0
                self.startPoint = tempPoint
                self.endPoint = self.startPoint
                self.isEmittingPoint = True
                self.mapCanvas.setCursor(Qt.ArrowCursor)
        elif e.button() == Qt.MouseButton.RightButton:
            self.on_custom_menu_requested()
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent):
        tempPos = e.pos()
        tempPoint: QgsPoint = self.toMapCoordinates(tempPos)

        if self.mapToolMode == 0 and self.isEmittingPoint:
            self.endPoint = tempPoint
            self.showRect(self.startPoint, self.endPoint)
        elif self.mapToolMode == 1 and self.tempMoveCenter and self.isEmittingPoint:
            self.showMoveShape(tempPoint,tempPos)

    def canvasReleaseEvent(self, e: QgsMapMouseEvent):
        tempPos = e.pos()
        tempPoint: QgsPoint = self.toMapCoordinates(tempPos)
        if self.mapToolMode == 0:
            res = self.rectangle()
            if res == 1:
                queryCode,queryRes = self.pgw.queryFeaturesByPoint(tempPoint.x(),tempPoint.y(),self.taskId)
            elif type(res) == QgsRectangle:
                queryCode,queryRes = self.pgw.queryFeaturesByExtent(res.xMinimum(),res.yMinimum(),res.xMaximum(),res.yMaximum(),self.taskId)
            else:
                queryCode = True
                queryRes = []
            if queryCode:
                if e.modifiers() & Qt.ControlModifier:
                    pass
                else:
                    self.editLayer.deleteFeatures(self.editLayer.allFeatureIds())
                if len(queryRes) > 0:
                    for tempDict in queryRes:
                        tempWkt = str(tempDict['geometry']).replace('\'','\"')
                        tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.editLayer.fields(), None)[0]
                        if type(res) == QgsRectangle and not tempFeature.geometry().intersects(res):
                            continue
                        tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                        tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                        tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                        tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                        self.editLayer.addFeature(tempFeature)
                    self.editLayer.selectAll()
                    self.tempSelectedIds = self.editLayer.selectedFeatureIds()
                else:
                    self.tempSelectedIds = []
        elif self.mapToolMode == 1:
            self.showMoveShape(tempPoint,tempPos,True)
        elif self.mapToolMode == 2:
            pass
        
        self.reset(False)
        self.mapCanvas.refresh()
        self.mapCanvas.setCursor(Qt.ArrowCursor)
        if self.otherCanvas:
            self.otherCanvas.refresh()
        self.parentWindow.drawServerLayer.triggerRepaint()
        
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

        geometryList = []
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        for id in self.tempSelectedIds:
            tempFeature = self.editLayer.getFeature(id)
            tempFeatureId = tempFeature.attribute('FeatureId')
            remark1 = f"{tempFeature.attribute('remark1')}"
            remark2 = f"{tempFeature.attribute('remark1')}"
            remark3 = f"{tempFeature.attribute('remark1')}"
            newGeometry = tempFeature.geometry()
            newGeometry.translate(tempPoint.x() - self.tempMoveCenter.x(), tempPoint.y() - self.tempMoveCenter.y())
            if trueChange:
                self.editLayer.changeGeometry(id,newGeometry)
                self.pgw.updateFeature(tempFeatureId,newGeometry.asWkt(),self.userId,self.taskId,remark1,remark2,remark3,fishnetId)
                self.parentWindow.updateFeatureTable()
            else:
                geometryList.append(newGeometry)
        if len(geometryList) > 0:
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

# 选择渔网
class SelectFishnetMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,taskId,taskProjectType:appConfig.WebDrawQueryType,userId,parentWindow,otherCanvas=None):
        super(SelectFishnetMapTool,self).__init__(canvas)
        self.mapCanvas: QgsMapCanvas = canvas
        self.taskId = taskId
        self.taskProjectType = taskProjectType
        self.userId = userId

        if self.taskProjectType == appConfig.WebDrawQueryType.Draw:
            self.searchFieldName = 'repair_name'
        elif self.taskProjectType == appConfig.WebDrawQueryType.Review:
            self.searchFieldName = 'audit_name'
        elif self.taskProjectType == appConfig.WebDrawQueryType.Random:
            self.searchFieldName = 'random_name'

        self.parentWindow = parentWindow
        self.otherCanvas: QgsMapCanvas = otherCanvas 

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(250, 250, 5))
        self.rubberBand.setWidth(6)

        self.rubberBandRect = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBandRect.setColor(QColor(255, 0, 0, 50))
        self.rubberBandRect.setLineStyle(Qt.DashLine)
        self.rubberBandRect.setWidth(3)

        self.pgw = rsdmWeber()

        self.statusDict = {
            '601' : '待精修',
            '603' : '待质检（已精修）',
            '604' : '质检退回',
            '605' : '质检通过',
            '607' : '抽检通过',
            '608' : '抽检退回',
        }

        self.reset()
    
    def reset(self,resetIds=True):
        self.fishnetStatus = None  #选中单个渔网时，那个渔网的状态
        if resetIds:
            self.selectedFishnetIdList = [] #渔网的id列表

        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset()
        self.rubberBandRect.reset()
    
    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        tempPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton and not self.isEmittingPoint:
            self.startPoint = tempPoint
            self.endPoint = tempPoint
            self.isEmittingPoint = True
    
    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        tempPos = e.pos()
        tempPoint: QgsPoint = self.toMapCoordinates(tempPos)

        if self.isEmittingPoint:
            self.endPoint = tempPoint
            self.showRect()


    def canvasReleaseEvent(self, e:QgsMapMouseEvent):
        tempPoint : QgsPoint = self.toMapCoordinates(e.pos())
        if e.button() == Qt.MouseButton.LeftButton:
            
            res = self.rectangle()
            if res == 1:
                queryCode,queryRes = self.pgw.queryFishnet(tempPoint.x(),tempPoint.y(),self.taskId)
            elif type(res) == QgsRectangle:
                queryCode,queryRes = self.pgw.queryFishnetByExtent(res.xMinimum(),res.yMinimum(),res.xMaximum(),res.yMaximum(),self.taskId)
            else:
                queryCode = True
                queryRes = []

            tempWktList = []
            if queryCode:
                if e.modifiers() & Qt.ControlModifier:
                    pass
                else:
                    self.rubberBand.reset()
                    self.fishnetStatus = None  #选中单个渔网时，那个渔网的状态
                    self.selectedFishnetIdList = [] #渔网的id列表

                if len(queryRes) > 0:
                    if len(queryRes) == 1:
                        self.fishnetStatus = queryRes[0]['properties']['status']
                    else:
                        self.fishnetStatus = None

                    for tempDict in queryRes:
                        if tempDict['properties'][f"{self.searchFieldName}"] == self.userId and (tempDict['properties']['id'] not in self.selectedFishnetIdList):
                            self.selectedFishnetIdList.append(tempDict['properties']['id'])
                            tempWktList.append(str(tempDict['geometry']).replace('\'','\"'))
            
            if len(tempWktList) >0:
                for tempWkt in tempWktList:
                    tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt,QgsFields(), None)[0]
                    self.rubberBand.addGeometry(tempFeature.geometry())
            
            self.startPoint = self.endPoint = None
            self.isEmittingPoint = False
            self.rubberBandRect.reset()

        
        if e.button() == Qt.MouseButton.RightButton:
            #self.statusDict = {
            #     '601' : '待精修',
            #     '603' : '待质检（已精修）',
            #     '604' : '质检退回',
            #     '605' : '质检通过',
            #     '607' : '抽检通过',
            #     '608' : '抽检退回',
            cusMenu = RoundMenu(parent=self.parentWindow)
            cusMenu.setItemHeight(50)
            if len(self.selectedFishnetIdList) > 1:
                if self.taskProjectType == appConfig.WebDrawQueryType.Draw:
                    changeStatus601 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:待精修")
                    changeStatus601.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'601'))
                    cusMenu.addAction(changeStatus601)
                    changeStatus603 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:待质检（已精修）")
                    changeStatus603.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'603'))
                    cusMenu.addAction(changeStatus603)
                elif self.taskProjectType == appConfig.WebDrawQueryType.Review:
                    changeStatus604 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:质检退回")
                    changeStatus604.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'604'))
                    cusMenu.addAction(changeStatus604)
                    changeStatus605 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:质检通过")
                    changeStatus605.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'605'))
                    cusMenu.addAction(changeStatus605)
                elif self.taskProjectType == appConfig.WebDrawQueryType.Random:
                    changeStatus607 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:抽检通过")
                    changeStatus607.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'607'))
                    cusMenu.addAction(changeStatus607)
                    changeStatus608 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"批量修改为:抽检退回")
                    changeStatus608.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'608'))
                    cusMenu.addAction(changeStatus608)

            elif len(self.selectedFishnetIdList)==1 and self.fishnetStatus:
                currentStatus = Action(QIcon(':/img/resources/menu_prop.png'),f"当前状态:{self.statusDict[self.fishnetStatus]}")
                cusMenu.addAction(currentStatus)

                if self.taskProjectType == appConfig.WebDrawQueryType.Draw:
                    if self.fishnetStatus != '601':
                        changeStatus601 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:待精修")
                        changeStatus601.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'601'))
                        cusMenu.addAction(changeStatus601)
                    if self.fishnetStatus != '603':
                        changeStatus603 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:待质检（已精修）")
                        changeStatus603.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'603'))
                        cusMenu.addAction(changeStatus603)
                elif self.taskProjectType == appConfig.WebDrawQueryType.Review:
                    if self.fishnetStatus != '604':
                        changeStatus604 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:质检退回")
                        changeStatus604.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'604'))
                        cusMenu.addAction(changeStatus604)
                    if self.fishnetStatus != '605':
                        changeStatus605 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:质检通过")
                        changeStatus605.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'605'))
                        cusMenu.addAction(changeStatus605)
                elif self.taskProjectType == appConfig.WebDrawQueryType.Random:
                    if self.fishnetStatus != '607':
                        changeStatus607 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:抽检通过")
                        changeStatus607.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'607'))
                        cusMenu.addAction(changeStatus607)
                    if self.fishnetStatus != '608':
                        changeStatus608 = Action(QIcon(':/img/resources/gis/shp_modify_attr.png'),"修改为:抽检退回")
                        changeStatus608.triggered.connect(lambda: self.changeFishnetStatus(self.selectedFishnetIdList,'608'))
                        cusMenu.addAction(changeStatus608)

            curPos : QPoint = QCursor.pos()
            cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def showRect(self):
        self.rubberBandRect.reset(QgsWkbTypes.PolygonGeometry)
        if self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return

        self.rubberBandRect.addGeometry(QgsGeometry.fromRect(QgsRectangle(self.startPoint,self.endPoint)))
        self.rubberBandRect.show()
    
    def rectangle(self):
        if self.startPoint is None or self.endPoint is None:
            return None
        elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
            return 1
        return QgsRectangle(self.startPoint, self.endPoint) 
        

    def changeFishnetStatus(self,fishnetIdList,status):
        resCode = self.pgw.changeFishnetStatus(fishnetIdList,status)
        if resCode:
            self.reset()
            self.parentWindow.refreshCurrentRow()
        else:
            MessageBox('错误', "服务器状态更新失败，请联系管理员", self.parentWindow).exec_()
    
    def deactivate(self):
        self.reset()
        super().deactivate() 

# segment-anything 样本构建辅助算法mapTool
class WebSegAnyMapTool(QgsMapToolIdentify):
    def __init__(self,canvas,samInfer,layer,parentWindow,taskId,userId,otherCanvas=None,fieldValueDict=None,drawType=0):
        super(WebSegAnyMapTool, self).__init__(canvas)
        self.mapCanvas : QgsMapCanvas = canvas
        self.samInfer : samWeber = samInfer
        self.editLayer: QgsVectorLayer = layer  # 真正在上面创建矢量的图层
        self.parentWindow: QMainWindow = parentWindow
        self.taskId = taskId
        self.userId = userId
        self.fieldValueDict = fieldValueDict
        
        self.drawType = drawType # 0 正常 1 水平矩形
        self.otherCanvas = otherCanvas
        self.pgw = rsdmWeber()

        self.rubberBand = QgsRubberBand(self.mapCanvas, QgsWkbTypes.PolygonGeometry)
        self.rubberBand.setColor(QColor(255, 0, 0, 50))
        self.rubberBand.setWidth(4)

        # xform
        crs = QgsCoordinateReferenceSystem("EPSG:4490")
        crsDest = QgsCoordinateReferenceSystem("EPSG:3857")
        transformContext = PROJECT.transformContext()
        self.xform = QgsCoordinateTransform(crs, crsDest, transformContext)
        # zLevle transform
        self.maxScalePerPixel = 156543.04
        self.inchesPerMeter = 39.37

        self.reset()

    def fullSeg(self): #todo: 以后 全要素分割要用的  
        tempGeoList, reason = self.samInfer.magicInferMask(self.projectName,self.tifName)
        tempGeo: QgsGeometry
        self.parentWindow.editStack.beginMacro("fullSeg")
        for tempGeo in tempGeoList:
            tempGeo = tempGeo.makeValid()
            if tempGeo and tempGeo.isGeosValid():
                feat = QgsFeature(self.drawLayer.fields())
                feat.setAttribute(self.preField, self.preFieldValue[-1])
                feat.setGeometry(tempGeo.makeValid())
                self.drawLayer.addFeature(feat)
        self.parentWindow.editStack.endMacro()
        self.mapCanvas.refresh()
        if self.otherCanvas:
            self.otherCanvas.refresh()
        self.parentWindow.updateShpUndoRedoButton()

    def calZLevel(self):
        scale = self.mapCanvas.scale()
        dpi = self.parentWindow.physicalDpiX()
        z = int(round(math.log( ((dpi* self.inchesPerMeter * self.maxScalePerPixel) / scale), 2 ), 0))
        if z < 1:
            z = 0
        elif z > 18:
            z = 18
        return z

    def reset(self):
        self.points = []
        self.positivePoints = []
        self.negativePoints = []
        self.ctrlTempPolygon = None
        self.ctrlClsfyString = ""

        self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)

    def showTempPolygon(self):
        if self.ctrlTempPolygon:
            
            tempGeo = QgsGeometry(self.ctrlTempPolygon)
            tempGeo.transform(self.xform, self.xform.ReverseTransform)

            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
            self.rubberBand.setColor(QColor(209, 254, 0, 50))
            self.rubberBand.setWidth(4)
            self.rubberBand.addGeometry(tempGeo)

    def commitMagicTempPolygon(self):
        if self.ctrlTempPolygon:
            self.addFeature(self.ctrlTempPolygon)
        self.reset()
    
    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.modifiers() and Qt.ControlModifier and e.key() == Qt.Key.Key_Z:
            self.reset()
        return super().keyPressEvent(e)

    def canvasPressEvent(self, e):
        tempPoint4490: QgsPointXY = self.toMapCoordinates(e.pos())
        tempPoint = self.xform.transform(tempPoint4490)
        if e.modifiers() & Qt.ControlModifier:
            self.points.append(tempPoint)
        else:
            if e.button() == Qt.LeftButton:
                self.positivePoints.append(tempPoint)
            elif e.button() == Qt.RightButton:
                self.negativePoints.append(tempPoint)

    def addFeature(self,tempGeo):
        if appConfig.yoyiSetting().configSettingReader.value('simpleFeature',type=bool):
            newGeo: QgsGeometry = tempGeo.simplify(1.5)
            if newGeo.isGeosValid():
                tempGeo = newGeo

        tempGeo.transform(self.xform, self.xform.ReverseTransform)
        try:
            fishnetId = self.parentWindow.fishnetIdList[self.parentWindow.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        
        dialog = WebAttrEditDialogClass(remark1String=self.parentWindow.remark1String,
                                        remark1Type=self.parentWindow.remark1Type,
                                        remark1List=self.parentWindow.remark1List,
                                        remark1PreAttr=None,
                                        remark2String=self.parentWindow.remark2String,
                                        remark2Type=self.parentWindow.remark2Type,
                                        remark2List=self.parentWindow.remark2List,
                                        remark2PreAttr=None,
                                        remark3String=self.parentWindow.remark3String,
                                        remark3Type=self.parentWindow.remark3Type,
                                        remark3List=self.parentWindow.remark3List,
                                        remark3PreAttr=None,
                                        parent=self.parentWindow
                                        )
        dialog.exec()
        if dialog.remark1Attr is not None:
            tempWkt = tempGeo.asWkt()
            self.pgw.addFeature(tempWkt,self.userId,self.taskId,
                                dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
        self.reset()
        dialog.deleteLater()
        self.parentWindow.drawServerLayer.triggerRepaint()
        self.parentWindow.updateFeatureTable()

    def canvasReleaseEvent(self, e):
        if len(self.positivePoints) > 0:
            posiXs = [i.x() for i in self.positivePoints]
            posiYs = [i.y() for i in self.positivePoints]
            negaXs = [i.x() for i in self.negativePoints]
            negaYs = [i.y() for i in self.negativePoints]
            tempGeo,reason = self.samInfer.magicInferByPosiNega(posiXs,posiYs,negaXs,negaYs,self.calZLevel())
            if tempGeo:
                if self.drawType == 0:
                    self.ctrlTempPolygon = tempGeo
                elif self.drawType == 1:
                    tempRec: QgsRectangle = tempGeo.boundingBox()
                    self.ctrlTempPolygon = QgsGeometry.fromRect(tempRec)
                self.showTempPolygon()
            elif reason != "ok":
                MessageBox('错误', "服务器使用人数太多了，请再试一下吧~", self.parentWindow).exec_()
            self.isEmittingPoint = False
        elif len(self.points) == 1 :
            tempPoint = self.points[0]
            tempGeo,reason = self.samInfer.magicInferBySingle(tempPoint.x(),tempPoint.y(),self.calZLevel())

            if tempGeo:
                if self.drawType == 0:
                    self.addFeature(tempGeo)
                elif self.drawType == 1:
                    tempRec: QgsRectangle = tempGeo.boundingBox()
                    self.addFeature(QgsGeometry.fromRect(tempRec))
            elif reason !="ok":
                MessageBox('错误', "服务器使用人数太多了，请再试一下吧~", self.parentWindow).exec_()
            self.reset()

    def deactivate(self):
        self.reset()
        super().deactivate()