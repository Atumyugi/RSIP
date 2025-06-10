import os
import os.path as osp
from datetime import datetime
import ctypes
import subprocess
from ui.homeLocalWindow import Ui_homeLocalMainWindow
from PyQt5.QtCore import Qt,QSortFilterProxyModel,QStringListModel,QUrl,QModelIndex,QPoint,QDir,QCoreApplication
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon,QKeySequence, QPainter, QColor, QBrush, QPainterPath,QDesktopServices,QCursor,QStandardItemModel,QStandardItem
from PyQt5.QtWidgets import QStatusBar,QVBoxLayout,QSpacerItem,QWidget,QTreeWidgetItem,QMenu \
    ,QAction,QUndoStack,QMainWindow,QShortcut,QDialog,QColorDialog,QMessageBox,QSizePolicy \
    ,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication,QFileSystemModel, QHBoxLayout \
    ,QFrame,QAbstractItemView 
from qgis.core import QgsLayerTreeModel,QgsMapSettings,QgsProject,Qgis,QgsCoordinateReferenceSystem \
    ,QgsMapLayerType,QgsPointXY,QgsVectorLayer,QgsFeature,QgsFillSymbol,QgsWkbTypes
from qgis.gui import QgsLayerTreeMapCanvasBridge,QgsLayerTreeView,QgsMapCanvas,QgsMapToolPan,QgsMapToolZoom \
    ,QgsMapCanvasItem,QgsRubberBand,QgsNewVectorLayerDialog
import traceback
from qfluentwidgets import MessageBox,PushButton,LineEdit,SubtitleLabel,setFont,ComboBox \
    ,TransparentToolButton,ToolButton,SearchLineEdit,TreeWidget,CardWidget,RoundMenu,Action,BodyLabel \
    ,MenuAnimationType,ListView,TreeView,FlowLayout
from qfluentwidgets import FluentIcon as FIF
from appConfig import *

import widgets

from yoyiUtils import yoyiThread,yoyiToolbox
from yoyiUtils.maptool_utils import makeValid_deleteAngle0
from yoyiUtils.custom_maptool import PolygonMapTool,ReShapePolygonMapTool,SplitPolygonMapTool,EditVertexMapTool,RecTangleSelectFeatureMapTool,MeasureDistanceMapTool,MeasureAreaMapTool,YoyiMapCanvas
from yoyiUtils.custom_swipMaptool import SwipeMapTool
from yoyiUtils.custom_widget import BetterCardWidget,HorizontalLabel
from yoyiUtils.qgisLayerUtils import getFIDlist,addMapLayer,readRasterFile,readVectorFile,loadWmsasLayer
from yoyiUtils.qgisMenu import menuProvider
from yoyiUtils.yoyiDefault import InferType,InferTypeName
from yoyiUtils.yoyiTranslate import yoyiTrans

import yoyirs_rc

PROJECT = QgsProject.instance()
class UnderToolButton(ToolButton):
    def _drawIcon(self, icon, painter: QPainter, rect, state):
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        super(UnderToolButton, self)._drawIcon(icon, painter, rect, state)


class HomeLocalWindowClass(Ui_homeLocalMainWindow,QMainWindow):
    def __init__(self, parent=None,extraFile=None,mode="common"):
        super(HomeLocalWindowClass, self).__init__(parent)
        self.parentWindow = parent
        self.mode = mode
        self.TEMPDIR = self.parentWindow.TEMPDIR
        self.setting = yoyiSetting()

        self.setupUi(self)
        self.initUI()
        # 状态栏 connect
        self.actionStatsBarConnectFunc()
        # 文件树 connect
        # 图层树 connect
        self.layerTreeConnectFunc()
        # 常规 connect
        self.actionMapToolConnectFunc()
        self.actionOpenConnectFunc()
        self.actionCommonConnectFunc()
        #self.action
        # 处理 process
        self.actionTifProcessConnectFunc()
        self.actionShpProcessConnectFunc()
        # 解译 infer
        self.actionInferConnectFunc()

        if extraFile:
            print(extraFile)
            if osp.basename(extraFile).split(".")[-1] == "shp":
                self.addVectorLayer(extraFile)
            elif osp.basename(extraFile).split(".")[-1] == "tif" or osp.basename(extraFile).split(".")[-1] == "TIF":
                self.addRasterLayer(extraFile)
        
        self.retranslateDiyUI()
    
    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        self.toolboxTitleLabel.setText(_translate("DIYDialog", "Toolbox"))
        self.layerTitleLabel.setText(_translate("homeLocalMainWindow", "Layers"))
        self.SegmentedWidget.widget("inferSW").setText(_translate("DIYDialog", "Intelligent Extract"))
        self.SegmentedWidget.widget("commonSW").setText(_translate("DIYDialog", "Common"))
        self.SegmentedWidget.widget("tifProcessSW").setText(yoyiTrs._translate('数据处理'))
        self.SegmentedWidget.widget("shpProcessSW").setText(_translate("DIYDialog", "Training"))
        
        #GIS 工具栏
        #第一个栏
        self.panMapToolPb.setText(_translate("DIYDialog","Pan"))
        self.selectFeatureMapToolPb.setText(_translate("DIYDialog","Select"))
        self.zoomOutMapToolPb.setText(_translate("DIYDialog","Zoom Out"))
        self.zoomInMapToolPb.setText(_translate("DIYDialog","Zoom In"))
        self.scaelToFullExtentPb.setText(_translate("DIYDialog","Scale Full"))
        self.newVectorLayerPb.setText(_translate("DIYDialog","New Vector"))
        self.editShapefilePb.setText(_translate("DIYDialog","Editing"))
        self.saveEditPb.setText(_translate("DIYDialog","Save Edit"))
        self.undoPb.setText(_translate("DIYDialog","Undo"))
        self.redoPb.setText(_translate("DIYDialog","Redo"))
        self.polygonMapToolPb.setText(_translate("DIYDialog","Polygon Tool"))
        self.splitMapToolPb.setText(_translate("DIYDialog","Split Tool"))
        self.editVertexMapToolPb.setText(_translate("DIYDialog","Vertex Tool"))
        self.reshapeMapToolPb.setText(_translate("DIYDialog","Reshape Tool"))
        self.changeFeatureAttributePb.setText(_translate("DIYDialog","Change Attr"))
        self.mergeMapToolPb.setText(_translate("DIYDialog","Merge"))
        self.deleteFeaturePb.setText(_translate("DIYDialog","Delete Feature"))
        #第二个栏
        self.measureAreaMapToolPb.setText(_translate("DIYDialog","Measure Area"))
        self.measureDistanceMapToolPb.setText(_translate("DIYDialog","Measure Distance"))
        self.lonlatSearchPb.setText(_translate("DIYDialog","Lonlat Search"))
        self.swipeTb.setText(_translate("DIYDialog","Rolling Shutter"))
        self.createFishNetPb.setText(_translate("DIYDialog","Generate Fish Net"))
        #第三个栏
        self.shpExportPb.setText(_translate("DIYDialog","Export Vector"))
        self.shpCalCentroidPb.setText(_translate("DIYDialog","Cal Centroid"))
        self.shpErasePb.setText(_translate("DIYDialog","Vector Erase"))
        self.shpOrthPb.setText(_translate("DIYDialog","Vector Orth"))
        self.shpCalAreaPb.setText(_translate("DIYDialog","Vector CalArea"))
        self.shpChangeAnalysisPb.setText(_translate("DIYDialog","Change Analysis"))
        #第四个栏
        self.rasterBuildOverviewPb.setText(_translate("DIYDialog","Generate OVR"))
        self.saveAsImgPb.setText(_translate("DIYDialog","Capture Canvas"))

        #Common 常规
        #第一栏
        self.openProjectPb.setText(_translate("DIYDialog","Open Project"))
        self.openRasterPb.setText(_translate("DIYDialog","Open Tif"))
        self.openShapeFilePb.setText(_translate("DIYDialog","Open Shp"))
        self.openXYZTilesPb.setText(_translate("DIYDialog","Open XYZTiles"))
        #第二栏
        self.saveProjectPb.setText(_translate("DIYDialog","Save"))
        self.saveAsProjectPb.setText(_translate("DIYDialog","Save As"))
        self.helpPb.setText(_translate("DIYDialog","Help"))
        self.supportPb.setText(_translate("DIYDialog","Support"))
        self.jl1Pb.setText(_translate("DIYDialog","JL1 Tiles"))
        self.jl1SitePb.setText(_translate("DIYDialog","Into JL1"))

        #Infer 解译
        self.batchInferPb.setText(_translate("DIYDialog","Batch Infer"))
        self.customizeSegPb.setText(_translate("DIYDialog","Customize Extract"))

        #Process 处理
        #第一栏
        self.singleLabelingPb.setText(_translate("DIYDialog","Single Labeling"))
        self.changeLabelingPb.setText(_translate("DIYDialog","Change Labeling"))
        self.jointLabelingPb.setText(_translate("DIYDialog","Joint Labeling"))
        #第二栏
        self.shp2RasterPb.setText(_translate("DIYDialog","Vector Rasterization"))
        self.shpClipPb.setText(_translate("DIYDialog","Vector Clip"))
        self.shpInterPb.setText(_translate("DIYDialog","Vector Intersect"))
        self.shpBufferPb.setText(_translate("DIYDialog","Vector Buffer"))
        self.shp2SinglePb.setText(_translate("DIYDialog","Multi to Single"))
        self.shpMergePb.setText(_translate("DIYDialog","Vector Merge"))
        self.shpDissolvePb.setText(_translate("DIYDialog","Vector Dissolve"))
        self.shpRemoveSmallPb.setText(_translate("DIYDialog","Remove Area"))
        #第三栏
        self.raster2ShpPb.setText(_translate("DIYDialog","Raster vectorization"))
        self.raster16to8Pb.setText(_translate("DIYDialog","Raster Uint16 to Uint8"))
        self.rasterClipPb.setText(_translate("DIYDialog","Raster Clip"))
        self.rasterReprojectPb.setText(_translate("DIYDialog","Raster Reproject"))
        self.rasterExportPb.setText(_translate("DIYDialog","Export Raster"))
        self.rasterRecombinePb.setText(_translate("DIYDialog","Raster Recombine"))
        self.rasterMergePb.setText(_translate("DIYDialog","Raster Merge"))
        self.rasterCalcPb.setText(_translate("DIYDialog","Raster Calculator"))

        self.objectOutputPb.setText(_translate("DIYDialog","Object Output"))

        #Train 训练
        self.createDatasetPb.setText(_translate("DIYDialog","Generate Dataset"))
        self.splitDatasetPb.setText(_translate("DIYDialog","Split Dataset"))
        self.trainToolPb.setText(_translate("DIYDialog","Train Tool"))

        self.actionExpandAllNodes.setText(yoyiTrs._translate('展开'))
        self.actionCollapseAllNodes.setText(yoyiTrs._translate('折叠'))
        self.actionDeleteLayer.setText(yoyiTrs._translate('移除选中图层'))

        self.rightMenuProv = menuProvider(self,self.parentWindow.yoyiTrans)
        self.layerTreeView.setMenuProvider(self.rightMenuProv)

        # 大棚比较特殊
        self.greenHouseMenu = RoundMenu(parent=self)
        self.actionGhseg = Action(text=_translate("homeLocalMainWindow", "GreenHouse Polygon Extract"),parent=self)
        self.actionGhseg.triggered.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.GreenHouse))
        if yoyiTrs.language == "Ch":
            self.actionGhseg.setText("塑料大棚面提取")
        
        self.actionGhdetec = Action(text=_translate("homeLocalMainWindow", "GreenHouse Detec"),parent=self)
        self.actionGhdetec.triggered.connect(lambda: self.detecInferPbClicked(InferType.ObbDetection,InferTypeName.GreenHouse))
        if yoyiTrs.language == "Ch":
            self.actionGhdetec.setText("塑料大棚检测")
        
        self.actionBrokenGh = Action(text=_translate("homeLocalMainWindow", "Broken GH Detec"),parent=self)
        self.actionBrokenGh.triggered.connect(lambda: self.detecInferPbClicked(InferType.ObbDetection,InferTypeName.BrokenGH))
        if yoyiTrs.language == "Ch":
            self.actionBrokenGh.setText("破损塑料大棚检测")

        self.greenHouseMenu.addAction(self.actionGhseg)
        self.greenHouseMenu.addAction(self.actionGhdetec)
        self.greenHouseMenu.addAction(self.actionBrokenGh)
        self.greenHousePb.setFlyout(self.greenHouseMenu)

        self.mapCanvas.changeTrs(yoyiTrs)
    
    def deleteChildDialog(self):

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget,QDialog) and widget.parent() is None:
                print(f"Closing dialog: {widget.windowTitle()}")
                widget.close()
                widget.deleteLater()

    def hideLayerDockPbClicked(self):
        self.dockWidgetLayer.hide()
        self.showLayerDockPb.show()
    
    def showLayerDockPbClicked(self):
        self.dockWidgetLayer.show()
        self.showLayerDockPb.hide()
    
    def hideToolboxDockPbClicked(self):
        self.dockWidgetToolbox.hide()
        self.showToolboxDockPb.show()
    
    def showToolboxDockPbClicked(self,extraOption=None):
        self.dockWidgetToolbox.show()
        if extraOption:
            self.toolboxTree.expandAll()
            # if extraOption == 'shp':
            #     self.toolboxTree.expand(self.itemShp.index())
            # elif extraOption == 'tif':
            #     self.toolboxTree.expand(self.itemTif.index())
        self.showToolboxDockPb.hide()

    def initUI(self):
        #
        # 0 图层树
        self.layerTitleWidget = QWidget(self)
        layerTitleLayout = QHBoxLayout(self.layerTitleWidget)
        layerTitleLayout.setContentsMargins(4, 4, 4, 4)
        self.layerTitleLabel = BodyLabel(self)
        layerTitleLayout.addWidget(self.layerTitleLabel)
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layerTitleLayout.addItem(spacerItem1)
        self.hideLayerDockPb = TransparentToolButton(':/img/resources/menu_collaH.png',self)
        layerTitleLayout.addWidget(self.hideLayerDockPb)
        self.showLayerDockPb.hide()
        self.hideLayerDockPb.clicked.connect(self.hideLayerDockPbClicked)
        self.showLayerDockPb.clicked.connect(self.showLayerDockPbClicked)
        self.dockWidgetLayer.setTitleBarWidget(self.layerTitleWidget)

        # 1 工具箱
        self.toolboxTitleWidget = QWidget(self)
        toolboxTitleLayout = QHBoxLayout(self.toolboxTitleWidget)
        toolboxTitleLayout.setContentsMargins(4, 4, 4, 4)
        self.toolboxTitleLabel = BodyLabel(self)
        toolboxTitleLayout.addWidget(self.toolboxTitleLabel)
        spacerItem2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        toolboxTitleLayout.addItem(spacerItem2)
        self.hideToolboxDockPb = TransparentToolButton(':/img/resources/close.png',self)
        toolboxTitleLayout.addWidget(self.hideToolboxDockPb)
        self.hideToolboxDockPb.clicked.connect(self.hideToolboxDockPbClicked)
        self.showToolboxDockPb.clicked.connect(self.showToolboxDockPbClicked)
        self.dockWidgetToolbox.setTitleBarWidget(self.toolboxTitleWidget)

        self.hideToolboxDockPbClicked()


        # 2 顶栏
        self.dockWidgetTop.setTitleBarWidget(QWidget(self))
        self.SegmentedWidget.addItem(routeKey='commonSW',text="",onClick=lambda: self.stackedWidget.setCurrentIndex(0),icon=':/img/resources/title/top1-common.png')
        self.SegmentedWidget.addItem(routeKey='inferSW',text="",onClick=lambda: self.stackedWidget.setCurrentIndex(1),icon=':/img/resources/title/top2-infer.png')
        self.SegmentedWidget.addItem(routeKey='tifProcessSW',text="",onClick=lambda: self.stackedWidget.setCurrentIndex(2),icon=':/img/resources/title/top3-processing.png')
        self.SegmentedWidget.addItem(routeKey='shpProcessSW',text="",onClick=lambda: self.stackedWidget.setCurrentIndex(3),icon=':/img/resources/title/top4-train.png')
        
        self.stackedWidget.setCurrentIndex(0)
        self.SegmentedWidget.setCurrentItem('commonSW')

        smallIconW = 50
        smallIconH = 60
        smallIconSize = 25
        bigIconW = 70
        bigIconH = 65

        # 0.5 底下的GIS工具栏
        insertIndex = -1
        # flow layout
        # 0.5.1 第一个栏
        self.panMapToolPb = BetterCardWidget(True,'Pan',":/img/resources/gis/gis_pan.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut='Q')
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.panMapToolPb)
        
        self.zoomInMapToolPb = BetterCardWidget(True,'Zoom In',":/img/resources/gis/gis_zoom_in.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.zoomInMapToolPb)

        self.zoomOutMapToolPb = BetterCardWidget(True,'Zoom Out',":/img/resources/gis/gis_zoom_out.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.zoomOutMapToolPb)

        self.scaelToFullExtentPb = BetterCardWidget(False,'Scale Full',":/img/resources/menu_zoomToLayer.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.scaelToFullExtentPb)

        self.trspb0 = TransparentToolButton(':/img/resources/separator.png',self)
        self.trspb0.setIconSize(QtCore.QSize(8,24))
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.trspb0)

        self.selectFeatureMapToolPb = BetterCardWidget(True,'Select',":/img/resources/gis/shp_select_multi.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,disableIconPath=":/img/resources/gis/shp_select_multi_disable.png",shortcut="S")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.selectFeatureMapToolPb)
        self.selectFeatureMapToolPb.setEnabled(False)

        self.newVectorLayerPb = BetterCardWidget(False,'New Vector',":/img/resources/open_new_shp.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.newVectorLayerPb)

        self.editShapefilePb = BetterCardWidget(True,'Editing',":/img/resources/gis/shp_edit.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,disableIconPath=":/img/resources/gis/shp_edit_disable.png")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.editShapefilePb)
        self.editShapefilePb.setEnabled(False)

        self.saveEditPb = BetterCardWidget(False,'Save Edit',":/img/resources/gis/save_edit.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.saveEditPb)
        self.saveEditPb.hide()

        self.undoPb = BetterCardWidget(False,'Undo',":/img/resources/gis/edit_undo.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,disableIconPath=":/img/resources/gis/edit_undo_disable.png",shortcut="Ctrl+Z")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.undoPb)
        self.undoPb.setEnabled(False)
        self.undoPb.hide()

        self.redoPb = BetterCardWidget(False,'Redo',":/img/resources/gis/edit_redo.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,disableIconPath=":/img/resources/gis/edit_redo_disable.png",shortcut="Ctrl+Shift+Z")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.redoPb)
        self.redoPb.setEnabled(False)
        self.redoPb.hide()

        self.polygonMapToolPb = BetterCardWidget(True,'Polygon',":/img/resources/gis/edit_polygon.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="E")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.polygonMapToolPb)
        self.polygonMapToolPb.hide()

        self.splitMapToolPb = BetterCardWidget(True,'Split',":/img/resources/gis/shp_clip_polygon.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="Z")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.splitMapToolPb)
        self.splitMapToolPb.hide()

        self.editVertexMapToolPb = BetterCardWidget(True,'Vertex',":/img/resources/gis/shp_vertexTool.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="X")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.editVertexMapToolPb)
        self.editVertexMapToolPb.hide()

        self.reshapeMapToolPb = BetterCardWidget(True,'Reshape',":/img/resources/gis/shp_clip_1.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="C")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.reshapeMapToolPb)
        self.reshapeMapToolPb.hide()

        self.mergeMapToolPb = BetterCardWidget(False,'Merge',":/img/resources/gis/shp_merge.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="F1")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.mergeMapToolPb)
        self.mergeMapToolPb.hide()

        self.deleteFeaturePb = BetterCardWidget(False,'Del Feature',':/img/resources/gis/shp_delete_select.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="Del")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.deleteFeaturePb)
        self.deleteFeaturePb.hide()

        self.changeFeatureAttributePb = BetterCardWidget(False,'Change Attr',':/img/resources/gis/shp_modify_attr.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize,shortcut="F2")
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.changeFeatureAttributePb)
        self.changeFeatureAttributePb.hide()

        self.trspb1 = TransparentToolButton(':/img/resources/separator.png',self)
        self.trspb1.setIconSize(QtCore.QSize(8,24))
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.trspb1)

        # 0.5.2 第二个栏
        self.measureAreaMapToolPb = BetterCardWidget(True,'Measure Area',":/img/resources/measure_area.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.measureAreaMapToolPb)

        self.measureDistanceMapToolPb = BetterCardWidget(True,'Measure Distance',":/img/resources/measure_distance.png",w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.measureDistanceMapToolPb)

        self.createFishNetPb = BetterCardWidget(False,'Generate Fish Net',':/img/resources/fishNet.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.createFishNetPb)

        self.trspb2 = TransparentToolButton(':/img/resources/separator.png',self)
        self.trspb2.setIconSize(QtCore.QSize(8,24))
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.trspb2)

        # 0.5.3 第三个栏
        self.shpExportPb = BetterCardWidget(False,'Export Vector',':/img/resources/shpProcess/shp_export.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpExportPb)

        self.shpCalCentroidPb = BetterCardWidget(False,'Cal Centroid',':/img/resources/shpProcess/shp_calCentorid.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpCalCentroidPb)

        self.shpErasePb = BetterCardWidget(False,'Vector Erase',':/img/resources/shpProcess/shp_erase.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpErasePb)

        self.shpOrthPb = BetterCardWidget(False,'Vector Orth',':/img/resources/shpProcess/shp_orth.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpOrthPb)

        self.shpCalAreaPb = BetterCardWidget(False,'Vector CalArea',':/img/resources/shpProcess/shp_calArea.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpCalAreaPb)

        self.shpChangeAnalysisPb = BetterCardWidget(False,'Change Analysis',':/img/resources/shpProcess/shp_changeAna.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.shpChangeAnalysisPb)

        self.trspb3 = TransparentToolButton(':/img/resources/separator.png',self)
        self.trspb3.setIconSize(QtCore.QSize(8,24))
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.trspb3)

        # 0.5.4 第三个栏
        self.rasterBuildOverviewPb = BetterCardWidget(False,'Generate OVR',':/img/resources/tifProcess/tif_ovr.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.rasterBuildOverviewPb)

        self.saveAsImgPb = BetterCardWidget(False,'Capture Canvas',':/img/resources/saveAsImg.png',w=smallIconW,h=smallIconH,parent=self,iconSize=smallIconSize)
        self.horizontalLayout_Tool.insertWidget(insertIndex:=insertIndex+1,self.saveAsImgPb)

        #0.6 常规
        #0.6.1 第一栏
        insertCommonIndex = -1
        self.openProjectPb = BetterCardWidget(False,'Open Project',':/img/resources/open_project.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.openProjectPb)

        self.openRasterPb = BetterCardWidget(False,'Open Tif',':/img/resources/open_tif.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.openRasterPb)

        self.openShapeFilePb = BetterCardWidget(False,'Open Shp',':/img/resources/open_shp.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.openShapeFilePb)

        self.openXYZTilesPb = BetterCardWidget(False,'Open XYZTiles',':/img/resources/HTTPTif.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.openXYZTilesPb)

        self.sepLine1 = QFrame(self.commonPage)
        self.sepLine1.setFrameShape(QFrame.VLine)
        self.sepLine1.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.sepLine1)

        #0.6.2 第二栏
        self.saveProjectPb = BetterCardWidget(False,'Save',':/img/resources/open_save.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.saveProjectPb)

        self.saveAsProjectPb = BetterCardWidget(False,'Save As',':/img/resources/open_saveas.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.saveAsProjectPb)

        self.sepLine2 = QFrame(self.commonPage)
        self.sepLine2.setFrameShape(QFrame.VLine)
        self.sepLine2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.sepLine2)

        #0.6.3 第三栏
        self.helpPb = BetterCardWidget(False,'Help',':/img/resources/other_helpBook.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.helpPb)

        self.supportPb = BetterCardWidget(False,'Support',':/img/resources/other_support.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.supportPb)

        self.lonlatSearchPb = BetterCardWidget(True,'Lonlat Search',':/img/resources/lonlatsearch.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.lonlatSearchPb)

        self.swipeTb = BetterCardWidget(True,'Rolling Shutter',':/img/resources/gis/gis_rollerShutter.png',w=bigIconW,h=bigIconW,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.swipeTb)
        
        self.jl1Pb = BetterCardWidget(False,'JL1 Tiles',':/img/resources/free.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.jl1Pb)

        self.jl1SitePb = BetterCardWidget(False,'Into JL1',':/img/resources/CGlogo.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_common.insertWidget(insertCommonIndex:=insertCommonIndex+1,self.jl1SitePb)

        #0.7 解译
        self.batchInferPb = BetterCardWidget(False,'Batch Infer',':/img/resources/infer/batchInfer.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_5.insertWidget(0,self.batchInferPb)
        self.customizeSegPb = BetterCardWidget(False,'Customize Extract',':/img/resources/infer/other_model.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_5.addWidget(self.customizeSegPb)
        spacerItem3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem3)
        
        #0.8 处理
        #0.8 处理 第一栏
        self.shpLabelingSpacer = HorizontalLabel('矢量标注',self)
        self.shpLabelingSpacer.initLabel()
        self.horizontalLayout_process.addWidget(self.shpLabelingSpacer)

        self.singleLabelingPb = BetterCardWidget(False,'Single Labeling',':/img/resources/title/t2-singleLabeling.png',w=bigIconW,h=bigIconH,parent=self)
        self.singleLabelingPb.clicked.connect(lambda :self.parentWindow.setCurrentStackWidget('segmentDraw'))
        self.horizontalLayout_process.addWidget(self.singleLabelingPb)
        
        self.changeLabelingPb = BetterCardWidget(False,'Change Labeling',':/img/resources/title/t3-cdLabeling.png',w=bigIconW,h=bigIconH,parent=self)
        self.changeLabelingPb.clicked.connect(lambda :self.parentWindow.setCurrentStackWidget('cdDraw'))
        self.horizontalLayout_process.addWidget(self.changeLabelingPb)

        self.jointLabelingPb = BetterCardWidget(False,'Joint Labeling',':/img/resources/title/t4-jointLabeling.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_process.addWidget(self.jointLabelingPb)

        self.sepLine3 = QFrame(self.processPage)
        self.sepLine3.setFrameShape(QFrame.VLine)
        self.sepLine3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_process.addWidget(self.sepLine3)

        #0.8 处理 第二栏
        self.shpProcessingSpacer = HorizontalLabel('矢量处理',self)
        self.shpProcessingSpacer.initLabel()
        self.horizontalLayout_process.addWidget(self.shpProcessingSpacer)
        #0.8 处理 第二栏 top
        self.verticalLayout_shpProcess = QVBoxLayout()
        self.horizontalLayout_shpProcess_top = QHBoxLayout()
        self.verticalLayout_shpProcess.addLayout(self.horizontalLayout_shpProcess_top)
        self.horizontalLayout_shpProcess_bottom = QHBoxLayout()
        self.verticalLayout_shpProcess.addLayout(self.horizontalLayout_shpProcess_bottom)
        self.horizontalLayout_process.addLayout(self.verticalLayout_shpProcess)

        self.shp2RasterPb = PushButton(QIcon(':/img/resources/shpProcess/shp_2raster.png'),'Vector Rasterization',self)
        self.horizontalLayout_shpProcess_top.addWidget(self.shp2RasterPb)

        self.shpClipPb = PushButton(QIcon(':/img/resources/gis/shp_clip_polygon.png'),'Vector Clip',self)
        self.horizontalLayout_shpProcess_top.addWidget(self.shpClipPb)

        self.shpInterPb = PushButton(QIcon(':/img/resources/shpProcess/shp_interesct.png'),'Vector Intersect',self)
        self.horizontalLayout_shpProcess_top.addWidget(self.shpInterPb)

        self.shpBufferPb = PushButton(QIcon(':/img/resources/shpProcess/shp_buffer.png'),'Vector Buffer',self)
        self.horizontalLayout_shpProcess_top.addWidget(self.shpBufferPb)

        #0.8 处理 第二栏 bottom
        self.shp2SinglePb = PushButton(QIcon(':/img/resources/shpProcess/shp_split.png'),'Multi to Single',self)
        self.horizontalLayout_shpProcess_bottom.addWidget(self.shp2SinglePb)

        self.shpMergePb = PushButton(QIcon(':/img/resources/gis/shp_merge.png'),'Vector Merge',self)
        self.horizontalLayout_shpProcess_bottom.addWidget(self.shpMergePb)

        self.shpDissolvePb = PushButton(QIcon(':/img/resources/shpProcess/shp_dissolve.png'),'Vector Dissolve',self)
        self.horizontalLayout_shpProcess_bottom.addWidget(self.shpDissolvePb)

        self.shpRemoveSmallPb = PushButton(QIcon(':/img/resources/shpProcess/shp_removeArea.png'),'Remove Area',self)
        self.horizontalLayout_shpProcess_bottom.addWidget(self.shpRemoveSmallPb)

        #0.8 处理 第二栏 右下角 
        self.verticalLayout_shpProcess_more = QVBoxLayout()
        self.horizontalLayout_process.addLayout(self.verticalLayout_shpProcess_more)
        spacerItem5 = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_shpProcess_more.addItem(spacerItem5)
        self.shpProcessingMorePb = TransparentToolButton(':/img/resources/more.png',self)
        self.shpProcessingMorePb.clicked.connect(lambda :self.showToolboxDockPbClicked('shp'))
        self.verticalLayout_shpProcess_more.addWidget(self.shpProcessingMorePb)

        self.sepLine4 = QFrame(self.processPage)
        self.sepLine4.setFrameShape(QFrame.VLine)
        self.sepLine4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_process.addWidget(self.sepLine4)
        #0.8 处理 第三栏 栅格处理

        self.tifProcessingSpacer = HorizontalLabel('栅格处理',self)
        self.tifProcessingSpacer.initLabel()
        self.horizontalLayout_process.addWidget(self.tifProcessingSpacer)
        #0.8 处理 第三栏 栅格处理 TOP
        self.verticalLayout_tifProcess = QVBoxLayout()
        self.horizontalLayout_tifProcess_top = QHBoxLayout()
        self.verticalLayout_tifProcess.addLayout(self.horizontalLayout_tifProcess_top)
        self.horizontalLayout_tifProcess_bottom = QHBoxLayout()
        self.verticalLayout_tifProcess.addLayout(self.horizontalLayout_tifProcess_bottom)
        self.horizontalLayout_process.addLayout(self.verticalLayout_tifProcess)

        self.raster2ShpPb = PushButton(QIcon(':/img/resources/tifProcess/tif_2shp.png'),'Raster vectorization',self)
        self.horizontalLayout_tifProcess_top.addWidget(self.raster2ShpPb)

        self.raster16to8Pb = PushButton(QIcon(':/img/resources/tifProcess/tif_1628.png'),'Raster Uint16 to Uint8',self)
        self.horizontalLayout_tifProcess_top.addWidget(self.raster16to8Pb)

        self.rasterClipPb = PushButton(QIcon(':/img/resources/tifProcess/tif_clip.png'),'Raster Clip',self)
        self.horizontalLayout_tifProcess_top.addWidget(self.rasterClipPb)

        self.rasterReprojectPb = PushButton(QIcon(':/img/resources/tifProcess/tif_reproject.png'),'Raster Reproject',self)
        self.horizontalLayout_tifProcess_top.addWidget(self.rasterReprojectPb)

        #0.8 处理 第三栏 栅格处理 BOTTOM
        self.rasterExportPb = PushButton(QIcon(':/img/resources/export.png'),'Export Raster',self)
        self.horizontalLayout_tifProcess_bottom.addWidget(self.rasterExportPb)

        self.rasterRecombinePb = PushButton(QIcon(':/img/resources/tifProcess/tif_reCombine.png'),'Raster Recombine',self)
        self.horizontalLayout_tifProcess_bottom.addWidget(self.rasterRecombinePb)

        self.rasterMergePb = PushButton(QIcon(':/img/resources/tifProcess/tif_merge.png'),'Raster Merge',self)
        self.horizontalLayout_tifProcess_bottom.addWidget(self.rasterMergePb)

        self.rasterCalcPb = PushButton(QIcon(':/img/resources/tifProcess/calNorm.png'),'Raster Calculator',self)
        self.horizontalLayout_tifProcess_bottom.addWidget(self.rasterCalcPb)

        #0.8 处理 第三栏 栅格处理 右下角 
        self.verticalLayout_tifProcess_more = QVBoxLayout()
        self.horizontalLayout_process.addLayout(self.verticalLayout_tifProcess_more)
        spacerItem7 = QSpacerItem(40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_tifProcess_more.addItem(spacerItem7)
        self.tifProcessingMorePb = TransparentToolButton(':/img/resources/more.png',self)
        self.tifProcessingMorePb.clicked.connect(lambda: self.showToolboxDockPbClicked('tif'))
        self.verticalLayout_tifProcess_more.addWidget(self.tifProcessingMorePb)

        self.sepLine5 = QFrame(self.processPage)
        self.sepLine5.setFrameShape(QFrame.VLine)
        self.sepLine5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_process.addWidget(self.sepLine5)

        self.objectOutputPb = BetterCardWidget(False,'Object Output',':/img/resources/shpProcess/shp_objectOutput.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_process.addWidget(self.objectOutputPb)

        self.excelTransLinePb = BetterCardWidget(False,'生成线路',':/img/resources/shpProcess/shp_objectOutput.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_process.addWidget(self.excelTransLinePb)

        #0.9 训练 
        self.createDatasetPb = BetterCardWidget(False,'Generate Dataset',':/img/resources/geneDs.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_train.addWidget(self.createDatasetPb)

        self.splitDatasetPb = BetterCardWidget(False,'Split Dataset',':/img/resources/splitDataset.png',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_train.addWidget(self.splitDatasetPb)

        self.trainToolPb = BetterCardWidget(False,'Train Tool',':/img/resources/train.ico',w=bigIconW,h=bigIconH,parent=self)
        self.horizontalLayout_train.addWidget(self.trainToolPb)

        spacerItem4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout_train.addItem(spacerItem4)


        # 1 mapcanvas
        self.mapCanvas : QgsMapCanvas = YoyiMapCanvas(self,self.parentWindow.yoyiTrans)
        self.mapCanvas.setParallelRenderingEnabled(True)
        self.mapCanvas.setCachingEnabled(True)
        self.mapCanvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
        self.hl = QHBoxLayout(self.frame)
        self.hl.setContentsMargins(0, 0, 0, 0)
        self.hl.addWidget(self.mapCanvas)
        
        # 2 图层树与文件树
        # 2.1 图层树
        self.layerTreeView = QgsLayerTreeView(self)
        self.layerTreeViewLayout.addWidget(self.layerTreeView)
        # 2.2 工具箱树
        # 侧边栏树状视图的搜索栏
        self.toolboxSearchLineEdit = SearchLineEdit(self)
        self.toolboxSearchLineEdit.setClearButtonEnabled(True)
        self.toolboxSearchLineEdit.textChanged.connect(self.toolboxSearchLineEditUpdateFilter)
        self.toolboxLayout.addWidget(self.toolboxSearchLineEdit)
        
        # 工具箱树的主体
        self.toolboxTree = TreeView(self)
        self.toolboxLayout.addWidget(self.toolboxTree)
        
        # 创建源模型
        self.toolboxTreeSourceModel = QStandardItemModel()
        rootItem = self.toolboxTreeSourceModel.invisibleRootItem()
        
        # 添加工具箱的各项
        self.itemShp = QStandardItem("矢量处理 (Vector)")
        rootItem.appendRow(self.itemShp)
        
        self.itemShp_geo = QStandardItem("地理处理 (Vector Geometry)")
        self.itemShp_geo.appendRows(yoyiToolbox.getItems_shp_geo())
        
        self.itemShp_common = QStandardItem("通用工具 (Vector Common)")
        self.itemShp_common.appendRows(yoyiToolbox.getItems_shp_common())
        
        self.itemShp_trans = QStandardItem("转换工具 (Vector Translation)")
        self.itemShp_trans.appendRows(yoyiToolbox.getItems_shp_trans())

        self.itemShp_analysis = QStandardItem("分析工具 (Vector Analysis)")
        self.itemShp_analysis.appendRows(yoyiToolbox.getItems_shp_analysis())
        
        self.itemShp.appendRows([
            self.itemShp_geo,
            self.itemShp_common,
            self.itemShp_trans,
            self.itemShp_analysis
        ])
        
        self.itemTif = QStandardItem("栅格处理 (Raster)")
        rootItem.appendRow(self.itemTif)
        
        self.itemTif_common = QStandardItem("通用工具 (Raster Common)")
        self.itemTif_common.appendRows(yoyiToolbox.getItems_tif_common())
        
        self.itemTif_trans = QStandardItem("转换工具 (Raster Translation)")
        self.itemTif_trans.appendRows(yoyiToolbox.getItems_tif_trans())
        
        self.itemTif_cal = QStandardItem("计算工具 (Raster Calculator)")
        self.itemTif_cal.appendRows(yoyiToolbox.getItems_tif_cal())

        self.itemTif.appendRows([
            self.itemTif_common,
            self.itemTif_trans,
            self.itemTif_cal
        ])
        
        # 创建代理模型
        self.toolboxTreeProxyModel = QSortFilterProxyModel()
        self.toolboxTreeProxyModel.setSourceModel(self.toolboxTreeSourceModel)
        self.toolboxTreeProxyModel.setRecursiveFilteringEnabled(True)
        self.toolboxTreeProxyModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.toolboxTree.setModel(self.toolboxTreeProxyModel)
        
        self.toolboxTree.expandAll()
        self.toolboxTree.setHeaderHidden(True)
        self.toolboxTree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.toolboxTree.doubleClicked.connect(self.toolboxTreeDoubleClicked)

        # 3 设置图层树风格 建立图层树与地图画布的桥接
        #self.model = QgsLayerTreeModel(PROJECT.layerTreeRoot(), self)
        self.model = QgsLayerTreeModel(PROJECT.layerTreeRoot(), self)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeRename)  # 允许图层节点重命名
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)  # 允许图层拖拽排序
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)  # 允许改变图层节点可视性
        self.model.setFlag(QgsLayerTreeModel.ShowLegendAsTree)  # 展示图例
        self.model.setAutoCollapseLegendNodes(10)  # 当节点数大于等于10时自动折叠
        self.layerTreeView.setModel(self.model) # 图层树model设置
        self.layerTreeBridge = QgsLayerTreeMapCanvasBridge(PROJECT.layerTreeRoot(), self.mapCanvas, self)
        # 3.5 图层树上面的bar
        self.actionExpandAllNodes = Action(QIcon(":/img/resources/menu_expand.png"), '全部展开')
        self.actionExpandAllNodes.triggered.connect(self.layerTreeView.expandAllNodes)
        self.actionCollapseAllNodes = Action(QIcon(":/img/resources/menu_collapse.png"), '全部折叠')
        self.actionCollapseAllNodes.triggered.connect(self.layerTreeView.collapseAllNodes)
        self.actionDeleteLayer = Action(QIcon(":/img/resources/menu_close.png"), '移除选中图层')
        self.actionDeleteLayer.triggered.connect(self.deleteSelectedLayer)
        self.layerTreeCommandBar.addActions([
            self.actionExpandAllNodes,self.actionCollapseAllNodes,self.actionDeleteLayer
        ])
        # 4 刷新间隔
        #self.mapCanvas.setMapUpdateInterval(50)
        # 5 状态栏
        self.statusBar = QStatusBar(self)
        self.statusXY = BodyLabel('{:<40}'.format(''),self)  # x y 坐标状态
        self.statusBar.addWidget(self.statusXY, 1)
        self.statusCrsLabel = BodyLabel(self)
        self.statusScaleComboBox = ComboBox(self)
        self.statusScaleComboBox.setFixedWidth(120)
        self.statusScaleComboBox.addItems(
            ["1:500", "1:1000", "1:2500", "1:5000", "1:10000", "1:25000", "1:100000", "1:500000", "1:1000000"])
        #self.statusScaleComboBox.setEditable(True)
        self.statusBar.addWidget(self.statusScaleComboBox)
        self.statusBar.addWidget(self.statusCrsLabel)
        self.statusCrsLabel.setText(f"{self.parentWindow.yoyiTrans._translate('坐标系')}: {self.mapCanvas.mapSettings().destinationCrs().description()}-{self.mapCanvas.mapSettings().destinationCrs().authid()}")
        self.setStatusBar(self.statusBar)
        # 6 图层树右键菜单创建
        self.rightMenuProv = menuProvider(self,self.parentWindow.yoyiTrans)
        self.layerTreeView.setMenuProvider(self.rightMenuProv)
        # 7 一些初始状态
        self.firstAdd = True # 初始未加载图层，默认设定坐标系为4326 初始加载后，修改状态
        self.algoStateTipDict = {} #记录算法tip的字典
        self.stopSwipe = False #停止卷帘渲染
        self.currentProjectPath = None
        self.swipeLayersComboBox.hide() #初始隐藏卷帘图层
        self.SearchLineEdit.hide() #初始隐藏搜索图层
        self.editTempLayer = None
        self.editStack : QUndoStack = None

        # 9 允许拖拽文件触发事件
        self.setAcceptDrops(True)

        # 10 根据mode选择智能解译的运行方式
        self.inferSegButtonDict = {
            InferTypeName.Cropland : self.croplandSegPb,
            InferTypeName.Tree : self.treeSegPb,
            InferTypeName.Water : self.waterSegPb,
            InferTypeName.Building : self.buildingSegPb,
            InferTypeName.GreenHouse: self.greenHousePb,
            InferTypeName.DustNet: self.dustNetSegPb,
            InferTypeName.SteelTile: self.steelTileSegPb,
            InferTypeName.AgriculturalFilm: self.agriculturalFilmSegPb,
            InferTypeName.Road: self.roadSegPb,
        }
        self.inferDetecButtonDict = {
            InferTypeName.TowerCrane: self.towerCraneDetPb,
            InferTypeName.WindTurbine: self.windTurbineDetPb,
            InferTypeName.Stadium: self.stadiumDetPb,
            InferTypeName.ConstructionSite: self.constructionSiteDetPb,
            InferTypeName.Substation: self.substationDetPb,
            InferTypeName.ElectricTower: self.electricTowerDetPb
        }
        self.inferChangeDetecDict = {
            InferTypeName.Building: self.buildCDPb,
            InferTypeName.Cropland: self.croplandCDPb,
            InferTypeName.Tree: self.treeCDPb,
        }

        self.objectOutputPb.hide()
        self.excelTransLinePb.hide()

        self.segList = [InferTypeName.Cropland,InferTypeName.Road,
                            InferTypeName.DustNet,InferTypeName.SteelTile,
                            InferTypeName.Water,InferTypeName.Tree,InferTypeName.AgriculturalFilm,
                            InferTypeName.GreenHouse]
        self.insSegList = [InferTypeName.Building]
        self.detecList = [InferTypeName.Stadium,InferTypeName.TowerCrane,
                                InferTypeName.WindTurbine,InferTypeName.Substation,InferTypeName.ElectricTower]
        self.obbDetecList = [InferTypeName.ConstructionSite,InferTypeName.GreenHouse,InferTypeName.BrokenGH]
        self.cdBtnList = [InferTypeName.Building,InferTypeName.Cropland,InferTypeName.Tree]
        
        self.segBtnList = self.segList + self.insSegList
        self.detecBtnList = self.detecList + self.obbDetecList

        # 隐藏某些控件
        for segTypeName,segPb in self.inferSegButtonDict.items():
            if segTypeName not in self.segBtnList:
                segPb.hide()
        
        for detecTypeName,detecPb in self.inferDetecButtonDict.items():
            if detecTypeName not in self.detecBtnList:
                detecPb.hide()
        
        for cdTypeName,cdPb in self.inferChangeDetecDict.items():
            if cdTypeName not in self.cdBtnList:
                cdPb.hide()
    
    # 算法运行进度相关
    def refreshTips(self):
        for key,algoTip in self.algoStateTipDict.items():
            algoTip.move(algoTip.getSuitablePos())

    def algoTipClosed(self,key):
        self.algoStateTipDict.pop(key)
        self.refreshTips() 
    
    # 其他相关 如 拖拽等等
    def resizeEvent(self, a0, QResizeEvent=None):
        self.refreshTips()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, a0, QDropEvent=None):
        mimeData: QtCore.QMimeData = a0.mimeData()
        filePathList = [u.path()[1:] for u in mimeData.urls()]
        print(filePathList)
        for filePath in filePathList:
            if osp.isfile(filePath) and filePath.split(".")[-1] in ["tif", "TIF", "tiff", "TIFF", "GTIFF", "png", "jpg"]:
                self.addRasterLayer(filePath)
            elif osp.isfile(filePath) and filePath.split(".")[-1] in ["shp","gpkg"]:
                self.addVectorLayer(filePath)

    def actionStatsBarConnectFunc(self):
        self.mapCanvas.xyCoordinates.connect(self.showXY)
        self.mapCanvas.destinationCrsChanged.connect(self.showCrs)
        self.mapCanvas.scaleChanged.connect(self.showScale)
        self.statusScaleComboBox.currentTextChanged.connect(self.changeScaleForString)
        self.SearchLineEdit.searchSignal.connect(self.searchSignalTriggered)

    def showXY(self, point):
        x = point.x()
        y = point.y()
        self.statusXY.setText(f'{x:.6f}, {y:.6f}')

    def showScale(self, scale):
        self.statusScaleComboBox.setText(f"1:{int(scale)}")

    def showCrs(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        mapSetting : QgsMapSettings = self.mapCanvas.mapSettings()
        self.statusCrsLabel.setText(f"{yoyiTrs._translate('坐标系')}: {mapSetting.destinationCrs().description()}-{mapSetting.destinationCrs().authid()}")

    def changeScaleForString(self,str):
        try:
            left,right = str.split(":")[0],str.split(":")[-1]
            if int(left)==1 and int(right)>0 and int(right)!=int(self.mapCanvas.scale()):
                self.mapCanvas.zoomScale(int(right))
        except Exception as e:
            print(traceback.format_exc())

    def searchSignalTriggered(self,content:str):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        try:
            content = content.replace("，",",")
            splitList = content.split(",")
            if len(splitList) == 2:
                x,y = splitList[0],splitList[1]
                x = float(x)
                y = float(y)
                search_center = QgsPointXY(x,y)
                self.mapCanvas.setCenter(search_center)
                self.mapCanvas.refresh()
                self.mapCanvas.zoomScale(self.mapCanvas.scale() // 2)  
            else:
                MessageBox(yoyiTrs._translate('警告'), yoyiTrs._translate('输入格式非法'), self).exec_()
        except Exception as e:
            print(traceback.format_exc())
            MessageBox(yoyiTrs._translate('警告'), yoyiTrs._translate('输入格式非法'), self).exec_()
        

    def layerTreeConnectFunc(self):
        self.layerTreeView.doubleClicked.connect(self.doubelClickedLayerTree)
        self.layerTreeView.clicked.connect(self.clickedLayerTree)
    
    def clickedLayerTree(self):
        layer = self.layerTreeView.currentLayer()
        if layer is not None:
            if layer.type() == QgsMapLayerType.VectorLayer: # 如果是矢量图层 选择功能Enable 编辑功能有机会Enable
                self.selectFeatureMapToolPb.setEnabled(True) #选择功能Enable
                if self.editTempLayer == None or self.editTempLayer == layer: #若没有编辑中的图层或当前编辑图层是选中图层 编辑功能Enable
                    self.editShapefilePb.setEnabled(True)
                else:
                    self.editShapefilePb.setEnabled(False)
            else:
                self.selectFeatureMapToolPb.setEnabled(False)
                self.editShapefilePb.setEnabled(False)
        else:
            self.selectFeatureMapToolPb.setEnabled(False)
            self.editShapefilePb.setEnabled(False)
    
    def doubelClickedLayerTree(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        layer = self.layerTreeView.currentLayer()
        if layer is not None:
            if layer.type() == QgsMapLayerType.VectorLayer or layer.type() == QgsMapLayerType.RasterLayer:
                lp = widgets.LayerPropWindowWidgeter(layer, self.mapCanvas,self.parentWindow.yoyiTrans,parent=self)
                lp.show()
    
    def deleteLayer(self,layer,refresh=True):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        reply = MessageBox(yoyiTrs._translate('信息'),yoyiTrs._translate('确定要移除图层？'),self)
        reply.yesButton.setText(yoyiTrs._translate('确认'))
        reply.cancelButton.setText(yoyiTrs._translate('取消'))
        if reply.exec():
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
            PROJECT.removeMapLayer(layer)
            if refresh:
                self.mapCanvas.refresh()
        return 0

    def deleteSelectedLayer(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        layers = self.layerTreeView.selectedLayers()
        if len(layers) == 0:
            MessageBox(yoyiTrs._translate('信息'),yoyiTrs._translate('当前未选中图层'),self).exec()
            return
        reply = MessageBox(yoyiTrs._translate('信息'),yoyiTrs._translate('确定要移除图层？'),self)
        reply.yesButton.setText(yoyiTrs._translate('确认'))
        reply.cancelButton.setText(yoyiTrs._translate('取消'))
        if reply.exec():
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
            for layer in layers:
                PROJECT.removeMapLayer(layer)
            self.mapCanvas.refresh()
    
    def deleteAllLayer(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if len(PROJECT.mapLayers().values()) == 0:
            MessageBox(yoyiTrs._translate('信息'), yoyiTrs._translate('图层树为空'), self).exec_()
        else:
            reply = MessageBox(
                yoyiTrs._translate('信息'),
                yoyiTrs._translate('确定要移除所有图层？'),
                self
            )
            reply.yesButton.setText(yoyiTrs._translate('确认'))
            reply.cancelButton.setText(yoyiTrs._translate('取消'))
            if reply.exec():
                QApplication.processEvents()
                if self.mapCanvas.mapTool():
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
                PROJECT.clear()
                self.mapCanvas.refresh()

    def actionMapToolConnectFunc(self):
        self.panMapToolPb.clicked.connect(self.panMapToolPbClicked)
        self.zoomInMapToolPb.clicked.connect(self.zoomInMapToolPbClicked)
        self.zoomOutMapToolPb.clicked.connect(self.zoomOutMapToolPbClicked)
        self.scaelToFullExtentPb.clicked.connect(self.scaelToFullExtentPbClicked)
        self.lonlatSearchPb.clicked.connect(self.lonlatSearchPbClicked)

        self.newVectorLayerPb.clicked.connect(self.newVectorLayerPbClicked)
        self.saveEditPb.clicked.connect(self.saveEditPbClicked)

        self.undoPb.clicked.connect(self.undoPbClicked)
        self.redoPb.clicked.connect(self.redoPbClicked)

        self.selectFeatureMapToolPb.clicked.connect(self.selectFeatureMapToolPbClicked)
        self.editShapefilePb.clicked.connect(self.editShapefilePbClicked)
        self.polygonMapToolPb.clicked.connect(self.polygonMapToolPbClicked)
        self.splitMapToolPb.clicked.connect(self.splitMapToolPbClicked)
        self.editVertexMapToolPb.clicked.connect(self.editVertexMapToolPbClicked)
        self.reshapeMapToolPb.clicked.connect(self.reshapeMapToolPbClicked)
        self.mergeMapToolPb.clicked.connect(self.mergeMapToolPbClicked)
        self.deleteFeaturePb.clicked.connect(self.deleteFeaturePbClicked)
        self.changeFeatureAttributePb.clicked.connect(self.changeFeatureAttributePbClicked)

        self.measureDistanceMapToolPb.clicked.connect(self.measureDistanceMapToolPbClicked)
        self.measureAreaMapToolPb.clicked.connect(self.measureAreaMapToolPbClicked)
        
        # swipe 卷帘相关
        self.swipeMapTool = SwipeMapTool(self.swipeLayersComboBox,self.mapCanvas)
        self.preMapTool = None
        PROJECT.layerTreeRoot().layerOrderChanged.connect(self.updateSwipeCb)
        PROJECT.layerTreeRoot().visibilityChanged.connect(self.updateSwipeCb)
        PROJECT.layerTreeRoot().nameChanged.connect(self.updateSwipeCb)
        self.mapCanvas.mapToolSet.connect(self.mapCanvasMapToolSet)
        self.swipeTb.clicked.connect(self.swipeTbClicked)
        self.swipeTb.checkChanged.connect(self.swipeTbCheckChanged)
    
    def swipeTbCheckChanged(self):
        if self.swipeTb.isChecked():
            self.swipeLayersComboBox.show()
        else:
            self.swipeLayersComboBox.hide()

    def swipeTbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if self.swipeLayersComboBox.count() < 2:
            self.swipeTb.setChecked(False)
            MessageBox(yoyiTrs._translate("警告"), yoyiTrs._translate("至少需要两个图层!"), self).exec_()
            return
        self.swipeTb.setChecked(True)
        if self.mapCanvas.mapTool() != self.swipeMapTool:
            self.mapCanvas.setMapTool(self.swipeMapTool)
    
    def updateSwipeCb(self):
        if self.stopSwipe:
            return
        self.swipeLayersComboBox.clear()
        layers = PROJECT.layerTreeRoot().checkedLayers()
        for layer in layers:
            self.swipeLayersComboBox.addItem(layer.name(),userData=layer.id())
        self.swipeLayersComboBox.setCurrentIndex(0)
        if self.swipeLayersComboBox.count() < 2:
            self.swipeTb.setChecked(False)
            self.mapCanvas.unsetMapTool(self.swipeMapTool)
    
    def mapCanvasMapToolSet(self, newTool, _):
        if newTool.__class__.__name__ != 'SwipeMapTool':
            self.swipeTb.setChecked(False)
            try:
                if self.preMapTool == "SwipeMapTool":
                    self.mapCanvas.renderStarting.disconnect(self.renderStarting)
                    self.mapCanvas.renderComplete.disconnect(self.renderComplete)
            except Exception as e:
                print("mapCanvasMapToolSet 发生错误")
                pass
            self.preMapTool = None
        else:
            self.preMapTool = "SwipeMapTool"
            self.mapCanvas.renderStarting.connect(self.renderStarting)
            self.mapCanvas.renderComplete.connect(self.renderComplete)
        
    def renderStarting(self):
        self.mapCanvas.setCursor(Qt.BusyCursor)

    def renderComplete(self):
        cursor = self.mapCanvas.cursor()
        pos = cursor.pos()
        # 触发鼠标移动事件
        cursor.setPos(pos.x() + 1, pos.y() + 1)

    def panMapToolPbClicked(self):
        if self.panMapToolPb.isChecked():
            self.panMapTool = QgsMapToolPan(self.mapCanvas)
            self.mapCanvas.setMapTool(self.panMapTool)
            self.panMapTool.deactivated.connect(lambda: self.panMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == QgsMapToolPan:
                    self.panMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())

    def zoomInMapToolPbClicked(self):
        if self.zoomInMapToolPb.isChecked():
            self.zoomInMapTool = QgsMapToolZoom(self.mapCanvas, False)
            self.mapCanvas.setMapTool(self.zoomInMapTool)
            self.zoomInMapTool.deactivated.connect(lambda: self.zoomInMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())

    def zoomOutMapToolPbClicked(self):
        if self.zoomOutMapToolPb.isChecked():
            self.zommOutMapTool = QgsMapToolZoom(self.mapCanvas, True)
            self.mapCanvas.setMapTool(self.zommOutMapTool)
            self.zommOutMapTool.deactivated.connect(lambda: self.zoomOutMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
        
    def scaelToFullExtentPbClicked(self):
        self.mapCanvas.zoomToFullExtent()
    
    def lonlatSearchPbClicked(self):
        if self.lonlatSearchPb.isChecked():
            self.SearchLineEdit.show()
        else:
            self.SearchLineEdit.hide()
    
    # 撤回重做
    def undoPbClicked(self):
        if self.editStack != None and self.editStack.canUndo():
            self.editStack.undo()
            self.mapCanvas.refresh()
            self.updateShpUndoRedoButton()
    
    def redoPbClicked(self):
        if self.editStack != None and self.editStack.canRedo():
            self.editStack.redo()
            self.mapCanvas.refresh()
            self.updateShpUndoRedoButton()
        
    def updateShpUndoRedoButton(self):
        """
        动态更新撤销重做控件是否可用
        """
        if self.editStack != None:
            self.undoPb.setEnabled(self.editStack.canUndo())
            self.redoPb.setEnabled(self.editStack.canRedo())
        else:
            self.undoPb.setEnabled(False)
            self.redoPb.setEnabled(False)

    def selectFeatureMapToolPbClicked(self):
        if self.selectFeatureMapToolPb.isChecked():
            curLayer = self.layerTreeView.currentLayer()
            if not curLayer or curLayer.type() != QgsMapLayerType.VectorLayer:
                self.selectFeatureMapToolPb.setChecked(False)
                return
            self.selectFeatureMapTool = RecTangleSelectFeatureMapTool(self.mapCanvas,curLayer,self,True)
            self.mapCanvas.setMapTool(self.selectFeatureMapTool)
            self.selectFeatureMapTool.deactivated.connect(lambda: self.selectFeatureMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == RecTangleSelectFeatureMapTool:
                    self.selectFeatureMapTool.reset()
                    self.selectFeatureMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())

    def newVectorLayerPbClicked(self):
        resPath = QgsNewVectorLayerDialog.execAndCreateLayer(self,"",QgsCoordinateReferenceSystem('EPSG:4326'))[0]
        if osp.exists(resPath):
            self.addVectorLayer(resPath)
    
    # 点击开始编辑 显隐某些组件
    def changeEditingButtonStatus(self,status:bool):
        self.saveEditPb.setHidden(not status)
        self.undoPb.setHidden(not status)
        self.redoPb.setHidden(not status)
        self.polygonMapToolPb.setHidden(not status)
        self.editVertexMapToolPb.setHidden(not status)
        self.reshapeMapToolPb.setHidden(not status)
        self.splitMapToolPb.setHidden(not status)
        self.mergeMapToolPb.setHidden(not status)
        self.deleteFeaturePb.setHidden(not status)
        self.changeFeatureAttributePb.setHidden(not status)

    def editShapefilePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if self.editShapefilePb.isChecked():
            curLayer = self.layerTreeView.currentLayer()
            if not curLayer or curLayer.type() != QgsMapLayerType.VectorLayer:
                self.editShapefilePb.setChecked(False)
                return
            if QgsWkbTypes.displayString(curLayer.wkbType()) not in ['Polygon','MultiPolygon']:
                MessageBox(yoyiTrs._translate('信息'), yoyiTrs._translate('当前仅限编辑面矢量'), self).exec_()
                self.editShapefilePb.setChecked(False)
                return 

            self.editTempLayer : QgsVectorLayer = self.layerTreeView.currentLayer()
            self.editTempLayer.startEditing()
            self.editStack = self.editTempLayer.undoStack()
            self.changeEditingButtonStatus(True)

        else:
            if self.editTempLayer.isModified():
                saveQues = MessageBox(yoyiTrs._translate('保存编辑'),yoyiTrs._translate('确定要将编辑内容保存到内存吗？'),self)
                saveQues.yesButton.setText(yoyiTrs._translate('确认'))
                saveQues.cancelButton.setText(yoyiTrs._translate('取消'))
                if saveQues.exec():
                    self.editTempLayer.commitChanges(stopEditing=True)
                else:
                    self.editTempLayer.rollBack()
            else:
                self.editTempLayer.commitChanges(stopEditing=True)
            self.panMapToolPbClicked()
            self.editTempLayer = None
            self.editStack = None
            self.updateShpUndoRedoButton()
            self.changeEditingButtonStatus(False)
    
    def saveEditPbClicked(self):
        if not self.editTempLayer:
            return
        self.editTempLayer.commitChanges(stopEditing=False)

    def polygonMapToolPbClicked(self):
        if self.polygonMapToolPb.isChecked():
            if not self.editTempLayer:
                self.polygonMapToolPb.setChecked(False)
                return
            self.polygonMapTool = PolygonMapTool(self.mapCanvas,self.editTempLayer,self)
            self.mapCanvas.setMapTool(self.polygonMapTool)
            self.polygonMapTool.deactivated.connect(lambda: self.polygonMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == PolygonMapTool:
                    self.polygonMapTool.reset()
                    self.polygonMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
    
    def reshapeMapToolPbClicked(self):
        if self.reshapeMapToolPb.isChecked():
            if not self.editTempLayer:
                self.reshapeMapToolPb.setChecked(False)
                return
            self.reshapeMapTool = ReShapePolygonMapTool(self.mapCanvas,self.editTempLayer,self)
            self.mapCanvas.setMapTool(self.reshapeMapTool)
            self.reshapeMapTool.deactivated.connect(lambda: self.reshapeMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == ReShapePolygonMapTool:
                    self.reshapeMapTool.reset()
                    self.reshapeMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
    
    def splitMapToolPbClicked(self):
        if self.splitMapToolPb.isChecked():
            if not self.editTempLayer:
                self.splitMapToolPb.setChecked(False)
                return
            self.splitMapTool = SplitPolygonMapTool(self.mapCanvas,self.editTempLayer,self)
            self.mapCanvas.setMapTool(self.splitMapTool)
            self.splitMapTool.deactivated.connect(lambda: self.splitMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == SplitPolygonMapTool:
                    self.splitMapTool.reset()
                    self.splitMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
    
    def editVertexMapToolPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if self.editVertexMapToolPb.isChecked():
            if not self.editTempLayer:
                self.editVertexMapToolPb.setChecked(False)
                return
            if self.editTempLayer.crs().authid() != self.mapCanvas.mapSettings().destinationCrs().authid():
                MessageBox(yoyiTrs._translate('信息'), yoyiTrs._translate('编辑图层坐标系与地图画布坐标系不符，禁止使用顶点编辑'), self).exec_()
                self.editVertexMapToolPb.setChecked(False)
                return
            self.editVertexMapTool = EditVertexMapTool(self.mapCanvas,self.editTempLayer,self)
            self.mapCanvas.setMapTool(self.editVertexMapTool)
            self.editVertexMapTool.deactivated.connect(lambda: self.editVertexMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == EditVertexMapTool:
                    self.editVertexMapTool.reset()
                    self.editVertexMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
    
    def mergeMapToolPbClicked(self):
        if not self.editTempLayer:
            return
        if self.editTempLayer.selectedFeatureCount() >1:
            maxArea = -1
            maxAreaAttribute = None
            geom = None
            idList = []
            for feature in self.editTempLayer.selectedFeatures():
                idList.append(feature.id())
                tempArea = feature.geometry().area()
                if tempArea > maxArea:
                    maxArea = tempArea
                    maxAreaAttribute = feature.attributes()
                if geom == None:
                    geom = feature.geometry()
                else:
                    geom = geom.combine(feature.geometry())

            geom = makeValid_deleteAngle0(geom)
            if geom.type() == 2:
                self.editStack.beginMacro("mergeFeatures")
                self.editTempLayer.deleteFeatures(idList)
                feat = QgsFeature(self.editTempLayer.fields())
                feat.setAttributes(maxAreaAttribute)
                feat.setGeometry(geom)
                self.editTempLayer.addFeature(feat)
                self.editStack.endMacro()
                self.mapCanvas.refresh()
                self.updateShpUndoRedoButton()
            else:
                MessageBox('信息', "合并失败，矢量过于复杂", self).exec_()
                
    def deleteFeaturePbClicked(self):
        if not self.editTempLayer:
            return
        if self.editTempLayer.selectedFeatureCount() == 0:
            return 
        self.editStack.beginMacro("deleteFeature")
        self.editTempLayer.deleteSelectedFeatures()
        self.editStack.endMacro()
        self.updateShpUndoRedoButton()
    
    def changeFeatureAttributePbClicked(self):
        if not self.editTempLayer:
            return
        if self.editTempLayer.selectedFeatureCount() == 0:
            return 
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.AttrEditDialog(self.editTempLayer,yoyiTrs,self)
        dialog.exec()

    
    def measureDistanceMapToolPbClicked(self):
        if self.measureDistanceMapToolPb.isChecked():
            self.measureDistanceMapTool = MeasureDistanceMapTool(self.mapCanvas,self)
            self.mapCanvas.setMapTool(self.measureDistanceMapTool)
            self.measureDistanceMapTool.deactivated.connect(lambda: self.measureDistanceMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == MeasureDistanceMapTool:
                    self.measureDistanceMapTool.measureDialog.itemsClear()
                    self.measureDistanceMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
    
    def measureAreaMapToolPbClicked(self):
        if self.measureAreaMapToolPb.isChecked():
            self.measureAreaMapTool = MeasureAreaMapTool(self.mapCanvas,self)
            self.mapCanvas.setMapTool(self.measureAreaMapTool)
            self.measureAreaMapTool.deactivated.connect(lambda: self.measureAreaMapToolPb.setChecked(False))
        else:
            if self.mapCanvas.mapTool():
                if type(self.mapCanvas.mapTool()) == MeasureAreaMapTool:
                    self.measureAreaMapTool.measureDialog.itemClear()
                    self.measureAreaMapToolPb.setChecked(True)
                else:
                    self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())


    def actionOpenConnectFunc(self):
        # 打开项目 保存项目 等
        self.openProjectPb.clicked.connect(self.openProjectPbClicked)
        self.saveProjectPb.clicked.connect(self.saveProjectPbClicked)
        self.saveAsProjectPb.clicked.connect(self.saveAsProjectPbClicked)
        # 打开图层文件
        self.openRasterPb.clicked.connect(self.openRasterPbClicked)
        self.openShapeFilePb.clicked.connect(self.openShapeFilePbClicked)
        self.openXYZTilesPb.clicked.connect(self.openXYZTilesPbClicked)
    
    def openProjectPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        data_file, ext = QFileDialog.getOpenFileName(self, yoyiTrs._translate('打开'), '', 'project files(*.qgs , *.qgz)')
        if data_file:
            self.stopSwipe = True
            PROJECT.read(data_file)
            self.currentProjectPath = data_file
            self.parentWindow.setWindowTitle(f'{yoyiSetting().windowTitle} -- {os.path.basename(data_file)}')
            self.stopSwipe = False
            self.updateSwipeCb()

    def saveProjectPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if self.currentProjectPath != None:
            PROJECT.write()
        else:
            saveProject, ext = QFileDialog.getSaveFileName(self, yoyiTrs._translate('保存项目'), "", "qgz(*.qgz)")
            if saveProject != "":
                PROJECT.write(saveProject)
                self.currentProjectPath = saveProject
                self.parentWindow.setWindowTitle(f'{yoyiSetting().windowTitle} -- {os.path.basename(saveProject)}')
        
        MessageBox(yoyiTrs._translate('信息'), yoyiTrs._translate('保存成功'), self).exec_()
    
    def saveAsProjectPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        saveProject, ext = QFileDialog.getSaveFileName(self, yoyiTrs._translate('另存项目'), "", "qgz(*.qgz)")
        if saveProject != "":
            PROJECT.write(saveProject)
            self.currentProjectPath = saveProject
            self.parentWindow.setWindowTitle(f'{yoyiSetting().windowTitle} -- {os.path.basename(saveProject)}')
        MessageBox(yoyiTrs._translate('信息'), yoyiTrs._translate('保存成功'), self).exec_()

    def openRasterPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        file, ext = QFileDialog.getOpenFileName(self, yoyiTrs._translate('选择栅格影像'), "", 'Raster(*.tif;*.tiff;*.TIF;*.TIFF;*.png;*.PNG;*.jpg.;*.jpeg;*.JPG)')
        if file:
            self.addRasterLayer(file)

    def openShapeFilePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        file, ext = QFileDialog.getOpenFileName(self, yoyiTrs._translate('选择矢量文件'), '',"Vector(*.shp;*.SHP;*.gpkg)")
        if file:
            self.addVectorLayer(file)
    
    def openXYZTilesPbClicked(self):
        dialog = widgets.OpenXYZTilesDialogClass(self.parentWindow.yoyiTrans,self)
        dialog.exec()
        if dialog.layerName and dialog.wmsPath:
            self.addWmsLayer(dialog.layerName,dialog.wmsPath)
        dialog.deleteLater()


    # 添加栅格图层
    def addRasterLayer(self, rasterFilePath):
        rasterLayer = readRasterFile(rasterFilePath)
        layerRender = rasterLayer.renderer()
        layerRender.setAlphaBand(-1)
        print("layer band count")
        if rasterLayer.bandCount() == 4:
            layerRender.setRedBand(3)
            layerRender.setGreenBand(2)
            layerRender.setBlueBand(1)
        #rasterLayer.triggerRepaint()

        if self.firstAdd:
            addMapLayer(rasterLayer, self.mapCanvas,self.parentWindow.yoyiTrans, True,parent=self)
            self.firstAdd = False
        else:
            addMapLayer(rasterLayer, self.mapCanvas,self.parentWindow.yoyiTrans,parent=self)

    # 添加矢量图层
    def addVectorLayer(self, vectorFilePath):
        vectorLayer = readVectorFile(vectorFilePath)
        if self.firstAdd:
            addMapLayer(vectorLayer, self.mapCanvas,self.parentWindow.yoyiTrans, True,parent=self)
            self.firstAdd = False
        else:
            addMapLayer(vectorLayer, self.mapCanvas,self.parentWindow.yoyiTrans,parent=self)
    
    # 添加wms图层
    def addWmsLayer(self,layerName,wmsPath):
        wmsLayer = loadWmsasLayer(wmsPath,layerName)
        if self.firstAdd:
            addMapLayer(wmsLayer,self.mapCanvas,self.parentWindow.yoyiTrans,True,parent=self)
            self.firstAdd = False
        else:
            addMapLayer(wmsLayer,self.mapCanvas,self.parentWindow.yoyiTrans,parent=self)
    

    def actionCommonConnectFunc(self):
        # 其他
        self.supportPb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("http://www.jl1.cn/contact1.aspx")))
        self.jl1Pb.clicked.connect(self.jl1PbClicked)
        self.helpPb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(HELP_PDF)))
        self.createFishNetPb.clicked.connect(self.createFishNetPbClicked)
        self.jl1SitePb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.jl1mall.com")))
        self.saveAsImgPb.clicked.connect(self.saveAsImgPbClicked)

        self.jointLabelingPb.clicked.connect(self.jointLabelingPbClicked)
    def jl1PbClicked(self):
        dialog = widgets.JL1FreeXYZTilesDialogClass(self)
        dialog.exec()
        if dialog.layerName and dialog.wmsPath:
            self.addWmsLayer(dialog.layerName,dialog.wmsPath)
        dialog.deleteLater()
    
    def createFishNetPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.CreateFishNetDialogClass(yoyiTrs,self)
        dialog.exec()

        if dialog.runMode:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('创建渔网')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()
            if dialog.runMode == "group":
                setattr(self, tempThreadObjName,yoyiThread.createFishNetRunClass(dialog.tifPath,dialog.fishNetSize,dialog.resPath,extent=dialog.groupExtent))
            elif dialog.runMode == "tif":
                setattr(self, tempThreadObjName,yoyiThread.createFishNetRunClass(dialog.tifPath,dialog.fishNetSize,dialog.resPath))
            else:
                setattr(self,tempThreadObjName,yoyiThread.createFishNetByXYIntervalRunClass(dialog.xyCrs,dialog.xyExtent,dialog.resPath,dialog.xyXNum,dialog.xyYNum))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()

    def saveAsImgPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if len(PROJECT.mapLayers()) == 0:
            MessageBox(yoyiTrs._translate("信息"), yoyiTrs._translate("图层树为空"), self).exec_()
            return 
        saveImg, ext = QFileDialog.getSaveFileName(self, yoyiTrs._translate("截图当前画布至图像"), "", "png(*.png);;jpg(*.jpg)")
        if saveImg != "":
            self.mapCanvas.saveAsImage(saveImg)
            MessageBox(yoyiTrs._translate("信息"), yoyiTrs._translate("保存成功"), self).exec_()

    def jointLabelingPbClicked(self):
        try:
            subprocess.Popen([JOINT_LABEL_CMD],creationflags=subprocess.DETACHED_PROCESS)
        except Exception as e:
            pass
    
    def toolboxSearchLineEditUpdateFilter(self):
        filterText = self.toolboxSearchLineEdit.text()
        self.toolboxTreeProxyModel.setFilterRegExp(filterText)
        self.toolboxTree.update()  # 手动刷新TreeWidget以显示新的过滤后的数据
        self.toolboxTree.expandAll()
    
    def toolboxTreeDoubleClicked(self, index: QModelIndex):
        data = index.data(Qt.ItemDataRole.UserRole)
        if not (type(data) == dict and "ID" in data.keys()):
            return
        
        id = data["ID"]
        if not (id in yoyiToolbox.toolboxIdDict.keys()):
            return
        
        toolboxProcessing = yoyiToolbox.toolboxIdDict[id]
        exec(f"self.{toolboxProcessing}()")
    
    def actionTifProcessConnectFunc(self):
        self.raster2ShpPb.clicked.connect(self.raster2ShpPbClicked)
        self.rasterRecombinePb.clicked.connect(self.rasterRecombinePbClicked)
        self.rasterExportPb.clicked.connect(self.rasterExportPbClicked)
        self.raster16to8Pb.clicked.connect(self.raster16to8PbClicked)
        self.rasterBuildOverviewPb.clicked.connect(self.rasterBuildOverviewPbClicked)
        self.rasterClipPb.clicked.connect(self.rasterClipPbClicked)
        self.rasterReprojectPb.clicked.connect(self.rasterReprojectPbClicked)
        self.rasterMergePb.clicked.connect(self.rasterMergePbClicked)
        self.rasterCalcPb.clicked.connect(self.rasterCalcPbClicked)
        # self.rasterZonalStaticPb.clicked.connect(self.rasterZonalStaticPbClicked)
    def raster2ShpPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.Raster2ShpDialog(yoyiTrs,self.parentWindow)
        dialog.exec()
        if dialog.inputFileList and dialog.fieldName and dialog.use8Connect and dialog.postName and dialog.saveDir:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格转矢量')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.raster2ShpBatchRunClass(dialog.inputFileList, dialog.saveDir, dialog.fieldName, dialog.postName, rts8Connect=dialog.use8Connect))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterRecombinePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.TifRecombineDialog(yoyiTrs,self.parentWindow)
        dialog.exec()
        if dialog.resPath and dialog.tifPath and dialog.recombineList:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格重排波段')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterRecombineRunClass(dialog.tifPath,dialog.recombineList,dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterExportPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.TifExportDialog(yoyiTrs,self.parentWindow)
        dialog.exec()
        if dialog.resPath and dialog.tifPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格导出')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterExportRunClass(dialog.tifPath,dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def raster16to8PbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.Raster16to8Dialog(yoyiTrs,self.parentWindow)
        dialog.exec()
        if dialog.saveDir:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格降位')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.raster16to8BatchRunClass(dialog.inputFileList,dialog.saveDir,dialog.clipPercent,dialog.postName))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterBuildOverviewPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.TifBuildOverviewDialog(yoyiTrs,self.parentWindow)
        dialog.exec()
        if dialog.tifPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格构建金字塔')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterBuildOverviewRunClass(dialog.tifPath,dialog.buildIn,dialog.clean))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterClipPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.RasterClipDialogClass(yoyiTrs,self)
        dialog.isReady.connect(self.rasterClipIsReady)
        dialog.show()
        
    def rasterClipIsReady(self,params:list):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        runMode,tifPath,resPath,extent,maskPath,expandMask = params
        tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
        stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格裁剪')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
        stateTooltip.move(stateTooltip.getSuitablePos())
        stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
        stateTooltip.show()
        if runMode == "extent":
            setattr(self, tempThreadObjName,yoyiThread.rasterClipByExtentRunClass(tifPath,resPath,extent))
        else:
            setattr(self, tempThreadObjName,yoyiThread.rasterClipByMaskRunClass(tifPath,resPath,maskPath,expandMask))
        self.algoStateTipDict[tempThreadObjName] = stateTooltip
        exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
        exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
        exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
        exec(f"self.{tempThreadObjName}.start()")

    
    def rasterReprojectPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.RasterReprojectDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.tifPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格重投影')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterReprojectRunClass(dialog.tifPath,dialog.resPath,dialog.targetCrs,dialog.resampleMode))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterMergePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.RasterMergeDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.tifList:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格合并')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterMergeRunClass(dialog.tifList,dialog.resampleIndex,dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterCalcPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        curLayer = self.layerTreeView.currentLayer()
        if not curLayer or curLayer.type() != QgsMapLayerType.RasterLayer:
            MessageBox(yoyiTrs._translate('警告'), yoyiTrs._translate('未选中栅格图层'), self).exec_() 
            return
        dialog = widgets.RasterCalcDialogClass(yoyiTrs,curLayer,parent=self)
        dialog.exec()
        if dialog.expression:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格计算器')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterCalcRunClass(dialog.expression,dialog.resPath,dialog.format,dialog.extent,dialog.crs,dialog.outWidth,dialog.outHeight,dialog.rasterCalcEntryList))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def rasterZonalStaticPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.RasterZonalStaticDialog(yoyiTrs,self)
        dialog.exec()
        if dialog.inputFile:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('栅格分区统计')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.rasterZonalStaticRunClass(dialog.inputFile,dialog.inputShp,dialog.saveFile))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def actionInferConnectFunc(self):
        self.croplandSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.Cropland))
        self.buildingSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.InstanceSegmentation,InferTypeName.Building))
        self.roadSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.Road))
        self.dustNetSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.DustNet))
        self.steelTileSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.SteelTile))
        
        self.waterSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.Water))
        self.treeSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.Tree))
        self.agriculturalFilmSegPb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.AgriculturalFilm))

        self.towerCraneDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.Detection,InferTypeName.TowerCrane))
        self.constructionSiteDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.ObbDetection,InferTypeName.ConstructionSite))

        self.stadiumDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.Detection,InferTypeName.Stadium))
        self.windTurbineDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.Detection,InferTypeName.WindTurbine))
        self.substationDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.Detection,InferTypeName.Substation))
        self.electricTowerDetPb.clicked.connect(lambda: self.detecInferPbClicked(InferType.Detection,InferTypeName.ElectricTower))

        self.buildCDPb.clicked.connect(lambda: self.changeDetecInferPbClicked(InferType.ChangeDection,InferTypeName.Building))
        self.treeCDPb.clicked.connect(lambda: self.changeDetecInferPbClicked(InferType.ChangeDection,InferTypeName.Tree))
        self.croplandCDPb.clicked.connect(lambda: self.changeDetecInferPbClicked(InferType.ChangeDection,InferTypeName.Cropland))

        self.greenHousePb.clicked.connect(lambda : self.segInferPbClicked(InferType.Segmentation,InferTypeName.GreenHouse))
        # custom 
        self.batchInferPb.clicked.connect(self.batchInferPbClicked)
        self.customizeSegPb.clicked.connect(self.customizeSegPbClicked)
        #dataset
        self.createDatasetPb.clicked.connect(self.createDatasetPbClicked)
        self.splitDatasetPb.clicked.connect(self.splitDatasetPbClicked)
        self.trainToolPb.clicked.connect(self.trainToolPbClicked)

    def batchInferPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return

    def customizeSegPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return

    def segInferPbClicked(self,inferType:InferType,typeName:InferTypeName):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return
        dialog = widgets.InferSegDialog(self.parentWindow.yoyiTrans,inferType,typeName,self.parentWindow)
        dialog.exec()

    def detecInferPbClicked(self,inferType:InferType,typeName:InferTypeName):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return

    def changeDetecInferPbClicked(self,inferType:InferType,typeName:InferTypeName):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return
        dialog = widgets.InferChangeDetecDialog(yoyiTrs,inferType,typeName,self)
        dialog.isReady.connect(self.changeDetecIsReady)
        dialog.show()

    def changeDetecIsReady(self,params:list):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        tifPath,tifIIPath,saveDir,postName,typeName,imgSize,batchSize,overlap,tolerance,removeArea,removeHole,gpuId,extraExtent = params

    def createDatasetPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.GenerateDatasetDialogClass(yoyiTrs,self)
        dialog.exec()
        
        if dialog.resDir:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('创建数据集')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            if dialog.LCRb.isChecked():
                setattr(self, tempThreadObjName,yoyiThread.createCgwxSegmentSample(tifPathList=dialog.tifPathList,
                                                                               resDir=dialog.resDir,
                                                                               shpPathList=dialog.shpPathList,
                                                                               needTransRgb=dialog.needTransRgb,
                                                                               overlap=dialog.overlap,
                                                                               imgSize=dialog.imgSize,
                                                                               dropZero=dialog.dropZero,
                                                                               generatePost=dialog.generatePost,
                                                                               shpField=dialog.shpField,
                                                                               shpPixelMapping=dialog.shpPixelMapping,
                                                                               diyPixelValue=dialog.diyPixelValue,
                                                                               classDict=dialog.classDict,
                                                                               mosaicShp=dialog.mosaicShp,
                                                                               mosaicShpImgidField=dialog.mosaicShpImgidField,
                                                                               imgIdTime=dialog.imgIdTime,
                                                                               sampleName=dialog.sampleName,
                                                                               sampleDescription=dialog.sampleDescription,
                                                                               sampleBuilder=dialog.sampleBuilder,
                                                                               imageAreaId=dialog.imageAreaId,
                                                                               filePre=dialog.filePre,
                                                                               initIndex=dialog.initIndex))
            elif dialog.ODRb.isChecked():
                setattr(self, tempThreadObjName,yoyiThread.createCgwxODSample(tifPathList=dialog.tifPathList,
                                                                              resDir=dialog.resDir,
                                                                              shpPathList=dialog.shpPathList,
                                                                              needTransRgb=dialog.needTransRgb,
                                                                              overlap=dialog.overlap,
                                                                              imgSize=dialog.imgSize,
                                                                              generatePost=dialog.generatePost,
                                                                              shpField=dialog.shpField,
                                                                              shpPixelMapping=dialog.shpPixelMapping,
                                                                              classDict=dialog.classDict,
                                                                              mosaicShp=dialog.mosaicShp,
                                                                              mosaicShpImgidField=dialog.mosaicShpImgidField,
                                                                              imgIdTime=dialog.imgIdTime,
                                                                              sampleName=dialog.sampleName,
                                                                              sampleDescription=dialog.sampleDescription,
                                                                              sampleBuilder=dialog.sampleBuilder,
                                                                              imageAreaId=dialog.imageAreaId,
                                                                              isObb=dialog.isObb,
                                                                              clipMinAreaPer=dialog.clipMinAreaPer,
                                                                              filePre=dialog.filePre,
                                                                              initIndex=dialog.initIndex
                                                                              ))
            elif dialog.CDRb.isChecked():
                setattr(self, tempThreadObjName,yoyiThread.createCgwxCDSample(tifPathList=dialog.tifPathList,
                                                                              tifPathListII=dialog.tifPathListII,
                                                                              resDir=dialog.resDir,
                                                                              shpPathList=dialog.shpPathList,
                                                                              needTransRgb=dialog.needTransRgb,
                                                                              overlap=dialog.overlap,
                                                                              imgSize=dialog.imgSize,
                                                                              dropZero=dialog.dropZero,
                                                                              generatePost=dialog.generatePost,
                                                                              shpField=dialog.shpField,
                                                                              shpFieldII=dialog.shpFieldII,
                                                                              shpPixelMapping=dialog.shpPixelMapping,
                                                                              diyPixelValue=dialog.diyPixelValue,
                                                                              classDict=dialog.classDict,
                                                                              mosaicShp=dialog.mosaicShp,
                                                                              mosaicShpII=dialog.mosaicShpII,
                                                                              mosaicShpImgidField=dialog.mosaicShpImgidField,
                                                                              mosaicShpImgidFieldII=dialog.mosaicShpImgidFieldII,
                                                                              imgIdTime=dialog.imgIdTime,
                                                                              imgIdTimeII=dialog.imgIdTimeII,
                                                                              sampleName=dialog.sampleName,
                                                                              sampleDescription=dialog.sampleDescription,
                                                                              sampleBuilder=dialog.sampleBuilder,
                                                                              imageAreaId=dialog.imageAreaId,
                                                                              filePre=dialog.filePre,
                                                                              initIndex=dialog.initIndex
                                                                              ))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    
    def splitDatasetPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.SplitDatasetDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resDirPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('划分数据集')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.splitDatasetRunClass(
                imgDir=dialog.imgDirPath,
                labelDir=dialog.labelDirPath,
                imgDirPost=dialog.imgDirPost,
                labelDirPost=dialog.labelDirPost,
                resDir=dialog.resDirPath,
                validRatio=dialog.validRatio,
                testRatio=dialog.testRatio,
                shuffleOrder=dialog.shuffle,
                trainDirName=dialog.trainSetDirName,
                validDirName=dialog.validSetDirName,
                testDirName=dialog.testSetDirName,
                imageDirName=dialog.imgDirName,
                labelDirName=dialog.labelDirName
            ))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()

    
    def trainToolPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        if not GPUENABLE:
            MessageBox('信息', yoyiTrs._translate("当前软件未搜寻到本地模型"), self.parentWindow).exec_()
            return
        dialog = widgets.OpenTrainToolDialogClass(yoyiTrs,self)
        dialog.exec()
        
    def actionShpProcessConnectFunc(self):
        self.shp2RasterPb.clicked.connect(self.shp2RasterPbClicked)
        self.shpExportPb.clicked.connect(self.shpExportPbClicked)
        self.shpClipPb.clicked.connect(self.shpClipPbClicked)
        self.shpErasePb.clicked.connect(self.shpErasePbClicked)
        self.shpBufferPb.clicked.connect(self.shpBufferPbClicked)
        self.shpInterPb.clicked.connect(self.shpInterPbClicked)
        self.shpOrthPb.clicked.connect(self.shpOrthPbClicked)
        self.shpCalCentroidPb.clicked.connect(self.shpCalCentroidPbClicked)
        self.shpCalAreaPb.clicked.connect(self.shpCalAreaPbClicked)
        self.shpDissolvePb.clicked.connect(self.shpDissolvePbClicked)
        self.shp2SinglePb.clicked.connect(self.shp2SinglePbClicked)
        self.shpMergePb.clicked.connect(self.shpMergePbClicked)
        self.shpRemoveSmallPb.clicked.connect(self.shpRemoveSmallPbClicked)
        self.shpChangeAnalysisPb.clicked.connect(self.shpChangeAnalysisPbClicked)
    
    def shp2RasterPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.Shp2RasterDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.shpPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量转栅格')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shp2RasterRunClass(dialog.shpPath,
                                                                          dialog.fieldName,
                                                                          dialog.pixelWidth,
                                                                          dialog.pixelHeight,
                                                                          dialog.dataType,
                                                                          dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpExportPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpExportDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量导出')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpExportRunClass(shpLayerName=dialog.shpLayerName,
                                                                         targetCrs=dialog.targetCrs,
                                                                         onlyExportSelected=dialog.onlyExportSelected,
                                                                         encoding=dialog.encoding,
                                                                         resPath=dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpFixPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpFixGeometryDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.saveDir:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量几何修复')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shapeFileFixGeometryRunClass(shpList=dialog.inputFileList,
                                                                                    resDir=dialog.saveDir,
                                                                                    postName=dialog.postName))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpClipPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpClipDialogClass(yoyiTrs,self)
        dialog.isReady.connect(self.shpClipPbIsReady)
        dialog.show()
    
    def shpClipPbIsReady(self,params:list):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        runMode,shpPath,resPath,extent,maskPath = params
        print(runMode,shpPath,resPath,extent,maskPath)
        
        tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
        stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量裁剪')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
        stateTooltip.move(stateTooltip.getSuitablePos())
        stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
        stateTooltip.show()
        if runMode == "extent":
            setattr(self, tempThreadObjName,yoyiThread.shpClipByExtentRunClass(shpPath=shpPath,
                                                                               resPath=resPath,
                                                                               extent=extent))
        else:
            setattr(self, tempThreadObjName,yoyiThread.shpClipByMaskRunClass(shpPath=shpPath,
                                                                             resPath=resPath,
                                                                             maskPath=maskPath))
        self.algoStateTipDict[tempThreadObjName] = stateTooltip
        exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
        exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
        exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
        exec(f"self.{tempThreadObjName}.start()")
    
    def shpErasePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpEraseDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量相减')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpEraseRunClass(shpPath=dialog.shpPath,
                                                                        resPath=dialog.resPath,
                                                                        erasePath=dialog.erasePath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()

    def shpSimplyPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpSimplyDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量简化')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpSimplyRunClass(shpPath=dialog.shpPath,
                                                                         resPath=dialog.resPath,
                                                                         tolerance=dialog.tolerance))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpBufferPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpBufferDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量缓冲')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpBufferRunClass(shpPath=dialog.shpPath,
                                                                         resPath=dialog.resPath,
                                                                         distance=dialog.distance,
                                                                         segments=dialog.segments,
                                                                         endStyle=dialog.endStyle,
                                                                         joinStyle=dialog.joinStyle,
                                                                         miterLimit=dialog.miterLimit,
                                                                         dissolve=dialog.dissolve))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpInterPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpIntersectionDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量相交')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpIntersectionRunClass(shpPath=dialog.shpPath,
                                                                               resPath=dialog.resPath,
                                                                               intersectShp=dialog.intersectShp,
                                                                               prefix=dialog.prefix))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpOrthPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpOrthogoDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量正交')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpOrthogoRunClass(shpPath=dialog.shpPath,
                                                                          resPath=dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpCalCentroidPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpCalCentroidDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量计算质心')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpCalCentroidRunClass(shpPath=dialog.shpPath,
                                                                              resPath=dialog.resPath,
                                                                              allPart=dialog.allPart))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpCalAreaPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpCalAreaDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量面积计算')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpCalAreaRunClass(shpPath=dialog.shpPath,
                                                                          resPath=dialog.resPath,
                                                                          fieldName=dialog.fieldName,
                                                                          fieldLength=dialog.fieldLength,
                                                                          fieldPrecision=dialog.fieldPrecision))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpDissolvePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpDissolveDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量融合')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpDissolveRunClass(shpPath=dialog.shpPath,
                                                                           resPath=dialog.resPath,
                                                                           fields=dialog.fields))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shp2SinglePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpSinglepartsDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量转单部件')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shp2SinglepartsRunClass(shpPath=dialog.shpPath,
                                                                               resPath=dialog.resPath))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpSmoothPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpSmoothDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量平滑')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpSmoothRunClass(shpPath=dialog.shpPath,
                                                                         resPath=dialog.resPath,
                                                                         iterNum=dialog.iterNum,
                                                                         offset=dialog.offset,
                                                                         maxAngle=dialog.maxAngle))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpMergePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpMergeDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.shpList:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量合并')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpMergeRunClass(shpList=dialog.shpList,
                                                                        resPath=dialog.resPath,
                                                                        crs=dialog.crs))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()

    def shpReprojectPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpReprojectDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量转换投影')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpReprojectRunClass(shpPath=dialog.shpPath,
                                                                            resPath=dialog.resPath,
                                                                            targetCrs=dialog.targetCrs))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpRemoveSmallPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpRemoveAreaDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量碎斑过滤')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpRemoveAreaRunClass(shpPath=dialog.shpPath,
                                                                             resPath=dialog.resPath,
                                                                             minArea=dialog.minArea))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpFillHolePbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpDeleteholesDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量孔洞填充')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpDeleteholesRunClass(shpPath=dialog.shpPath,
                                                                              resPath=dialog.resPath,
                                                                              minArea=dialog.minArea))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()
    
    def shpChangeAnalysisPbClicked(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        dialog = widgets.ShpChangeAnalysisDialogClass(yoyiTrs,self)
        dialog.exec()
        if dialog.resPath:
            tempThreadObjName = "Thread_" + datetime.now().strftime('%m%d%H%M%S')
            stateTooltip = widgets.YoyiStateToolTip(f"{yoyiTrs._translate('矢量变化分析')} {yoyiTrs._translate('开始')}：{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", yoyiTrs._translate('运行中'),yoyiTrs, self)
            stateTooltip.move(stateTooltip.getSuitablePos())
            stateTooltip.closedSignal.connect(lambda : self.algoTipClosed(tempThreadObjName))
            stateTooltip.show()

            setattr(self, tempThreadObjName,yoyiThread.shpChangeAnalysisRunClass(preShpPath=dialog.preShpPath,
                                                                                 lastShpPath=dialog.lastShpPath,
                                                                                 resPath=dialog.resPath,
                                                                                 tempDir=self.TEMPDIR,
                                                                                 ))
            self.algoStateTipDict[tempThreadObjName] = stateTooltip
            exec(f"self.{tempThreadObjName}.signal_process.connect(stateTooltip.changeStateProcess)")
            exec(f"self.{tempThreadObjName}.signal_over.connect(stateTooltip.stateEnd)")
            exec(f"self.{tempThreadObjName}.finished.connect(self.{tempThreadObjName}.deleteLater)")
            exec(f"self.{tempThreadObjName}.start()")
        dialog.deleteLater()