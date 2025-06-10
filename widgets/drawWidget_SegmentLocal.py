import os
import os.path as osp
import requests
import random
import time
from ui.segmentWorkDrawWindow_Local import Ui_SegDrawWindow
from PyQt5.QtCore import QVariant,QStringListModel,QCoreApplication
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout,QWidget,QAbstractItemView,QMenu, QAction,QUndoStack,QMainWindow,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsLayerTreeModel,QgsRectangle,QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsPalLayerSettings,QgsVectorLayerSimpleLabeling,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry
from qgis.gui import QgsLayerTreeMapCanvasBridge,QgsLayerTreeView,QgsMessageBar,QgsMapToolIdentifyFeature,QgsMapCanvas,QgsMapToolPan
import traceback

from qfluentwidgets import MessageBox,SubtitleLabel,setFont,ToolTipFilter

from appConfig import *

from widgets.projectListDialog import LocalProjectListDialogClass
from widgets.draw_dialog_createSegProject  import SegDrawCreateProjectDialogClass
from widgets.draw_dialog_multiBandTifRenderWindow import multiBandTifAttrWindowClass
from widgets.draw_dialog_pixelClassifyMapWindow import PixelClassifyMapWindowClass
from widgets.draw_dialog_spectralCurveDialog import SpectralCurveWindowClass
from widgets.layerPropWindowWidget import LayerPropWindowWidgeter

from yoyiUtils.maptool_utils import makeValid_deleteAngle0
from yoyiUtils.custom_maptool import *
from yoyiUtils.custom_widget import YoyiTreeLayerWidget,BetterPillToolButton
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import readYamlToDict,checkAllFileList,saveSampleWorkYaml,readYamlToList,deleteDir,deleteNameTagging,makeFileUnique
from yoyiUtils.qgisLayerUtils import getFIDlist
from yoyiUtils.qgisFunction import saveShpFunc,createFishNetByXYInterval
from yoyiUtils.yoyiDialogThread import updateDataSetRunClass,pixelClsfyRunClass
from yoyiUtils.yoyiTranslate import yoyiTrans
try:
    from yoyiUtils.yoyiSamLocal import SegAnyMapTool
except Exception as e:
    pass

PROJECT = QgsProject.instance()

class DrawWidgetSegmentLocalWindowClass(Ui_SegDrawWindow,QMainWindow):
    def __init__(self, parent=None):
        super(DrawWidgetSegmentLocalWindowClass, self).__init__(parent)
        self.parentWindow = parent
        self.setting = yoyiSetting()
        self.spMapCanvas = None
        self.setupUi(self)
        self.setupDIYUI()
 
        self.dockWidgetTop.setTitleBarWidget(QWidget(self))

        self.emptyLabel = SubtitleLabel("请点击右上角↗创建项目",self)
        self.emptyLabel.setAlignment(Qt.AlignCenter)
        setFont(self.emptyLabel, 35)
        self.hl = QHBoxLayout(self.frame)
        self.hl.setContentsMargins(0, 0, 0, 0)
        self.hl.addWidget(self.emptyLabel)

        # yoyiTrans
        self.yoyiTrs = self.parentWindow.yoyiTrans
        
        # mapcanvas
        self.spMapCanvas : QgsMapCanvas = QgsMapCanvas(self)
    

        self.hl.addWidget(self.spMapCanvas)
        self.spMapCanvas.hide()

        # 左侧图层树
        vl = QVBoxLayout(self.dockWidgetContentsLeft)
        self.layerTree = YoyiTreeLayerWidget(self.spMapCanvas,self.yoyiTrs,self)
        self.layerTree.treeChanged.connect(self.updateMapcanvasLayers)
        self.layerTree.itemChanged.connect(self.updateMapcanvasLayers)
        vl.addWidget(self.layerTree)

        # 进度条
        self.ProgressBar.hide()

        self.controlList = [
            # 上面
            self.addGuideLayer,self.xSpinBox,self.ySpinBox,
            self.changeFishNet,self.createExtentPb,self.checkFeatureCountPb,
            # 右边上部分
            self.pixelClsfyPb,self.openSpectralCurvePb,self.panMapToolPb,
            self.magicMapToolPb,self.polygonMapToolPb,self.rectangleMapToolPb,
            self.circleMapToolPb,self.selectMapToolPb,self.deleteFeaturePb,
            self.rotateMapToolPb,self.rescaleMapToolPb,self.mergeMapToolPb,self.changeAttrPb,
            self.pasteMapToolPb,self.vertexMapToolPb,self.reshapeMapToolPb,
            self.splitMapToolPb,self.fillHoleMapToolPb,
            # 右边下部分
            self.lastPb,self.nextPb,self.undoPB,self.redoPB,self.commitMagicPB,
            self.reSizeExtent,self.saveWorkPb,self.exportShpPb
        ]

        self.changeEnables(False)
        self.setObjectName("Window_Draw_Segment_Local")
        self.firstLoad = True
        self.workDir = None
        self.scpDialog = None

        # 地图工具
        self.delMapTool()
        
        self.projectConnectFunc() # 项目相关
        self.topBarConnectFunc()
        self.mapToolConnectFunc() # 地图工具
        self.rightBarConnectFunc()
    
    def setupDIYUI(self):
        # qewrt
        self.panMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.panMapToolPb.setIcon(QIcon(':/img/resources/gis/gis_pan.png'))
        self.panMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.panMapToolPb.setToolTip('Pan (Q) Drag the Map Canvas to Move')
        self.panMapToolPb.installEventFilter(ToolTipFilter(self.panMapToolPb,0))
        self.panMapToolPb.setShortcut("Q")
        self.hl_qwer.addWidget(self.panMapToolPb)

        self.magicMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.magicMapToolPb.setIcon(QIcon(':/img/resources/infer/clsfy_magic.png'))
        self.magicMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.magicMapToolPb.setToolTip('Magic Wand (W) Intelligently Extracts Contours')
        self.magicMapToolPb.installEventFilter(ToolTipFilter(self.magicMapToolPb,0))
        self.magicMapToolPb.setShortcut("W")
        self.hl_qwer.addWidget(self.magicMapToolPb)

        self.polygonMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.polygonMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_polygon.png'))
        self.polygonMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.polygonMapToolPb.setToolTip('Draw Feature Tool (E) Double Click to Open Stream Mode, Single Click to Close')
        self.polygonMapToolPb.installEventFilter(ToolTipFilter(self.polygonMapToolPb,0))
        self.polygonMapToolPb.setShortcut("E")
        self.hl_qwer.addWidget(self.polygonMapToolPb)

        self.rectangleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rectangleMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_rectangle.png'))
        self.rectangleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rectangleMapToolPb.setToolTip('Draw Rectangle Feature Tool (R)')
        self.rectangleMapToolPb.installEventFilter(ToolTipFilter(self.rectangleMapToolPb,0))
        self.rectangleMapToolPb.setShortcut("R")
        self.hl_qwer.addWidget(self.rectangleMapToolPb)

        self.circleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.circleMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_circle.png'))
        self.circleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.circleMapToolPb.setToolTip('Draw Circle Feature Tool (T)')
        self.circleMapToolPb.installEventFilter(ToolTipFilter(self.circleMapToolPb,0))
        self.circleMapToolPb.setShortcut("T")
        self.hl_qwer.addWidget(self.circleMapToolPb)

        #asdfg
        self.lastPb = BetterPillToolButton(self.dockWidgetContents)
        self.lastPb.setIcon(QIcon(':/img/resources/last.png'))
        self.lastPb.setIconSize(QtCore.QSize(30,30))
        self.lastPb.setToolTip('last fishnet (A)')
        self.lastPb.installEventFilter(ToolTipFilter(self.lastPb,0))
        self.lastPb.setShortcut("A")
        self.lastPb.setCheckable(False)
        self.hl_asdf.addWidget(self.lastPb)

        self.selectMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.selectMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_select_multi.png'))
        self.selectMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.selectMapToolPb.setToolTip('Select Feature Tool (S) Drag to Move the Selected Feature, Right Click for Menu Bar')
        self.selectMapToolPb.installEventFilter(ToolTipFilter(self.selectMapToolPb,0))
        self.selectMapToolPb.setShortcut("S")
        self.hl_asdf.addWidget(self.selectMapToolPb)

        self.nextPb = BetterPillToolButton(self.dockWidgetContents)
        self.nextPb.setIcon(QIcon(':/img/resources/next.png'))
        self.nextPb.setIconSize(QtCore.QSize(30,30))
        self.nextPb.setToolTip('next fishnet (D)')
        self.nextPb.installEventFilter(ToolTipFilter(self.nextPb,0))
        self.nextPb.setShortcut("D")
        self.nextPb.setCheckable(False)
        self.hl_asdf.addWidget(self.nextPb)

        self.rotateMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rotateMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_rotate.png'))
        self.rotateMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rotateMapToolPb.setToolTip('Rotate Feature Tool (F)')
        self.rotateMapToolPb.installEventFilter(ToolTipFilter(self.rotateMapToolPb,0))
        self.rotateMapToolPb.setShortcut("F")
        self.hl_asdf.addWidget(self.rotateMapToolPb)

        self.rescaleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rescaleMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_scale.png'))
        self.rescaleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rescaleMapToolPb.setToolTip('rescale Feature Tool (G)')
        self.rescaleMapToolPb.installEventFilter(ToolTipFilter(self.rescaleMapToolPb,0))
        self.rescaleMapToolPb.setShortcut("G")
        self.hl_asdf.addWidget(self.rescaleMapToolPb)

        #zxcvb
        self.splitMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.splitMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_clip_polygon.png'))
        self.splitMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.splitMapToolPb.setToolTip('Cut Feature Tool (Z)')
        self.splitMapToolPb.installEventFilter(ToolTipFilter(self.splitMapToolPb,0))
        self.splitMapToolPb.setShortcut("Z")
        self.hl_zxcv.addWidget(self.splitMapToolPb)

        self.vertexMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.vertexMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_vertexTool.png'))
        self.vertexMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.vertexMapToolPb.setToolTip('Vertex Edit Tool (X)')
        self.vertexMapToolPb.installEventFilter(ToolTipFilter(self.vertexMapToolPb,0))
        self.vertexMapToolPb.setShortcut("X")
        self.hl_zxcv.addWidget(self.vertexMapToolPb)

        self.reshapeMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.reshapeMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_clip_1.png'))
        self.reshapeMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.reshapeMapToolPb.setToolTip('Reshape Feature Tool(C)')
        self.reshapeMapToolPb.installEventFilter(ToolTipFilter(self.reshapeMapToolPb,0))
        self.reshapeMapToolPb.setShortcut("C")
        self.hl_zxcv.addWidget(self.reshapeMapToolPb)

        self.pasteMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.pasteMapToolPb.setIcon(QIcon(':/img/resources/gis/gis_copyFeature.png'))
        self.pasteMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.pasteMapToolPb.setToolTip('Paste Feature Tool (V)')
        self.pasteMapToolPb.installEventFilter(ToolTipFilter(self.pasteMapToolPb,0))
        self.pasteMapToolPb.setShortcut("V")
        self.hl_zxcv.addWidget(self.pasteMapToolPb)

        self.fillHoleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.fillHoleMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_fillhole.png'))
        self.fillHoleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.fillHoleMapToolPb.setToolTip('Fill Holes Tool (B)')
        self.fillHoleMapToolPb.installEventFilter(ToolTipFilter(self.fillHoleMapToolPb,0))
        self.fillHoleMapToolPb.setShortcut("B")
        self.hl_zxcv.addWidget(self.fillHoleMapToolPb)

        #f1234
        self.deleteFeaturePb = BetterPillToolButton(self.dockWidgetContents)
        self.deleteFeaturePb.setIcon(QIcon(':/img/resources/gis/shp_delete_select.png'))
        self.deleteFeaturePb.setIconSize(QtCore.QSize(30,30))
        self.deleteFeaturePb.setToolTip('Delete Feature Tool (Del)')
        self.deleteFeaturePb.installEventFilter(ToolTipFilter(self.deleteFeaturePb,0))
        self.deleteFeaturePb.setShortcut("Del")
        self.deleteFeaturePb.setCheckable(False)
        self.hl_f1234.addWidget(self.deleteFeaturePb)

        self.mergeMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.mergeMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_merge.png'))
        self.mergeMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.mergeMapToolPb.setToolTip('Merge Selected Features (F1)')
        self.mergeMapToolPb.installEventFilter(ToolTipFilter(self.mergeMapToolPb,0))
        self.mergeMapToolPb.setShortcut("F1")
        self.mergeMapToolPb.setCheckable(False)
        self.hl_f1234.addWidget(self.mergeMapToolPb)

        self.changeAttrPb = BetterPillToolButton(self.dockWidgetContents)
        self.changeAttrPb.setIcon(QIcon(':/img/resources/gis/shp_modify_attr.png'))
        self.changeAttrPb.setIconSize(QtCore.QSize(30,30))
        self.changeAttrPb.setToolTip('Modify Attributes (F2)')
        self.changeAttrPb.installEventFilter(ToolTipFilter(self.changeAttrPb,0))
        self.changeAttrPb.setShortcut("F2")
        self.changeAttrPb.setCheckable(False)
        self.hl_f1234.addWidget(self.changeAttrPb)

        self.undoPB = BetterPillToolButton(self.dockWidgetContents)
        self.undoPB.setIcon(QIcon(':/img/resources/gis/edit_undo.png'))
        self.undoPB.setIconSize(QtCore.QSize(30,30))
        self.undoPB.setToolTip('undo draw action (ctrl+Z)')
        self.undoPB.installEventFilter(ToolTipFilter(self.undoPB,0))
        self.undoPB.setShortcut("Ctrl+Z")
        self.undoPB.setCheckable(False)
        self.hl_f1234.addWidget(self.undoPB)

        self.redoPB = BetterPillToolButton(self.dockWidgetContents)
        self.redoPB.setIcon(QIcon(':/img/resources/gis/edit_redo.png'))
        self.redoPB.setIconSize(QtCore.QSize(30,30))
        self.redoPB.setToolTip('redo draw action (ctr+shiftl+Z)')
        self.redoPB.installEventFilter(ToolTipFilter(self.redoPB,0))
        self.redoPB.setShortcut("Ctrl+Shift+Z")
        self.redoPB.setCheckable(False)
        self.hl_f1234.addWidget(self.redoPB)

    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate

        self.panMapToolPb.setToolTip(_translate("DIYDialog", "Pan (Q) Drag the Map Canvas to Move"))
        self.magicMapToolPb.setToolTip(_translate("DIYDialog", "Magic Wand (W) Intelligently Extracts Contours"))
        self.polygonMapToolPb.setToolTip(_translate("DIYDialog", "Draw Feature Tool (E) Double Click to Open Stream Mode, Single Click to Close"))
        self.rectangleMapToolPb.setToolTip(_translate("DIYDialog", "Draw Rectangle Feature Tool (R)"))
        self.circleMapToolPb.setToolTip(_translate("DIYDialog", "Draw Circle Feature Tool (T)"))

        self.lastPb.setToolTip(_translate("DIYDialog", "last fishnet (A)"))
        self.selectMapToolPb.setToolTip(_translate("DIYDialog", "Select Feature Tool (S) Drag to Move the Selected Feature, Right Click for Menu Bar"))
        self.nextPb.setToolTip(_translate("DIYDialog", "next fishnet (D)"))
        self.rotateMapToolPb.setToolTip(_translate("DIYDialog", "Rotate Feature Tool (F)"))
        self.rescaleMapToolPb.setToolTip(_translate("DIYDialog", "rescale Feature Tool (G)"))

        self.splitMapToolPb.setToolTip(_translate("DIYDialog", "Cut Feature Tool (Z)"))
        self.vertexMapToolPb.setToolTip(_translate("DIYDialog", "Vertex Edit Tool (X)"))
        self.reshapeMapToolPb.setToolTip(_translate("DIYDialog", "Reshape Feature Tool(C)"))
        self.pasteMapToolPb.setToolTip(_translate("DIYDialog", "Paste Feature Tool (V)"))
        self.fillHoleMapToolPb.setToolTip(_translate("DIYDialog", "Fill Holes Tool (B)"))

        self.deleteFeaturePb.setToolTip(_translate("DIYDialog", "Delete Feature Tool (Del)"))
        self.mergeMapToolPb.setToolTip(_translate("DIYDialog", "Merge Selected Features (F1)"))
        self.changeAttrPb.setToolTip(_translate("DIYDialog", "Modify Attributes (F2)"))
        self.undoPB.setToolTip(_translate("DIYDialog", "undo draw action (ctrl+Z)"))
        self.redoPB.setToolTip(_translate("DIYDialog", "redo draw action (ctr+shiftl+Z)"))

        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        self.layerTree.retranslateDIYUI(yoyiTrs)
        self.emptyLabel.setText(yoyiTrs._translate("点击右上角↗创建项目"))
    
    def changeEnables(self,states):
        # 左上角
        for control in self.controlList:
            control.setEnabled(states)
    
    def delMapTool(self):
        # 
        self.polygonMapTool = None
        self.rectangleMapTool = None
        self.circleMapTool = None
        self.selectMapTool = None
        self.rotateMapTool = None
        self.rescaleMapTool = None
        self.pasteMapTool = None
        self.vertexMapTool = None
        self.reshapeMapTool = None
        self.splitMapTool = None
        self.fillHoleMapTool = None

    def unsetMemberUI(self):
        self.panMapToolPb.click()
        self.delMapTool()
        self.editStack = None
        self.layerTree.clearLevelI()
        del self.tifLayer
        del self.drawLayer
        del self.fishNetLayer
        self.tifLayer = None
        self.drawLayer = None
        self.fishNetLayer = None
        if self.samMapTool:
            self.samMapTool.setDrawLayer(None)
    

    def initMember(self,workDir):
        self.tifDir = None
        self.samMapTool = None
        self.yspc = yoyiShpPropClass()
        self.workDir = workDir
        # 一些默认值 默认地址
        self.valueField = "value"
        self.workCfg = osp.join(self.workDir, "project.config")

        contentDict = readYamlToDict(self.workCfg)
        self.workType = int(contentDict['workType'])
        self.initIndex = int(contentDict['curIndex'])  # 继续上一次作业
        self.fishNetPath = osp.join(self.workDir,contentDict['fishNetPath'])
        if self.workType == DRAW_TYPE_SEG or self.workType == DRAW_TYPE_OD:
            self.tifPath = contentDict['tifPath']
            self.segSize = int(contentDict['segSize'])
        else:
            self.tifPath = contentDict['tifPath']
            self.tifSource = f"type=xyz&url={requests.utils.quote(contentDict['tifPath'])}"
            self.segSize = contentDict['segSize']
            self.xSegNum = self.segSize[0]
            self.ySegNum = self.segSize[1]
        self.drawShpPath = osp.join(self.workDir, contentDict['workShpPath'])
        self.extraLabelDir = contentDict['extraLabelDir'] # 勾画样本时候的额外参数： 标签文件夹
        self.extraImgPost = contentDict['extraImgPost'] # 勾画样本时候的额外参数： 样本后缀
        self.extraLabelPost = contentDict['extraLabelPost'] # 勾画样本时候的额外参数： 标签后缀

        # codeMap
        codemapCfg = osp.join(self.workDir,"project.codemap")

        self.ColorMap = readYamlToDict(codemapCfg)
        self.preFieldValue = list(self.ColorMap.keys())

        # pixelMap
        pixelMapCfg = osp.join(self.workDir,"project.pixelmap")
        if osp.exists(pixelMapCfg):
            self.pixelMapDict = readYamlToDict(pixelMapCfg)
        else:
            self.pixelMapDict = None

        if osp.isdir(self.tifPath):
            self.tifDir = self.tifPath
            self.tifPath = checkAllFileList(self.tifDir,postType=self.extraImgPost)[0]
            self.fishNetLayer = -1
            self.tifLayer = QgsRasterLayer(self.tifPath)
            self.tifLayer.renderer().setAlphaBand(-1)
            if self.tifLayer.bandCount() == 4:
                self.tifLayer.renderer().setRedBand(3)
                self.tifLayer.renderer().setGreenBand(2)
                self.tifLayer.renderer().setBlueBand(1)
            # 初始化矢量
            self.shpPath = osp.join(self.workDir,"vector",osp.basename(self.tifPath).split(".")[0]+".shp")
            self.drawLayer = QgsVectorLayer(self.shpPath, "#INTERDRAW#交互式样本勾画图层")
            self.drawLayer.triggerRepaint()
            self.drawLayer.startEditing()
        else:
            if self.workType == DRAW_TYPE_SEG or self.workType == DRAW_TYPE_OD:
                self.tifLayer = QgsRasterLayer(self.tifPath)
                self.tifLayer.renderer().setAlphaBand(-1)
                if self.tifLayer.bandCount() == 4:
                    self.tifLayer.renderer().setRedBand(3)
                    self.tifLayer.renderer().setGreenBand(2)
                    self.tifLayer.renderer().setBlueBand(1)
            else:
                self.tifLayer = QgsRasterLayer(self.tifSource, "pre", 'wms')
            # 初始化渔网图层
            self.fishNetLayer = QgsVectorLayer("MultiPolygon", "#INTERDRAW#渔网", "memory")
            self.fishNetLayer.setCrs(self.tifLayer.crs())
            createShpLabel(self.fishNetLayer, size=20)
            self.fishNetLayer.triggerRepaint()
            pr = self.fishNetLayer.dataProvider()
            pr.addAttributes([QgsField("FID", QVariant.LongLong)])
            # 初始化矢量
            self.drawLayer = QgsVectorLayer("MultiPolygon", "#INTERDRAW#交互式样本勾画图层", "memory")
            self.drawLayer.setCrs(self.tifLayer.crs())
            pr = self.drawLayer.dataProvider()
            pr.addAttributes([QgsField(self.valueField, QVariant.String)])
            self.drawLayer.updateFields()  # 告诉矢量图层从提供者获取更改
            createShpLabel(self.drawLayer, fieldName=self.valueField, r=255, g=255, b=20, size=13)  # 0 168 227
            self.drawLayer.triggerRepaint()
            self.drawLayer.startEditing()
        
        # layerTree
        self.layerTree.bottomLayer = self.tifLayer
        self.layerTree.drawBottomLayer = self.drawLayer
        if not self.tifDir:
            self.layerTree.fishnetBottomLayer = self.fishNetLayer

        self.layerTree.initBottomLayer()
        self.layerTree.setDrawBottomLayer()
        if not self.tifDir:
            self.layerTree.setFishnetBottomLayer()
        
    def initUI(self,addExtent=True):
        # project pkg label
        self.projectLabel.setText(osp.basename(self.workDir))
        # 是否隐藏渔网修改  label
        if self.workType == DRAW_TYPE_SEG or self.workType == DRAW_TYPE_OD:
            self.xLabel.hide()
            self.yLabel.hide()
            self.xSpinBox.hide()
            self.ySpinBox.hide()
            self.changeFishNet.hide()
            self.tifPathLabel.setText(self.tifPath)
        else:
            contentDict = readYamlToDict(self.workCfg)
            self.xLabel.show()
            self.yLabel.show()
            self.xSpinBox.show()
            self.xSpinBox.setValue(contentDict['segSize'][0])
            self.ySpinBox.show()
            self.ySpinBox.setValue(contentDict['segSize'][1])
            self.changeFishNet.show()
            self.tifPathLabel.setText(self.tifPath.split("{")[0])
        if self.tifDir:
            self.tifPathLabel.setText(self.tifDir)
        # 图层撤回重做相关
        self.editStack: QUndoStack = self.drawLayer.undoStack()
        self.undoPB.setEnabled(False)
        self.redoPB.setEnabled(False)
        # 导入矢量
        if osp.exists(self.drawShpPath):
            self.importShp(self.drawShpPath)
        if osp.exists(self.fishNetPath):
            self.importFishNet(self.fishNetPath)
        # 初始化影像列表 -- 地图画布 -- 颜色
        self.initListModel()
        self.initSpMapCanvas()

        if addExtent and self.workType == DRAW_TYPE_WMS_SEG:
            self.layerTree.addExtraItemByFile(osp.join(self.workDir, "extent.gpkg"))
        if self.initIndex >= 0 and self.initIndex < len(self.fidList) - 1:
            self.changeMapTif(self.initIndex)
        else:
            self.changeMapTif(0)

        self.changeEnables(True)

        if not GPUENABLE:
            self.samMapTool = None
        elif self.workType == DRAW_TYPE_WMS_SEG:
            self.samMapTool = None
        else:
            self.samMapTool = SegAnyMapTool(self.spMapCanvas, self.parentWindow.predictor, self.tifPath, self.drawLayer, self,
                                            self.valueField, 1, 1024)
            self.samMapTool.deactivated.connect(lambda: self.magicMapToolPb.setChecked(False))

        # segType ComboBox
        self.selectTypeComboBox.clear()
        if len(self.preFieldValue) >1 :
            self.selectTypeComboBox.addItem(STRING_FullClassify)
            self.selectTypeComboBox.addItems(self.preFieldValue)
        else:
            self.selectTypeComboBox.addItem(self.preFieldValue[0])
        self.selectTypeComboBox.setCurrentIndex(0)

        self.updateMapcanvasLayers()

    def updateMapcanvasLayers(self):
        if not self.layerTree.stopRender:
            self.spMapCanvas.setLayers(self.layerTree.getLayers())
            self.spMapCanvas.refresh()

    # 得到是否简化自动勾画的魔术棒
    def getAutoSimplyFeature(self):
        isSimply = self.parentWindow.settingInterface.simplyFeatureSwitchButton.isChecked()
        return isSimply

    def initListModel(self):
        if self.tifDir:
            self.fidList = checkAllFileList(self.tifDir,postType=self.extraImgPost)
            self.listViewList = checkAllFileList(self.tifDir,postType=self.extraImgPost,onlyBaseName=True)
        else:
            self.fidList = getFIDlist(self.fishNetLayer,False)
            self.listViewList = getFIDlist(self.fishNetLayer)
        self.slm = QStringListModel()
        self.slm.setStringList(self.listViewList)
        self.listView.setModel(self.slm)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.doubleClicked.connect(self.listViewClicked)

    def listViewClicked(self,modelIndex):
        self.changeMapTif(modelIndex.row())

    def initSpMapCanvas(self):
        self.emptyLabel.hide()
        self.spMapCanvas.show()
        self.spMapCanvas.setDestinationCrs(self.tifLayer.crs())
        self.mapSetting: QgsMapSettings = self.spMapCanvas.mapSettings()
        self.mapCrs = self.mapSetting.destinationCrs()
    
    def changeMapTif(self,index):
        if self.tifDir:
            redBand = self.tifLayer.renderer().redBand()
            greenBand = self.tifLayer.renderer().greenBand()
            blueBand = self.tifLayer.renderer().blueBand()
            preParams = self.drawLayer.renderer().clone()
            # change raster
            self.tifPath = self.fidList[index]
            self.tifLayer = QgsRasterLayer(self.tifPath)
            self.tifLayer.renderer().setRedBand(redBand)
            self.tifLayer.renderer().setGreenBand(greenBand)
            self.tifLayer.renderer().setBlueBand(blueBand)

            self.drawLayer.commitChanges()
            del self.drawLayer
            self.shpPath = osp.join(self.workDir,"vector",osp.basename(self.tifPath).split(".")[0]+".shp")
            self.drawLayer = QgsVectorLayer(self.shpPath, "#INTERDRAW#交互式样本勾画图层")
            createShpLabel(self.drawLayer, fieldName=self.valueField, r=255, g=255, b=20, size=13)  # 0 168 227
            self.drawLayer.startEditing()
            self.editStack: QUndoStack = self.drawLayer.undoStack()
            self.layerTree.bottomLayer = self.tifLayer
            self.layerTree.drawBottomLayer = self.drawLayer
            self.layerTree.setDrawBottomLayer(preParams)
            self.updateMapcanvasLayers()
            self.spMapCanvas : QgsMapCanvas

            crsDest = self.tifLayer.crs()
            xform = QgsCoordinateTransform(crsDest, self.mapCrs, PROJECT.transformContext())
            trueExtent = xform.transformBoundingBox(self.tifLayer.extent())

            self.spMapCanvas.setExtent(trueExtent)
            self.spMapCanvas.refresh()
            if self.samMapTool:
                self.samMapTool.setTif(self.tifPath)
                self.samMapTool.setDrawLayer(self.drawLayer)
            
            self.panMapToolPb.click()
        else:
            # 根据fid选中渔网
            self.fishNetLayer.selectByExpression(f'"FID"=\'{int(self.fidList[index])}\'', QgsVectorLayer.SetSelection)
            # self.fishNetLayer.selectByIds([index])
            self.spMapCanvas.setExtent(self.fishNetLayer.selectedFeatures()[0].geometry().boundingBox().buffered(0.0001))
            self.spMapCanvas.refresh()
        # 改变控件状态
        self.listView.setCurrentIndex(self.slm.index(index, 0))
        self.updateProcessLabel()

    def updateProcessLabel(self):
        self.processLabel.setText(f"{self.listView.currentIndex().row()+1}/{len(self.fidList)}")

    def projectConnectFunc(self):
         # 菜单栏
        self.openProjectPb.clicked.connect(self.actionOpenProjectTriggered)
        self.createProjectPb.clicked.connect(self.createProjectPbTriggered)
        self.closeProjectPb.clicked.connect(self.closeProjectPbTriggered)
        
    # 打开历史项目
    def actionOpenProjectTriggered(self):
        localProjectDir = yoyiSetting().configSettingReader.value('localProject', type=str)
        segmentProjectDir = osp.join(localProjectDir, "segment")
        self.parentWindow.setEnabled(False)
        QApplication.processEvents()
        projectSelectDialog = LocalProjectListDialogClass(segmentProjectDir,parent=self.parentWindow)
        self.parentWindow.setEnabled(True)
        projectSelectDialog.exec_()
        if projectSelectDialog.selectedProject:
            workDir = osp.join(segmentProjectDir,projectSelectDialog.selectedProject)
            if projectSelectDialog.delete:
                if self.workDir and self.workDir == workDir:
                        MessageBox('提示', "您已经打开该项目了,不能删除", self.parentWindow).exec_()
                else:
                    deleteDir(workDir)
                    MessageBox('提示', "删除完毕", self.parentWindow).exec_()
                    self.actionOpenProjectTriggered()
            else:
                try:
                    if self.firstLoad:
                        self.initMember(workDir)
                        self.initUI()
                        self.firstLoad = False
                    else:
                        if self.workDir and self.workDir == workDir:
                            MessageBox('提示', "您已经打开该项目了", self.parentWindow).exec_()
                        else:
                            self.unsetMemberUI()
                            self.initMember(workDir)
                            self.initUI()
                except Exception as e:
                    print(traceback.format_exc())
                    MessageBox('警告', "项目损坏,请删除", self.parentWindow).exec_()
                    self.unsetMemberUI()
                    self.spMapCanvas.hide()
                    self.changeEnables(False)
                    self.emptyLabel.show()
                    self.workDir = None
                    self.slm.setStringList([])
                    self.listView.setModel(self.slm)
                    self.processLabel.setText("?/?")

                    self.tifPathLabel.setText("Unknown")
                    self.projectLabel.setText("Unknown")

                    self.preFieldValue = []
                    self.selectTypeComboBox.clear()

                    self.tifDir = None
        
        projectSelectDialog.deleteLater()

    def createProjectPbTriggered(self):
        dialog = SegDrawCreateProjectDialogClass(self)
        dialog.exec()
        if dialog.projectDir and osp.exists(dialog.projectDir):
            if self.firstLoad:
                self.initMember(dialog.projectDir)
                self.initUI()
                self.firstLoad = False
            else:
                self.unsetMemberUI()
                self.initMember(dialog.projectDir)
                self.initUI()
                self.changeMapTif(0)
        dialog.deleteLater()

    def closeProjectPbTriggered(self):
        if not self.firstLoad and self.workDir:
            w = MessageBox(
                '关闭项目',
                '确认要关闭项目吗？ 勾画会自动保存。',
                self.parentWindow
            )
            w.yesButton.setText('确认关闭')
            w.cancelButton.setText('取消')

            if w.exec():
                self.saveWorkTriggered(False)
                self.drawLayer.commitChanges()
                self.unsetMemberUI()
                self.updateMapcanvasLayers()
                self.spMapCanvas.hide()
                self.changeEnables(False)
                self.emptyLabel.show()
                deleteNameTagging(self.workDir,tag="tempClsfyRes")
                self.workDir = None

                self.slm.setStringList([])
                self.listView.setModel(self.slm)
                self.processLabel.setText("?/?")

                self.tifPathLabel.setText("Unknown")
                self.projectLabel.setText("Unknown")

                self.preFieldValue = []
                self.selectTypeComboBox.clear()

                self.tifDir = None

    def topBarConnectFunc(self):
        self.addGuideLayer.clicked.connect(self.addGuideLayerTriggered)
        self.changeFishNet.clicked.connect(self.changeFishNetTriggered)
        # 全分割列表
        self.selectTypeComboBox.currentIndexChanged.connect(self.selectTypeComboBoxIndexChanged)

    def addGuideLayerTriggered(self):
        file, ext = QFileDialog.getOpenFileName(self,"选择参考图层", "", "GisFile(*.shp;*SHP;*gpkg;*geojson;*.tif;*tiff;*TIF;*TIFF)")
        if file:
            self.layerTree.addExtraItemByFile(file)
            self.updateMapcanvasLayers()

    def changeFishNetTriggered(self):
        self.panMapToolPb.click()
        self.spMapCanvas.setLayers([])
        success = QgsVectorFileWriter.deleteShapeFile(self.fishNetPath)
        createFishNetByXYInterval(osp.join(self.workDir, "extent.gpkg"),self.fishNetPath
                                  ,self.xSpinBox.value(),self.ySpinBox.value())
        saveSampleWorkYaml(self.workCfg, self.workType,
                           tifPath=self.tifPath, curIndex=0, segSize=[self.xSpinBox.value(),self.ySpinBox.value()])

        del self.fishNetLayer

        self.fishNetLayer = QgsVectorLayer("MultiPolygon", "#INTERDRAW#fishNet", "memory")
        self.fishNetLayer.setCrs(self.tifLayer.crs())
        createShpLabel(self.fishNetLayer, size=20)
        self.fishNetLayer.setRenderer(self.yspc.createDiySymbol("74,111,163", lineWidth='0.7', isFull=False))
        self.fishNetLayer.triggerRepaint()
        pr = self.fishNetLayer.dataProvider()
        pr.addAttributes([QgsField("FID", QVariant.LongLong)])

        self.layerTree.fishnetBottomLayer = self.fishNetLayer
        self.layerTree.setFishnetBottomLayer()

        self.initUI(addExtent=False)
        self.updateMapcanvasLayers()

    def selectTypeComboBoxIndexChanged(self):
        self.panMapToolPb.click()

    def mapToolConnectFunc(self):
        # 地图工具
        self.panMapToolPb.clicked.connect(self.panMapToolTriggered)
        self.magicMapToolPb.clicked.connect(self.magicMapToolPbTriggered)
        self.polygonMapToolPb.clicked.connect(self.polygonMapToolTriggered)
        self.rectangleMapToolPb.clicked.connect(self.rectangleMapToolTriggered)
        self.circleMapToolPb.clicked.connect(self.circleMapToolTriggered)

        self.selectMapToolPb.clicked.connect(self.selectMapToolTriggered)
        self.rotateMapToolPb.clicked.connect(self.rotateMapToolPbTriggered)
        self.rescaleMapToolPb.clicked.connect(self.rescaleMapToolPbTriggereds)

        self.pasteMapToolPb.clicked.connect(self.pasteMapToolTriggered)
        self.vertexMapToolPb.clicked.connect(self.vertexMapToolTriggered)
        self.reshapeMapToolPb.clicked.connect(self.reshapeMapToolTriggered)
        self.splitMapToolPb.clicked.connect(self.splitMapToolTriggered)
        self.fillHoleMapToolPb.clicked.connect(self.fillHoleMapToolTriggered)

        self.mergeMapToolPb.clicked.connect(self.mergeMapToolTriggered)
        self.changeAttrPb.clicked.connect(self.modifyAttrTriggered)
        self.deleteFeaturePb.clicked.connect(self.deleteFeaturePbTriggered)
        
    # 地图工具
    def panMapToolTriggered(self):
        if self.panMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.panMapTool = QgsMapToolPan(self.spMapCanvas)
            self.spMapCanvas.setMapTool(self.panMapTool)
            self.panMapTool.deactivated.connect(lambda: self.panMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == QgsMapToolPan:
                    self.panMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
         
    def magicMapToolPbTriggered(self):
        if self.samMapTool: 
            if self.magicMapToolPb.isChecked():
                if len(self.preFieldValue) == 1 or (len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify):
                    self.samMapTool.setPreFieldValue(self.preFieldValue)
                elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
                    self.samMapTool.setPreFieldValue(self.selectTypeComboBox.currentText())

                if self.spMapCanvas.mapTool() is None:
                    self.spMapCanvas.setMapTool(self.samMapTool)
                elif self.spMapCanvas.mapTool() and type(self.spMapCanvas.mapTool()) is not SegAnyMapTool:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.setMapTool(self.samMapTool)
                else:
                    self.samMapTool.reset()
            else:
                if self.spMapCanvas.mapTool():
                    if type(self.spMapCanvas.mapTool()) == SegAnyMapTool:
                        self.samMapTool.reset()
                        self.magicMapToolPb.setChecked(True)
                    else:
                        self.spMapCanvas.mapTool().deactivate()
                        self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
        else:
            MessageBox('信息', "当前软件未搜寻到GPU相关插件，禁止使用SAM", self.parentWindow).exec_()
            self.magicMapToolPb.setChecked(False)
             
    def polygonMapToolTriggered(self):
        if self.polygonMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            if len(self.preFieldValue) == 1 or (len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify):
                preFieldValueTemp = self.preFieldValue
            elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
                preFieldValueTemp = self.selectTypeComboBox.currentText()
            self.polygonMapTool = PolygonMapTool(self.spMapCanvas, self.drawLayer, self, preField=self.valueField, preFieldValue=preFieldValueTemp)
            self.spMapCanvas.setMapTool(self.polygonMapTool)
            self.polygonMapTool.deactivated.connect(lambda: self.polygonMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == PolygonMapTool:
                    self.polygonMapTool.reset()
                    self.polygonMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def rectangleMapToolTriggered(self):
        if self.rectangleMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            if len(self.preFieldValue) == 1 or (len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify):
                preFieldValueTemp = self.preFieldValue
            elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
                preFieldValueTemp = self.selectTypeComboBox.currentText()
            self.rectangleMapTool = RectangleMapTool(self.spMapCanvas, self.drawLayer, self, preField=self.valueField, preFieldValue=preFieldValueTemp)
            self.spMapCanvas.setMapTool(self.rectangleMapTool,True)
            self.rectangleMapTool.deactivated.connect(lambda: self.rectangleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RectangleMapTool:
                    self.rectangleMapTool.reset()
                    self.rectangleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def circleMapToolTriggered(self):
        if self.circleMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            if len(self.preFieldValue) == 1 or (len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify):
                preFieldValueTemp = self.preFieldValue
            elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
                preFieldValueTemp = self.selectTypeComboBox.currentText()
            self.circleMapTool = CircleMapTool(self.spMapCanvas, self.drawLayer, self, preField="value", preFieldValue=preFieldValueTemp)
            self.spMapCanvas.setMapTool(self.circleMapTool)
            self.circleMapTool.deactivated.connect(lambda: self.circleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == CircleMapTool:
                    self.circleMapTool.reset()
                    self.circleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def selectMapToolTriggered(self):
        if self.selectMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.selectMapTool = RecTangleSelectFeatureMapTool(self.spMapCanvas, self.drawLayer, self, alwaysUpdate=True)
            self.spMapCanvas.setMapTool(self.selectMapTool)
            self.selectMapTool.deactivated.connect(lambda: self.selectMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RecTangleSelectFeatureMapTool:
                    self.selectMapTool.reset()
                    self.selectMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
    
    def rotateMapToolPbTriggered(self):
        if self.rotateMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.rotateMapTool = RotatePolygonMapTool(self.spMapCanvas,self.drawLayer,self)
            self.spMapCanvas.setMapTool(self.rotateMapTool)
            self.rotateMapTool.deactivated.connect(lambda: self.rotateMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RotatePolygonMapTool:
                    self.selectMapTool.reset()
                    self.selectMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                
    def rescaleMapToolPbTriggereds(self):
        if self.rescaleMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.rescaleMapTool = RescalePolygonMapTool(self.spMapCanvas,self.drawLayer,self)
            self.spMapCanvas.setMapTool(self.rescaleMapTool)
            self.rescaleMapTool.deactivated.connect(lambda: self.rescaleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RescalePolygonMapTool:
                    self.selectMapTool.reset()
                    self.selectMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
        
    def pasteMapToolTriggered(self):
        if self.pasteMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.pasteMapTool = PastePolygonMapTool(self.spMapCanvas, self.drawLayer, self)
            self.spMapCanvas.setMapTool(self.pasteMapTool)
            self.pasteMapTool.deactivated.connect(lambda: self.pasteMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == PastePolygonMapTool:
                    self.pasteMapTool.reset()
                    self.pasteMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def vertexMapToolTriggered(self):
        if self.vertexMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.vertexMapTool = EditVertexMapTool(self.spMapCanvas, self.drawLayer, self,useBbox=False)
            self.spMapCanvas.setMapTool(self.vertexMapTool)
            self.vertexMapTool.deactivated.connect(lambda: self.vertexMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == EditVertexMapTool:
                    self.vertexMapTool.reset()
                    self.vertexMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def reshapeMapToolTriggered(self):
        if self.reshapeMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.reshapeMapTool = ReShapePolygonMapTool(self.spMapCanvas, self.drawLayer, self)
            self.spMapCanvas.setMapTool(self.reshapeMapTool)
            self.reshapeMapTool.deactivated.connect(lambda: self.reshapeMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == ReShapePolygonMapTool:
                    self.reshapeMapTool.reset()
                    self.reshapeMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def splitMapToolTriggered(self):
        if self.splitMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.splitMapTool = SplitPolygonMapTool(self.spMapCanvas, self.drawLayer, self)
            self.spMapCanvas.setMapTool(self.splitMapTool)
            self.splitMapTool.deactivated.connect(lambda: self.splitMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == SplitPolygonMapTool:
                    self.splitMapTool.reset()
                    self.splitMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def fillHoleMapToolTriggered(self):
        if self.fillHoleMapToolPb.isChecked():
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.mapTool().deactivate()
            self.fillHoleMapTool = FillHoleMapTool(self.spMapCanvas, self.drawLayer, self)
            self.spMapCanvas.setMapTool(self.fillHoleMapTool)
            self.fillHoleMapTool.deactivated.connect(lambda: self.fillHoleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == FillHoleMapTool:
                    self.fillHoleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.mapTool().deactivate()
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())

    def mergeMapToolTriggered(self):
        if len(self.drawLayer.selectedFeatureIds()) >1:
            if len(self.preFieldValue) == 1 :
                resString = self.preFieldValue[0]
            elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify:
                selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self)
                selectAttrWindows.exec()
                resIndex = selectAttrWindows.resIndex
                if resIndex <0:
                    return
                resString = self.preFieldValue[resIndex]
                selectAttrWindows.destroy()
            elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
                resString = self.selectTypeComboBox.currentText()

            geom : QgsGeometry = None
            idList = []
            for featTemp in self.drawLayer.selectedFeatures():
                idList.append(featTemp.id())
                if geom == None:
                    geom = featTemp.geometry()
                else:
                    geom = geom.combine(featTemp.geometry())
            geom = makeValid_deleteAngle0(geom)
            if geom.type() == 2:
                self.editStack.beginMacro("mergeFeatures")
                self.drawLayer.deleteFeatures(idList)
                feat = QgsFeature(self.drawLayer.fields())
                feat.setAttribute(self.valueField,resString)
                feat.setGeometry(geom)
                self.drawLayer.addFeature(feat)
                self.editStack.endMacro()
                self.spMapCanvas.refresh()
                self.updateShpUndoRedoButton()
            else:
                MessageBox('信息', "合并失败，矢量过于复杂", self.parentWindow).exec_()

    def modifyAttrTriggered(self):
        if len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() == STRING_FullClassify:
            selectAttrWindows = selectSingleAttrWindowClass(self.preFieldValue,self)
            selectAttrWindows.exec()
            resIndex = selectAttrWindows.resIndex
            if resIndex <0:
                return
            resString = self.preFieldValue[resIndex]
            selectAttrWindows.destroy()
        elif len(self.preFieldValue) > 1 and self.selectTypeComboBox.currentText() != STRING_FullClassify:
            resString = self.selectTypeComboBox.currentText()
        else:
            return

        self.editStack.beginMacro("modifyAttr")
        for featTemp in self.drawLayer.selectedFeatures():
            self.drawLayer.changeAttributeValue(featTemp.id(),0,resString)
        self.editStack.endMacro()
        self.spMapCanvas.refresh()
        self.updateShpUndoRedoButton()

    def deleteFeaturePbTriggered(self):
        self.editStack.beginMacro("deleteFeature")
        self.drawLayer.deleteSelectedFeatures()
        self.editStack.endMacro()
        self.updateShpUndoRedoButton()

    def rightBarConnectFunc(self):
        self.undoPB.clicked.connect(self.actionUndoShpTriggered)
        self.redoPB.clicked.connect(self.actionRedoShpTriggered)
        self.commitMagicPB.clicked.connect(self.commitMagicTriggered)
        self.checkFeatureCountPb.clicked.connect(self.checkFeatureCountPbTriggered)

        self.reSizeExtent.clicked.connect(self.reSizeExtentTriggered)

        self.lastPb.clicked.connect(self.lastPbTriggered)
        self.nextPb.clicked.connect(self.nextPbTriggered)

        # save
        self.saveWorkPb.clicked.connect(lambda : self.saveWorkTriggered(needMessage=True))
        self.exportShpPb.clicked.connect(self.exportShpTriggered) 

        # slcfy
        self.pixelClsfyPb.clicked.connect(self.pixelClsfyPbClicked)
        self.openSpectralCurvePb.clicked.connect(self.openSpectralCurvePbClicked)
         
    def commitMagicTriggered(self):
        if self.createExtentPb.isChecked():
            if self.tifDir:
                tempRec = self.tifLayer.extent()
            else:
                tempRec = self.fishNetLayer.selectedFeatures()[0].geometry().boundingBox()
            xminNew = tempRec.xMinimum() + 0.25*(tempRec.xMaximum()-tempRec.xMinimum())
            xmaxNew = tempRec.xMinimum() + 0.75*(tempRec.xMaximum()-tempRec.xMinimum())
            yminNew = tempRec.yMinimum() + 0.25*(tempRec.yMaximum()-tempRec.yMinimum())
            ymaxNew = tempRec.yMinimum() + 0.75*(tempRec.yMaximum()-tempRec.yMinimum())
            smallRec = QgsRectangle()
            smallRec.set(xminNew,yminNew,xmaxNew,ymaxNew)
            self.drawLayer.selectByRect(smallRec)
            self.drawLayer.deleteSelectedFeatures()
            feature = QgsFeature(self.drawLayer.fields())
            feature.setAttribute(self.valueField,self.preFieldValue[0])
            feature.setGeometry(QgsGeometry.fromRect(tempRec))
            self.drawLayer.addFeature(feature)
            self.spMapCanvas.refresh()
            self.updateShpUndoRedoButton()
        else:
            if self.samMapTool:
                self.samMapTool.commitMagicTempPolygon()
    
    def checkFeatureCountPbTriggered(self):
        MessageBox('信息', f"当前要素个数：{self.drawLayer.featureCount()}", self).exec_()

    # 撤回重做
    def actionUndoShpTriggered(self):
        
        if self.samMapTool:
            if self.spMapCanvas.mapTool() and type(self.spMapCanvas.mapTool()) == SegAnyMapTool:
                if self.samMapTool.ctrlTempPolygon:
                    self.samMapTool.reset()
                    return

        if self.editStack != None and self.editStack.canUndo():
            self.editStack.undo()
            self.spMapCanvas.refresh()
            self.updateShpUndoRedoButton()

    def actionRedoShpTriggered(self):
        if self.editStack != None and self.editStack.canRedo():
            self.editStack.redo()
            self.spMapCanvas.refresh()
            self.updateShpUndoRedoButton()

    def updateShpUndoRedoButton(self):
        """
        动态更新撤销重做控件是否可用
        """
        if self.editStack != None:
            self.undoPB.setEnabled(self.editStack.canUndo())
            self.redoPB.setEnabled(self.editStack.canRedo())
        else:
            self.undoPB.setEnabled(False)
            self.redoPB.setEnabled(False)

    def lastPbTriggered(self):
        if self.listView.currentIndex().row() == 0:
            MessageBox('提示', "您的任务已经是第一个了", self.parentWindow).exec_()
        else:
            self.changeMapTif(self.listView.currentIndex().row()-1)

    def nextPbTriggered(self):
        if self.listView.currentIndex().row() == len(self.fidList) - 1:
            MessageBox('提示', "您的任务已经是最后一个了", self.parentWindow).exec_()
        else:
            self.changeMapTif(self.listView.currentIndex().row() + 1)

    def reSizeExtentTriggered(self):
        tempExtent : QgsRectangle = self.tifLayer.extent()
        self.spMapCanvas.setExtent(tempExtent.buffered(0.0001))
        self.spMapCanvas.refresh()

    # 导入矢量
    def importShp(self, shpPath):
        if self.tifDir:
            pass
        else:
            fishNetExtent: QgsGeometry = QgsGeometry.fromRect(self.fishNetLayer.extent())
            # self.editStack.beginMacro("importShp")
            importLayer = QgsVectorLayer(shpPath, os.path.splitext(os.path.basename(shpPath))[0], "ogr")
            fieldList = []
            for field in importLayer.fields():
                fieldList.append(field.name())
            for featureTemp in importLayer.getFeatures():
                featureTemp: QgsFeature
                tempGeo: QgsGeometry = featureTemp.geometry()
                if fishNetExtent.intersects(tempGeo):
                    newFeature = QgsFeature(self.drawLayer.fields())
                    newFeature.setGeometry(tempGeo)
                    if len(self.preFieldValue) >1 and (self.valueField in fieldList):
                        tempAttr = str(featureTemp.attribute(self.valueField))
                        if tempAttr in self.preFieldValue:
                            newFeature.setAttribute(self.valueField,tempAttr)
                        else:
                            newFeature.setAttribute(self.valueField,self.preFieldValue[0])
                    else:
                        newFeature.setAttribute(self.valueField,self.preFieldValue[0])
                    self.drawLayer.addFeature(newFeature)
        self.drawLayer.commitChanges(stopEditing=False)
        self.drawLayer.triggerRepaint()

    def importFishNet(self,fishNetPath):
        self.fishNetLayer.startEditing()
        importLayer = QgsVectorLayer(fishNetPath)
        for featureTemp in importLayer.getFeatures():
            featureTemp: QgsFeature
            self.fishNetLayer.addFeature(featureTemp)
        self.fishNetLayer.commitChanges()
        del importLayer

    # 保存作业
    def saveWorkTriggered(self, needMessage=True):
        self.drawLayer.commitChanges(stopEditing=False)
        if not self.tifDir:
            saveShpFunc(self.drawShpPath, self.drawLayer)
        curIndex = self.listView.currentIndex().row()
        if self.workType == DRAW_TYPE_SEG or self.workType == DRAW_TYPE_OD:
            segSize = self.segSize
        else:
            segSize = [self.xSpinBox.value(), self.ySpinBox.value()]
        saveSampleWorkYaml(self.workCfg, self.workType,
                           tifPath=self.tifDir if self.tifDir else self.tifPath
                           ,curIndex=curIndex
                           ,segSize=segSize
                           ,extraLabelDir=self.extraLabelDir
                           ,extraImgPost=self.extraImgPost
                           ,extraLabelPost=self.extraLabelPost)
        if needMessage:
            MessageBox('信息', "保存成功", self.parentWindow).exec_()
        else:
            print("保存成功")
        
        self.spMapCanvas.saveAsImage(osp.join(self.workDir,STRING_SNAPSHOT))

    # 导出矢量
    def exportShpTriggered(self):
        if not self.tifDir:
            self.drawLayer.commitChanges(stopEditing=False)
            file, ext = QFileDialog.getSaveFileName(self, "保存文件", "" , "ShapeFile(*.shp;*SHP)")
            if file:
                saveShpFunc(file, self.drawLayer)
                MessageBox('信息', "导出成功", self.parentWindow).exec_()
        else:
            override = False
            if osp.exists(self.extraLabelDir):
                w = MessageBox('消息', '选择导出方式', self)
                w.yesButton.setText('直接覆盖')
                w.cancelButton.setText('另存为')
                if w.exec():
                    override = True
            
            if not override:
                fileDir = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
                if fileDir:
                    outputDir = fileDir
                else:
                    return 
            else:
                outputDir = self.extraLabelDir

            self.updateSampleThread = updateDataSetRunClass(
                label_dir_path=outputDir,
                label_shp_path=osp.join(self.workDir,"vector"),
                img_dir_path=self.tifDir,
                pixel_map=self.pixelMapDict,
                attr_field=self.valueField,
                img_post=self.extraImgPost,
                label_post=self.extraLabelPost if self.extraLabelPost!="" else "png"
            )
            self.setEnabled(False)
            self.ProgressBar.show()
            self.updateSampleThread.signal_process.connect(self.changeProgressBar)
            self.updateSampleThread.signal_over.connect(self.finishUpdateSample)
            self.updateSampleThread.finished.connect(self.updateSampleThread.deleteLater)
            self.updateSampleThread.start()
    
    def pixelClsfyPbClicked(self):
        if self.workType != DRAW_TYPE_SEG:
            MessageBox('警告', "只有本地影像勾画模式可以进行分类", self).exec_()
            return
        if self.tifDir:
            MessageBox('警告', "勾画数据集不可以进行分类", self).exec_()
            return
        if len(self.preFieldValue) < 2:
            MessageBox('警告', "类别数大于1才可以进行分类", self).exec_()
            return
        dialog = PixelClassifyMapWindowClass(self.preFieldValue,
                                             mode="classify",
                                             hideBg=True,parent=self)
        dialog.exec()
        if dialog.completeStatus:
            tempResPath = makeFileUnique(osp.join(self.workDir,"tempClsfyRes.tif"))
            self.interactiveClsfyThread = pixelClsfyRunClass(imgPath=self.tifPath,
                                                             shpPath=self.drawShpPath,
                                                             resultPath=tempResPath,
                                                             fieldName=self.valueField,
                                                             attrMapping=dialog.pixelMap,
                                                             mode="mle")
            self.setEnabled(False)
            self.ProgressBar.show()
            self.interactiveClsfyThread.signal_process.connect(self.changeProgressBar)
            self.interactiveClsfyThread.signal_over.connect(self.finishClsfy)
            self.interactiveClsfyThread.finished.connect(self.interactiveClsfyThread.deleteLater)
            self.interactiveClsfyThread.start()
        dialog.deleteLater()
        
    def openSpectralCurvePbClicked(self):
        if self.workType != DRAW_TYPE_SEG:
            MessageBox('警告', "只有本地影像勾画模式可以进行光谱曲线查看", self).exec_()
            return
        if self.tifDir:
            MessageBox('警告', "勾画数据集不可以进行光谱曲线查看", self).exec_()
            return
        if self.scpDialog:
            MessageBox('警告', "当前已经打开光谱曲线查看工具", self).exec_()
            return
        self.scpDialog = SpectralCurveWindowClass(self.spMapCanvas,self.tifLayer,self)
        self.scpDialog.dialogClosed.connect(self.scpDialogClosed)
        self.scpDialog.show()
    
    def scpDialogClosed(self):
        self.scpDialog.deleteLater()
        self.panMapToolPb.click()
        self.scpDialog = None

    def changeProgressBar(self,process):
        self.ProgressBar.setValue(process)
    
    def finishUpdateSample(self,resDir):
        self.setEnabled(True)
        self.ProgressBar.hide()

        if os.path.exists(resDir):
            MessageBox('成功',"更新成功", self).exec_()
        else:
            MessageBox('警告',resDir,self).exec_()

    def finishClsfy(self,params):
        resPath,attrMapping = params
        self.setEnabled(True)
        self.ProgressBar.hide()

        if osp.exists(resPath):
            self.layerTree.addExtraItemByFile(resPath,attrMapping=attrMapping)
            self.updateMapcanvasLayers()
        else:
            MessageBox('错误',resPath,self).exec_()

