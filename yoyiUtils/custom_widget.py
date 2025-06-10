import os
import os.path as osp
import time
import random
import shutil
import requests
from PyQt5.QtCore import QVariant,pyqtProperty,pyqtSignal,QRect,QPoint,QEvent
from PyQt5 import QtCore
from PyQt5.QtGui import QPen,QCursor,QKeySequence,QIcon,QColor, QDropEvent, QMouseEvent,QPixmap,QPainter,QDragMoveEvent,QImage,QBrush,QFont
from PyQt5.QtWidgets import QFrame,QAbstractItemView,QShortcut,QTreeWidgetItem,QTreeWidgetItemIterator,QGraphicsRectItem,QListWidgetItem,\
    QVBoxLayout,QWidget,QAbstractItemView,QMenu, QAction,QUndoStack,QMainWindow,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,\
        QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication,QGraphicsOpacityEffect
from qgis.core import QgsMapLayerType,QgsColorRampShader,QgsPalettedRasterRenderer,QgsMapLayer,QgsMapSettings,\
    QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader,QgsLayerTreeModel,\
    QgsPalettedRasterRenderer,QgsVectorLayer,QgsDataSourceUri,QgsLayerTreeNode,QgsLayerTree,\
    QgsLayerTreeGroup,QgsCoordinateTransform,QgsVectorTileLayer,QgsSingleSymbolRenderer,QgsGeometry
from qgis.gui import QgsMapToolIdentifyFeature,QgsLayerTreeViewMenuProvider,QgsLayerTreeView,QgsLayerTreeViewDefaultActions,QgsMapCanvas,QgsMapToolPan
import traceback

from qfluentwidgets import RoundMenu,Action,MessageBox,TreeWidget,MenuAnimationType,\
                            NavigationWidget,TransparentToolButton,FluentLabelBase,IconWidget,BodyLabel,isDarkTheme,ThemeColor,ToolTipFilter
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.common.animation import BackgroundAnimationWidget
from qfluentwidgets.components.widgets.button import PillToolButton,ToggleToolButton

from yoyiUtils.custom_maptool import IdentifyRasterMapTool
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiFile import saveYamlForDict,readYamlToDict,saveSampleWorkYaml
from yoyiUtils.qgisLayerUtils import getFIDlist
from yoyiUtils.qgisFunction import saveShpFunc
from yoyiUtils.yoyiTranslate import yoyiTrans
from yoyiUtils.attributeDialog import AttributeDialog

from widgets.layerPropWindowWidget import LayerPropWindowWidgeter
from widgets.draw_dialog_shpLabelingDialog import ShpLabelingDialogClass

from appConfig import *

import yoyirs_rc
PROJECT = QgsProject.instance()

class YoyiTreeView():
    def __init__(self,mapcanvas,yoyiTrs:yoyiTrans,parent=None,extraMapCanvas=None,openQuickKey=False) -> None:
        
        self.parentWindow = parent
        self.layerTreeView = QgsLayerTreeView(parent)
        self.mapCanvas: QgsMapCanvas = mapcanvas
        self.yoyiTrs = yoyiTrs
        self.extraMapCanvas : QgsMapCanvas = extraMapCanvas
        self.openQuickKey = openQuickKey

        self.project : QgsProject = QgsProject.instance()
        self.projectLayerTreeRoot:QgsLayerTree = self.project.layerTreeRoot()
        self.model = QgsLayerTreeModel(self.projectLayerTreeRoot, parent)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeRename)  # 允许图层节点重命名
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)  # 允许图层拖拽排序
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)  # 允许改变图层节点可视性
        self.model.setFlag(QgsLayerTreeModel.ShowLegendAsTree)  # 展示图例
        self.model.setAutoCollapseLegendNodes(10)  # 当节点数大于等于10时自动折叠
        self.layerTreeView.setModel(self.model) # 图层树model设置

        
        self.leftActiveKey = None
        self.rightActiveKey = None
        self.leftKey1 = None
        self.leftKey2 = None
        self.rightKey3 = None
        self.rightKey4 = None

        # 图层是否被激活

        self.connectFunc()
        self.initMember()

    def connectFunc(self):
        self.projectLayerTreeRoot.layerOrderChanged.connect(self.refreshLayers)
        self.projectLayerTreeRoot.visibilityChanged.connect(self.refreshLayers)

        self.rightMenuProv = yoyiMenuProvider(self,self.yoyiTrs)
        self.layerTreeView.setMenuProvider(self.rightMenuProv)
    
    def initMember(self):
        # 存储本地图层的类型
        self.layerTypeDict : dict[str:int] = {}
        # 画布的底图
        self.bottomLayer = None
        # 额外画布的底图
        self.extraBottomLayer = None
        # 作业矢量
        self.drawBottomLayer = None
        # 渔网
        self.fishnetBottomLayer = None
        self.yspc = yoyiShpPropClass()
    
    def clearTreeView(self):
        self.project.clear()
        self.layerTypeDict = {}
        self.mapCanvas.refresh()
        self.extraMapCanvas.refresh()
        # 画布的底图
        self.bottomLayer = None
        # 额外画布的底图
        self.extraBottomLayer = None
        # 作业矢量
        self.drawBottomLayer : QgsVectorLayer = None
        # 快捷绑定
        self.leftActiveKey = None
        self.rightActiveKey = None
        self.leftKey1 = None
        self.leftKey2 = None
        self.rightKey3 = None
        self.rightKey4 = None
    
    def openLayerProp(self, layer:QgsMapLayer):
        lp = LayerPropWindowWidgeter(layer, self.mapCanvas,self.yoyiTrs,extraMapCanvas=self.extraMapCanvas,parent=self.parentWindow)
        lp.show()

    def refreshLayers(self):
        #print("图层发生了变化")
        layers = self.projectLayerTreeRoot.checkedLayers()
        layers.insert(0,self.drawBottomLayer)

        if self.openQuickKey:
            if self.leftActiveKey == 1:
                if self.leftKey1:
                    if len(self.project.mapLayersByName(self.leftKey1)) >0:
                        quickLayer = self.project.mapLayersByName(self.leftKey1)[0]
                    else:
                        quickLayer = self.extraBottomLayer if self.extraBottomLayer else self.bottomLayer
                else:
                    quickLayer = self.extraBottomLayer if self.extraBottomLayer else self.bottomLayer
                layers.append(quickLayer)
            elif self.leftActiveKey == 2:
                if self.leftKey2:
                    if len(self.project.mapLayersByName(self.leftKey2)) >0:
                        quickLayer = self.project.mapLayersByName(self.leftKey2)[0]
                    else:
                        quickLayer = self.extraBottomLayer if self.extraBottomLayer else self.bottomLayer
                else:
                    quickLayer = self.extraBottomLayer if self.extraBottomLayer else self.bottomLayer
                layers.append(quickLayer)

        layers.append(self.bottomLayer)
        self.mapCanvas.setLayers(layers)

        if self.extraMapCanvas:
            extraLayers = self.projectLayerTreeRoot.checkedLayers()
            extraLayers.insert(0,self.drawBottomLayer)

            if self.openQuickKey:
                if self.rightActiveKey == 3:
                    if self.rightKey3:
                        if len(self.project.mapLayersByName(self.rightKey3)) >0:
                            quickLayer = self.project.mapLayersByName(self.rightKey3)[0]
                        else:
                            quickLayer = self.bottomLayer
                    else:
                        quickLayer = self.bottomLayer
                    extraLayers.append(quickLayer)
                elif self.rightActiveKey == 4:
                    if self.rightKey4:
                        if len(self.project.mapLayersByName(self.rightKey4)) >0:
                            quickLayer = self.project.mapLayersByName(self.rightKey4)[0]
                        else:
                            quickLayer = self.bottomLayer
                    else:
                        quickLayer = self.bottomLayer
                    extraLayers.append(quickLayer)

            extraLayers.append(self.extraBottomLayer)
            self.extraMapCanvas.setLayers(extraLayers)
        
    def addExtraItemByFile(self,file,attrMapping=None,needMsg=True,layerName=None): 

        if layerName:
            trueName = layerName
            tempPost = osp.basename(file).split(".")[-1]
        else:
            tempName = osp.basename(file).split(".")[0]
            tempPost = osp.basename(file).split(".")[-1]
            index = 1
            trueName = tempName+"."+tempPost
            while trueName in self.layerTypeDict.keys():
                trueName = tempName + f"_{index}"
                index += 1
        
        if tempPost in ['shp','SHP','geojson','gpkg']: 
            layer = QgsVectorLayer(file, trueName, "ogr")
            layer.setProviderEncoding('utf-8')
            
        elif tempPost in ['tif','TIF','tiff','TIFF']:
            layer = QgsRasterLayer(file,trueName)
            layerRender = layer.renderer()
            layerRender.setAlphaBand(-1)
            print("layer band count")
            if layer.bandCount() == 4:
                layerRender.setRedBand(3)
                layerRender.setGreenBand(2)
                layerRender.setBlueBand(1)
            elif attrMapping and layer.bandCount() == 1:
                pcolor = []
                random.seed(time.time())
                for name,pixelValue in attrMapping.items():
                    tempR = random.randint(1, 254)
                    tempG = random.randint(1, 254)
                    tempB = random.randint(1, 254)
                    pcolor.append(QgsColorRampShader.ColorRampItem(pixelValue, QColor(tempR,tempG,tempB),name))
                tempRenderer = QgsPalettedRasterRenderer(layer.dataProvider(),
                                                         1,
                                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
                layer.setRenderer(tempRenderer)

        if layer.isValid():
            self.layerTypeDict[trueName] = Local_Type
            self.project.addMapLayer(layer)
        else:
            if needMsg:
                MessageBox(self.yoyiTrs._translate('错误'),self.yoyiTrs._translate('图层无效'),self.yoyiLayerTree.parentWindow).exec()
            del layer
    
    def addExtraItemByUrl(self,url:QgsDataSourceUri,name,isLocalType=True,isChecked=True,isVectorTile=False,preSource=False):
        """
        name: 图层名
        isLocalType： 如果是Local_Type  在图层树里可以被删掉
        isVectorTile： 是矢量xyz
        preSource： 不需要解析，直接使用string
        # 当前没有使用 但是后续有可能使用 矢量切片 记录留作归档 
        # fishNetVectorTileUri = QgsDataSourceUri()
        # fishNetVectorTileUri.setParam("type", "xyz")
        # fishNetVectorTileUri.setParam("url", f"node_geo_forest2024/jygjServerBack/gridServer/{{z}}/{{x}}/{{y}}?task_id={self.taskId}")
        # self.layerTree.addExtraItemByUrl(fishNetVectorTileUri,"矢量切片-作业渔网",isLocalType=False,isVectorTile=True)
        """
        if isLocalType:
            itemType = Local_Type
        else:
            itemType = Wms_Type
        
        index = 1
        while name in self.layerTypeDict.keys():
            name = name + f"_{index}"
            index += 1

        netMode = yoyiSetting().configSettingReader.value('netMode',type=int)

        if preSource:
            layer = QgsRasterLayer(url,name,'wms')
        elif type(url) == QgsDataSourceUri:  #直接通过QgsDataSourceUri 加载
            if isVectorTile:
                print(url.uri())
                print(str(url.encodedUri())[2:-1])
                layer = QgsVectorTileLayer(str(url.encodedUri())[2:-1], name)
            else:
                layer = QgsRasterLayer(str(url.encodedUri())[2:-1],name,'wms')
        #sp_geoserver&namespace:interpretation_tool&layer:sjy_classification
        elif 'sp_geoserver' in url:  #geoserver 切片
            geoserverUrl  = GeoserverUrlDict[netMode]
            _,namespaceLine,layerLine = url.split("&")
            namespaceStr = namespaceLine.split(":")[1]
            layerStr = layerLine.split(":")[1]
            uriCompute = QgsDataSourceUri()
            uriCompute.setParam('url',f"{geoserverUrl}/geoserver/{namespaceStr}/wms?version%3D1.1.1")
            uriCompute.setParam('crs','EPSG:4326')
            uriCompute.setParam('dpiMode','4')
            uriCompute.setParam('format','image/png')
            uriCompute.setParam('layers',f'{layerStr}')
            uriCompute.setParam('styles','')
            uriCompute.setParam('IgnoreGetMapUrl','1')
            layer = QgsRasterLayer(str(uriCompute.encodedUri())[2:-1],name,'wms')
        else:  #普通wms图层
            if netMode > 0:
                url = url.replace(Jl1TileUrlDict[0],Jl1TileUrlDict[netMode]) 
            wmsContent = f"type=xyz&url={requests.utils.quote(url)}&zmax=17&zmin=0"
            layer = QgsRasterLayer(wmsContent,name,'wms')
        
        self.layerTypeDict[name] = itemType
        self.project.addMapLayer(layer)

        if not isChecked:
            layer_node = self.projectLayerTreeRoot.findLayer(layer)
            if layer_node:
                print("设置图层为未选中状态")
                # 设置图层为未选中状态
                layer_node.setItemVisibilityChecked(False)
        return layer

    def saveLayerHistory(self,taskId):
        historyDict = {
            'localFileDict' : {},
            'xyzDict' : {},
            'leftKey1' : None,
            'leftKey2' : None,
            'rightKey3' : None,
            'rightKey4' : None,
        }

        for layerName,layerType in self.layerTypeDict.items():
            if layerType == Local_Type:
                tempLayer = self.project.mapLayersByName(layerName)[0]
                tempLayerSource = tempLayer.source()
                if tempLayer.type() == QgsMapLayerType.VectorLayer:
                    historyDict["localFileDict"][layerName] = tempLayerSource
                elif tempLayer.type() == QgsMapLayerType.RasterLayer:
                    if tempLayer.providerType() == 'wms':
                        historyDict['xyzDict'][layerName] = tempLayerSource
                    else:
                        historyDict['localFileDict'][layerName] = tempLayerSource
        
        historyDict['leftKey1'] = self.leftKey1
        historyDict['leftKey2'] = self.leftKey2
        historyDict['rightKey3'] = self.rightKey3
        historyDict['rightKey4'] = self.rightKey4

        savePath = osp.join(Joint_Labeling_History_Dir,f"{taskId}.yaml")
        saveYamlForDict(savePath,historyDict)
    
    def loadLayerHistory(self,taskId):
        try:
            yamlPath = osp.join(Joint_Labeling_History_Dir,f"{taskId}.yaml")
            if osp.exists(yamlPath):
                historyDict = readYamlToDict(yamlPath)

                for localName,localSource in historyDict['localFileDict'].items():
                    self.addExtraItemByFile(localSource,needMsg=False,layerName=localName)
                
                for xyzName,xyzSource in historyDict['xyzDict'].items():
                    self.addExtraItemByUrl(xyzSource,xyzName,isLocalType=True,isChecked=True,preSource=True)

                self.leftKey1 = historyDict['leftKey1']
                self.leftKey2 = historyDict['leftKey2']
                self.rightKey3 = historyDict['rightKey3']
                self.rightKey4 = historyDict['rightKey4']
        except Exception as e:
            print(e)
                


class yoyiMenuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self,yoyiLayerTree:YoyiTreeView,yoyiTrs:yoyiTrans, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.yoyiLayerTree = yoyiLayerTree

        self.layerTreeView: QgsLayerTreeView = yoyiLayerTree.layerTreeView
        self.mapCanvas: QgsMapCanvas = yoyiLayerTree.mapCanvas
        self.extraMapCanvas = self.yoyiLayerTree.extraMapCanvas
        self.yoyiTrs = yoyiTrs
    
    def createContextMenu(self):
        try:
            menu = RoundMenu(parent=self.layerTreeView)
            self.actions : QgsLayerTreeViewDefaultActions = self.layerTreeView.defaultActions()
            if not self.layerTreeView.currentIndex().isValid():
                # 添加组
                actionAddGroup = self.actions.actionAddGroup(menu)
                actionAddGroup.setText(self.yoyiTrs._translate('添加组'))
                menu.addAction(actionAddGroup)

                actionExpandAllNodes = Action(QIcon(":/img/resources/menu_expand.png"), self.yoyiTrs._translate('展开'))
                actionExpandAllNodes.triggered.connect(self.layerTreeView.expandAllNodes)
                menu.addAction(actionExpandAllNodes)
                actionCollapseAllNodes = Action(QIcon(":/img/resources/menu_collapse.png"), self.yoyiTrs._translate('折叠'))
                actionCollapseAllNodes.triggered.connect(self.layerTreeView.collapseAllNodes)
                menu.addAction(actionCollapseAllNodes)

                curPos: QPoint = QCursor.pos()
                menu.exec_(QPoint(curPos.x(), curPos.y()), aniType=MenuAnimationType.NONE)
                return
            
            if len(self.layerTreeView.selectedLayers()) > 1:
                # 添加组
                self.actionGroupSelected = self.actions.actionGroupSelected()
                self.actionGroupSelected.setText(self.yoyiTrs._translate('将选中为组'))
                menu.addAction(self.actionGroupSelected)

                actionDeleteSelectedLayers = Action(QIcon(":/img/resources/menu_close.png"), self.yoyiTrs._translate('移除选中图层'))
                actionDeleteSelectedLayers.triggered.connect(self.deleteSelectedLayer)
                menu.addAction(actionDeleteSelectedLayers)
                curPos: QPoint = QCursor.pos()
                menu.exec_(QPoint(curPos.x(), curPos.y()), aniType=MenuAnimationType.NONE)
                return
            
            node: QgsLayerTreeNode = self.layerTreeView.currentNode()
            if node:
                if QgsLayerTree.isGroup(node):
                    group: QgsLayerTreeGroup = self.layerTreeView.currentGroupNode()
                    self.actionRenameGroup = self.actions.actionRenameGroupOrLayer(menu)
                    self.actionRenameGroup.setText(self.yoyiTrs._translate("重命名组"))

                    menu.addAction(self.actionRenameGroup)
                    actionDeleteGroup = QAction(self.yoyiTrs._translate('删除组'), menu)
                    actionDeleteGroup.triggered.connect(lambda: self.deleteGroup(group))
                    menu.addAction(actionDeleteGroup)
                elif QgsLayerTree.isLayer(node):

                    layer: QgsMapLayer = self.layerTreeView.currentLayer()
                    
                    print(layer)
                    layerName = layer.name()
                    layerType = self.yoyiLayerTree.layerTypeDict[layerName]
                    actionZoomToLayer = Action(QIcon(":/img/resources/menu_zoomToLayer.png"), self.yoyiTrs._translate('缩放到图层'))
                    actionZoomToLayer.triggered.connect(lambda: self.zoomToLayer(layer))
                    menu.addAction(actionZoomToLayer)

                    if layerType == Local_Type:
                        actionDeleteLayer = Action(QIcon(":/img/resources/menu_close.png"), self.yoyiTrs._translate('移除选中图层'))
                        actionDeleteLayer.triggered.connect(lambda: self.deleteLayer(layer))
                        menu.addAction(actionDeleteLayer)

                    if layer.type() == QgsMapLayerType.VectorLayer:
                        actionOpenAttributeDialog = Action(QIcon(":/img/resources/menu_tabel.png"), self.yoyiTrs._translate('打开属性表'))
                        actionOpenAttributeDialog.triggered.connect(lambda: self.openAttributeDialog(layer))
                        menu.addAction(actionOpenAttributeDialog)

                        actionLabeling = Action(FIF.FONT_SIZE,self.yoyiTrs._translate('标注'))
                        actionLabeling.triggered.connect(lambda: self.openLabelingDialog(layer))
                        menu.addAction(actionLabeling)

                        actionSelecMapTool = Action(QIcon(':/img/resources/gis/shp_select_multi.png'),self.yoyiTrs._translate('选择要素'))
                        actionSelecMapTool.triggered.connect(lambda: self.yoyiLayerTree.parentWindow.selectLocalVectorMapToolClicked(layer))
                        menu.addAction(actionSelecMapTool)
                    
                    if layer.type() == QgsMapLayerType.RasterLayer:
                        if self.yoyiLayerTree.openQuickKey:
                            if self.yoyiLayerTree.leftKey1 == layerName:
                                leftKey1Action = Action("√ 取消绑定1键")
                                leftKey1Action.triggered.connect(self.cancelBindKey1)
                            else:
                                leftKey1Action = Action("绑定到1键位")
                                leftKey1Action.triggered.connect(lambda: self.bindKey1(layerName) )
                            menu.addAction(leftKey1Action)

                            if self.yoyiLayerTree.leftKey2 == layerName:
                                leftKey2Action = Action("√ 取消绑定2键")
                                leftKey2Action.triggered.connect(self.cancelBindKey2)
                            else:
                                leftKey2Action = Action("绑定到2键位")
                                leftKey2Action.triggered.connect(lambda: self.bindKey2(layerName) )
                            menu.addAction(leftKey2Action)

                            if self.yoyiLayerTree.rightKey3 == layerName:
                                leftKey3Action = Action("√ 取消绑定3键")
                                leftKey3Action.triggered.connect(self.cancelBindKey3)
                            else:
                                leftKey3Action = Action("绑定到3键位")
                                leftKey3Action.triggered.connect(lambda: self.bindKey3(layerName) )
                            menu.addAction(leftKey3Action)

                            if self.yoyiLayerTree.rightKey4 == layerName:
                                leftKey4Action = Action("√ 取消绑定4键")
                                leftKey4Action.triggered.connect(self.cancelBindKey4)
                            else:
                                leftKey4Action = Action("绑定到4键位")
                                leftKey4Action.triggered.connect(lambda: self.bindKey4(layerName) )
                            menu.addAction(leftKey4Action)


                    actionOpenLayerProp = Action(QIcon(":/img/resources/menu_prop.png"), self.yoyiTrs._translate('属性'))
                    actionOpenLayerProp.triggered.connect(lambda : self.openLayerPropTriggered(layer))
                    menu.addAction(actionOpenLayerProp)

            curPos: QPoint = QCursor.pos()
            menu.exec_(QPoint(curPos.x(), curPos.y()), aniType=MenuAnimationType.NONE)
            return
        except Exception as e:
            print(traceback.format_exc())
    
    # Outside
    def deleteSelectedLayer(self):
        layers = self.layerTreeView.selectedLayers()
        if len(layers) == 0:
            MessageBox(self.yoyiTrs._translate('信息'),self.yoyiTrs._translate('当前未选中图层'),self.yoyiLayerTree.parentWindow).exec()
            return
        reply = MessageBox(self.yoyiTrs._translate('信息'),self.yoyiTrs._translate('确定要移除图层？'),self.yoyiLayerTree.parentWindow)
        reply.yesButton.setText(self.yoyiTrs._translate('确认'))
        reply.cancelButton.setText(self.yoyiTrs._translate('取消'))
        if reply.exec():
            if self.mapCanvas.mapTool() and (type(self.mapCanvas.mapTool()) in [IdentifyRasterMapTool,QgsMapToolIdentifyFeature]): 
                self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
            for layer in layers:
                name = layer.name()
                if self.yoyiLayerTree.layerTypeDict[name] == Local_Type:
                    self.deleteLayer(layer)

    def deleteLayer(self,layer:QgsMapLayer):
        if self.mapCanvas.mapTool() and (type(self.mapCanvas.mapTool()) in [IdentifyRasterMapTool,QgsMapToolIdentifyFeature]): 
            self.mapCanvas.unsetMapTool(self.mapCanvas.mapTool())
        
        self.yoyiLayerTree.layerTypeDict.pop(layer.name())
        if self.yoyiLayerTree.leftKey1 == layer.name():
            self.yoyiLayerTree.leftKey1 = None
        if self.yoyiLayerTree.leftKey2 == layer.name():
            self.yoyiLayerTree.leftKey2 = None
        if self.yoyiLayerTree.rightKey3 == layer.name():
            self.yoyiLayerTree.rightKey3 = None
        if self.yoyiLayerTree.rightKey4 == layer.name():
            self.yoyiLayerTree.rightKey4 = None
        
        self.yoyiLayerTree.project.removeMapLayer(layer)

    # Node
    def zoomToLayer(self,layer):
        mapSetting: QgsMapSettings = self.mapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        crsDest = layer.crs()
        transformContext = PROJECT.transformContext()
        xform = QgsCoordinateTransform(crsDest, mapCrs, transformContext)
        trueExtent = xform.transformBoundingBox(layer.extent())
        self.mapCanvas.setExtent(trueExtent)
        self.mapCanvas.refresh()
        if self.extraMapCanvas:
            self.extraMapCanvas.setExtent(trueExtent)
            self.extraMapCanvas.refresh()
    
    def openAttributeDialog(self, layer):
        ad = AttributeDialog(self.yoyiLayerTree.parentWindow,self.mapCanvas, layer,self.extraMapCanvas)
        ad.show()

    def openLayerPropTriggered(self, layer:QgsMapLayer):
        lp = LayerPropWindowWidgeter(layer, self.mapCanvas,self.yoyiTrs,extraMapCanvas=self.extraMapCanvas,parent=self.yoyiLayerTree.parentWindow)
        lp.show()
    
    def openLabelingDialog(self,layer):
        labelingDialog = ShpLabelingDialogClass(self.yoyiTrs,layer,self.mapCanvas,self.yoyiLayerTree.parentWindow)
        labelingDialog.exec()
    
    def bindKey1(self,name):
        self.yoyiLayerTree.leftKey1 = name
    
    def bindKey2(self,name):
        self.yoyiLayerTree.leftKey2 = name
    
    def bindKey3(self,name):
        self.yoyiLayerTree.rightKey3 = name
    
    def bindKey4(self,name):
        self.yoyiLayerTree.rightKey4 = name
    
    def cancelBindKey1(self):
        self.yoyiLayerTree.leftKey1 = None
    
    def cancelBindKey2(self):
        self.yoyiLayerTree.leftKey2 = None
    
    def cancelBindKey3(self):
        self.yoyiLayerTree.rightKey3 = None
    
    def cancelBindKey4(self):
        self.yoyiLayerTree.rightKey4 = None

    # Group
    def deleteGroup(self,group:QgsLayerTreeGroup):
        reply = MessageBox(self.yoyiTrs._translate('信息'),self.yoyiTrs._translate('确定要删除组？'),self.yoyiLayerTree.parentWindow)
        reply.yesButton.setText(self.yoyiTrs._translate('确认'))
        reply.cancelButton.setText(self.yoyiTrs._translate('取消'))
        if reply.exec():
            self.yoyiLayerTree.projectLayerTreeRoot.removeChildNode(group)
        

class YoyiTreeLayerWidget(TreeWidget):
    treeChanged = pyqtSignal(str)
    
    def __init__(self,mapcanvas,yoyiTrs:yoyiTrans,parent=None,extraMapCanvas=None,openQuickKey=False):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.parentWindow = parent
        self.mapcanvas : QgsMapCanvas = mapcanvas
        self.yoyiTrs = yoyiTrs
        self.extraMapCanvas : QgsMapCanvas = extraMapCanvas

        self.openQuickKey = openQuickKey
        self.leftActiveKey = None
        self.rightActiveKey = None
        self.leftKey1 = None
        self.leftKey2 = None
        self.rightKey3 = None
        self.rightKey4 = None

        # 停止渲染
        self.stopRender = False

        #self.itemDoubleClicked.connect(self.itemDoubleClickedFunc)
        
        self.initMember()
        self.initLevelI()
    
    def initMember(self):

        # 存储本地图层
        self.layerDict : dict[str:QgsMapLayer] = {}

        # 画布的底图
        self.bottomLayer = None
        # 额外画布的底图
        self.extraBottomLayer = None
        # 作业矢量
        self.drawBottomLayer = None
        # 渔网
        self.fishnetBottomLayer = None

        self.yspc = yoyiShpPropClass()
    
    def initLevelI(self):
        self.extraLevelINode = QTreeWidgetItem(self,["额外图层"],type=1)
        self.extraLevelINode.setFlags(self.extraLevelINode.flags() &~Qt.ItemIsSelectable)
        self.extraLevelINode.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        self.addTopLevelItem(self.extraLevelINode)

        self.bottomLevelINode = QTreeWidgetItem(self,["底图图层"],type=1)
        self.bottomLevelINode.setFlags(self.bottomLevelINode.flags() &~Qt.ItemIsSelectable)
        self.bottomLevelINode.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        self.addTopLevelItem(self.bottomLevelINode)
    
    def clearLevelI(self):
        self.layerDict = {}
        self.extraLevelINode.takeChildren()
        self.bottomLevelINode.takeChildren()
        del self.bottomLayer
        del self.extraBottomLayer
        del self.drawBottomLayer
        del self.fishnetBottomLayer
        # 画布的底图
        self.bottomLayer = None
        # 额外画布的底图
        self.extraBottomLayer = None
        # 作业矢量
        self.drawBottomLayer : QgsVectorLayer = None
        # 渔网
        self.fishnetBottomLayer = None
        # 快捷绑定
        self.leftActiveKey = None
        self.rightActiveKey = None
        self.leftKey1 = None
        self.leftKey2 = None
        self.rightKey3 = None
        self.rightKey4 = None
    
    def initBottomLayer(self):
        self.stopRender = True
        self.drawBottomItem = QTreeWidgetItem(self.bottomLevelINode,[self.drawBottomLayer.name()],type=Bottom_Draw)
        self.drawBottomItem.setCheckState(0, Qt.CheckState.Checked)
        self.drawBottomItem.setFlags(self.drawBottomItem.flags() &~Qt.ItemIsDropEnabled)
        self.addTopLevelItem(self.drawBottomItem)

        if self.fishnetBottomLayer:
            self.fishnetBottomItem = QTreeWidgetItem(self.bottomLevelINode,[self.fishnetBottomLayer.name()],type=Bottom_Fishnet)
            self.fishnetBottomItem.setCheckState(0, Qt.CheckState.Checked)
            self.fishnetBottomItem.setFlags(self.fishnetBottomItem.flags() &~Qt.ItemIsDropEnabled)
            self.addTopLevelItem(self.fishnetBottomItem)
        
        self.bottomLayerItem = QTreeWidgetItem(self.bottomLevelINode,["底图影像"],type=Bottom_Tif)
        self.bottomLayerItem.setFlags(self.bottomLayerItem.flags() &~Qt.ItemIsDropEnabled)
        self.addTopLevelItem(self.bottomLayerItem)
        
        if self.extraMapCanvas:
            self.bottomLayerItem2 = QTreeWidgetItem(self.bottomLevelINode,["底图影像-右"],type=Bottom_Tif2)
            self.bottomLayerItem2.setFlags(self.bottomLayerItem2.flags() &~Qt.ItemIsDropEnabled)
            self.addTopLevelItem(self.bottomLayerItem2)
        
        self.bottomLevelINode.setExpanded(True)
        self.stopRender = False

    def retranslateDIYUI(self,yoyiTrs:yoyiTrans):
        self.yoyiTrs = yoyiTrs
        self.extraLevelINode.setText(0,self.yoyiTrs._translate("额外图层"))
        self.bottomLevelINode.setText(0,self.yoyiTrs._translate("底图图层"))

    def setDrawBottomLayer(self,usePreRender=None):
        print(usePreRender)
        if type(usePreRender) == QgsSingleSymbolRenderer:
            color = usePreRender.symbol().color()
            tempPixmap = QPixmap(20, 20)
            tempPixmap.fill(color)
            self.drawBottomItem.setIcon(0,QIcon(tempPixmap))
            self.drawBottomLayer.setRenderer(usePreRender)
        elif usePreRender:
            self.drawBottomItem.setIcon(0,QIcon(":/img/resources/open_shp.png"))
            self.drawBottomLayer.setRenderer(usePreRender)
        else:
            colorR = 255
            colorG = 0
            colorB = 0
            color = QColor(colorR, colorG, colorB)
            renderOutline = 0.7
            tempPixmap = QPixmap(20, 20)
            tempPixmap.fill(color)
            self.drawBottomItem.setIcon(0,QIcon(tempPixmap))
            self.drawBottomLayer.setRenderer(self.yspc.createDiySymbol(color=f"{colorR},{colorG},{colorB}",
                                  lineWidth=str(renderOutline),isFull=False))
            
    
    def setFishnetBottomLayer(self):
        tempPixmap = QPixmap(20, 20)
        tempPixmap.fill(QColor(74,111,163))
        self.fishnetBottomItem.setIcon(0,QIcon(tempPixmap))
        self.fishnetBottomLayer.setRenderer(self.yspc.createDiySymbol("74,111,163", lineWidth='0.7', isFull=False))

    def dragMoveEvent(self,event:QDragMoveEvent):
        sourceItem = self.currentItem()
        targetItem = self.itemAt(event.pos())
        if sourceItem and targetItem:
            if not sourceItem.parent() or not targetItem.parent():
                event.ignore()
            elif sourceItem.parent() != targetItem.parent():
                event.ignore()
            elif sourceItem.type() >3: # wmsType 和 localType  是 2 3  大于3就不是这俩了
                event.ignore()
            else:
                super().dragMoveEvent(event)
    
    def dropEvent(self, event: QDropEvent) -> None:
        sourceItem = self.currentItem()
        targetItem = self.itemAt(event.pos())
        if sourceItem and targetItem:
            if not sourceItem.parent() or not targetItem.parent():
                event.ignore()
            elif sourceItem.parent() != targetItem.parent():
                event.ignore()
            elif sourceItem.type() >3:
                event.ignore()
            else:
                super().dropEvent(event)
                self.treeChanged.emit("")
    
    def getLayerByType(self,itemType):
        if itemType == Bottom_Draw:
            return self.drawBottomLayer
        elif itemType == Bottom_Fishnet:
            return self.fishnetBottomLayer
        elif itemType == Bottom_Tif:
            return self.bottomLayer
        elif itemType == Bottom_Tif2:
            return self.extraBottomLayer

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super().mousePressEvent(e)
        if e.button() == Qt.MouseButton.RightButton:
            cusMenu = RoundMenu(parent=self)
            cusMenu.setItemHeight(50)
            if len(self.selectedItems())==1:
                tempItem = self.selectedItems()[0]
                if tempItem.type() == Local_Type:

                    deleteSelectedLayerTriggered = Action(QIcon(":/img/resources/menu_close.png"), self.yoyiTrs._translate("清除图层"))
                    deleteSelectedLayerTriggered.triggered.connect(self.deleteSelectedLayerTriggered)
                    cusMenu.addAction(deleteSelectedLayerTriggered)
                    
                    tempLayer: QgsMapLayer = self.layerDict[tempItem.text(0)]
                elif tempItem.type() == Wms_Type:
                    tempLayer: QgsMapLayer = self.layerDict[tempItem.text(0)]
                else:
                    tempLayer: QgsMapLayer = self.getLayerByType(tempItem.type())

                if tempLayer:
                    scaleToLayer = Action(FIF.FULL_SCREEN, self.yoyiTrs._translate("缩放到图层"))
                    scaleToLayer.triggered.connect(lambda: self.scaleToLayerTriggered(tempLayer))
                    cusMenu.addAction(scaleToLayer)

                    if tempLayer.type() == QgsMapLayerType.VectorLayer:
                        vectorRenderAction = Action(QIcon(":/img/resources/menu_prop.png"),self.yoyiTrs._translate("属性"))
                        vectorRenderAction.triggered.connect(lambda: self.vectorRenderActionTriggered(tempLayer))
                        cusMenu.addAction(vectorRenderAction)
                        actionOpenAttributeDialog = Action(QIcon(":/img/resources/menu_tabel.png"), self.yoyiTrs._translate('打开属性表'))
                        actionOpenAttributeDialog.triggered.connect(lambda: self.openAttributeDialog(tempLayer))
                        cusMenu.addAction(actionOpenAttributeDialog)
                        actionLabeling = Action(FIF.FONT_SIZE,self.yoyiTrs._translate('标注'))
                        actionLabeling.triggered.connect(lambda: self.openLabelingDialog(tempLayer))
                        cusMenu.addAction(actionLabeling)
                    elif tempLayer.type() == QgsMapLayerType.RasterLayer:
                        
                        if self.openQuickKey:
                            if self.leftKey1 == tempItem.text(0):
                                leftKey1Action = Action("√ 已绑定1键位")
                            else:
                                leftKey1Action = Action("绑定到1键位")
                                leftKey1Action.triggered.connect(lambda: self.bindLeftKey1(tempItem.text(0)) )
                            cusMenu.addAction(leftKey1Action)

                            if self.leftKey2 == tempItem.text(0):
                                leftKey2Action = Action("√ 已绑定2键位")
                            else:
                                leftKey2Action = Action("绑定到2键位")
                                leftKey2Action.triggered.connect(lambda: self.bindLeftKey2(tempItem.text(0)) )
                            cusMenu.addAction(leftKey2Action)

                            if self.rightKey3 == tempItem.text(0):
                                rightKey3Action = Action("√ 已绑定3键位")
                            else:
                                rightKey3Action = Action("绑定到3键位")
                                rightKey3Action.triggered.connect(lambda: self.bindRightKey3(tempItem.text(0)) )
                            cusMenu.addAction(rightKey3Action)

                            if self.rightKey4 == tempItem.text(0):
                                rightKey4Action = Action("√ 已绑定4键位")
                            else:
                                rightKey4Action = Action("绑定到4键位")
                                rightKey4Action.triggered.connect(lambda: self.bindRightKey4(tempItem.text(0)) )
                            cusMenu.addAction(rightKey4Action)

                        rasterRenderAction = Action(QIcon(":/img/resources/menu_prop.png"),self.yoyiTrs._translate("属性"))
                        rasterRenderAction.triggered.connect(lambda : self.openLayerPropTriggered(tempLayer))
                        cusMenu.addAction(rasterRenderAction)
            curPos: QPoint = QCursor.pos()
            cusMenu.exec_(QPoint(curPos.x(), curPos.y()), aniType=MenuAnimationType.NONE)
    
    def bindLeftKey1(self,name):
        self.leftKey1 = name
    
    def bindLeftKey2(self,name):
        self.leftKey2 = name

    def bindRightKey3(self,name):
        self.rightKey3 = name

    def bindRightKey4(self,name):
        self.rightKey4 = name 

    # def itemDoubleClickedFunc(self,tempItem,column):
    #     tempLayer = None
    #     if tempItem.type() == Local_Type or tempItem.type() == Wms_Type:
    #         tempLayer: QgsMapLayer = self.layerDict[tempItem.text(0)]
    #     else:
    #         tempLayer: QgsMapLayer = self.getLayerByType(tempItem.type())

    #     if tempLayer:
    #         if tempLayer.type() == QgsMapLayerType.VectorLayer:
    #             self.vectorRenderActionTriggered(tempLayer)
    #         else:
    #             self.openLayerPropTriggered(tempLayer)

    def deleteSelectedLayerTriggered(self):
        if len(self.selectedItems()) == 1:
            item : QTreeWidgetItem = self.selectedItems()[0]
            if item.type() == Local_Type:
                self.layerDict.pop(item.text(0))
                self.extraLevelINode.removeChild(item)
        
        elif len(self.selectedItems()) > 1:
            for item in self.selectedItems():
                if item.type() == Local_Type:
                    self.layerDict.pop(item.text(0))
                    self.extraLevelINode.removeChild(item)
        
        self.extraLevelINode.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        self.treeChanged.emit("")

    def scaleToLayerTriggered(self,layer:QgsMapLayer):
        crsDest = layer.crs()
        transformContext = PROJECT.transformContext()
        xform = QgsCoordinateTransform(crsDest, self.mapcanvas.mapSettings().destinationCrs(), transformContext)
        trueExtent = xform.transformBoundingBox(layer.extent())
        print(trueExtent)
        self.mapcanvas.setExtent(trueExtent)
        self.mapcanvas.refresh()
        if self.extraMapCanvas:
            self.extraMapCanvas.setExtent(trueExtent)
            self.extraMapCanvas.refresh()
            
    def vectorRenderActionTriggered(self,layer:QgsMapLayer):
        dialog = LayerPropWindowWidgeter(layer, self.mapcanvas,self.yoyiTrs,extraMapCanvas=self.extraMapCanvas,parent=self)
        dialog.shpRenderChanged.connect(self.shpRenderChangedFunc)
        dialog.show()
    
    def openAttributeDialog(self, layer):
        ad = AttributeDialog(self.parentWindow,self.mapcanvas, layer,self.extraMapCanvas)
        ad.show()
    
    def openLabelingDialog(self,layer):
        labelingDialog = ShpLabelingDialogClass(yoyiTrans(),layer,self.mapcanvas,self.parentWindow)
        labelingDialog.exec()

    def shpRenderChangedFunc(self,list):
        layerName,color = list
        item : QTreeWidgetItem = self.findItems(layerName,Qt.MatchFlag.MatchRecursive | Qt.MatchFlag.MatchExactly,0)[0]
        if color is None:
            item.setIcon(0,QIcon(":/img/resources/open_shp.png"))
        else:
            tempPixmap = QPixmap(20, 20)
            tempPixmap.fill(color)
            item.setIcon(0,QIcon(tempPixmap))
        
    
    def openLayerPropTriggered(self, layer:QgsMapLayer):
        lp = LayerPropWindowWidgeter(layer, self.mapcanvas,self.yoyiTrs,extraMapCanvas=self.extraMapCanvas,parent=self)
        lp.show()
    
    def addExtraItemByUrl(self,url:QgsDataSourceUri,name,needScaleToExtent=False,isLocalType=True,isChecked=True,isInsert=True):
        if isLocalType:
            itemType = Local_Type
        else:
            itemType = Wms_Type
        index = 1
        while name in self.layerDict.keys():
            name = name + f"_{index}"
            index += 1
        item = QTreeWidgetItem([name],type=itemType)
        if type(url) == QgsDataSourceUri:
            layer = QgsRasterLayer(str(url.encodedUri())[2:-1],name,'wms')
        else:
            netMode = yoyiSetting().configSettingReader.value('netMode',type=int)
            if netMode > 0:
                url = url.replace(Jl1TileUrlDict[0],Jl1TileUrlDict[netMode]) 
            wmsContent = f"type=xyz&url={requests.utils.quote(url)}&zmax=17&zmin=0"
            layer = QgsRasterLayer(wmsContent,name,'wms')

        self.layerDict[name] = layer

        item.setIcon(0,QIcon(":/img/resources/open_tif.png"))
        item.setCheckState(0, Qt.CheckState.Checked if isChecked else Qt.CheckState.Unchecked)
        item.setFlags(item.flags() &~Qt.ItemIsDropEnabled)
        
        if isInsert:
            self.extraLevelINode.insertChild(0,item)
        else:
            self.extraLevelINode.addChild(item)

        self.extraLevelINode.setExpanded(True)
        
        if needScaleToExtent:
            crsDest = layer.crs()
            transformContext = PROJECT.transformContext()
            xform = QgsCoordinateTransform(crsDest, self.mapcanvas.mapSettings().destinationCrs(), transformContext)
            trueExtent = xform.transformBoundingBox(layer.extent())
            self.mapcanvas.setExtent(trueExtent)
            if self.extraMapCanvas:
                self.extraMapCanvas.setExtent(trueExtent)
        
        if isInsert:
            self.treeChanged.emit("")
        return layer

    def addExtraItemByFile(self,file,needScaleToExtent=False,attrMapping=None,isInsert=True):
        tempName = osp.basename(file).split(".")[0]
        tempPost = osp.basename(file).split(".")[-1]
        index = 1
        
        while tempName+"."+tempPost in self.layerDict.keys():
            tempName = tempName + f"_{index}"
            index += 1

        item = QTreeWidgetItem([tempName+"."+tempPost],type=2)
        if tempPost in ['shp','SHP','geojson','gpkg']: 
            layer = QgsVectorLayer(file, tempName+"."+tempPost, "ogr")
            layer.setProviderEncoding('utf-8')
            item.setIcon(0,QIcon(":/img/resources/open_shp.png"))
            #random.seed(time.time())
            #tempR = random.randint(1, 254)
            #tempG = random.randint(1, 254)
            #tempB = random.randint(1, 254)
            #tempPixmap = QPixmap(20, 20)
            #tempPixmap.fill(QColor(tempR,tempG,tempB))
            #item.setIcon(0,QIcon(tempPixmap))

            #layer.setRenderer(self.yspc.createDiySymbol(f"{tempR},{tempG},{tempB}",lineWidth='0.7', isFull=False))

            #item.setIcon(0,QIcon(tempPixmap))
            
        elif tempPost in ['tif','TIF','tiff','TIFF']:
            layer = QgsRasterLayer(file,tempName+"."+tempPost)
            if attrMapping and layer.bandCount() == 1:
                pcolor = []
                random.seed(time.time())
                for name,pixelValue in attrMapping.items():
                    tempR = random.randint(1, 254)
                    tempG = random.randint(1, 254)
                    tempB = random.randint(1, 254)
                    pcolor.append(QgsColorRampShader.ColorRampItem(pixelValue, QColor(tempR,tempG,tempB),name))
                tempRenderer = QgsPalettedRasterRenderer(layer.dataProvider(),
                                                         1,
                                                         QgsPalettedRasterRenderer.colorTableToClassData(pcolor))
                layer.setRenderer(tempRenderer)

            item.setIcon(0,QIcon(":/img/resources/open_tif.png"))

        self.layerDict[tempName+"."+tempPost] = layer
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setFlags(item.flags() &~Qt.ItemIsDropEnabled)

        if isInsert:
            self.extraLevelINode.insertChild(0,item)
        else:
            self.extraLevelINode.addChild(item)
        self.extraLevelINode.setExpanded(True)
        
        if needScaleToExtent:
            crsDest = layer.crs()
            transformContext = PROJECT.transformContext()
            xform = QgsCoordinateTransform(crsDest, self.mapcanvas.mapSettings().destinationCrs(), transformContext)
            trueExtent = xform.transformBoundingBox(layer.extent())
            self.mapcanvas.setExtent(trueExtent)
            if self.extraMapCanvas:
                self.extraMapCanvas.setExtent(trueExtent)
        self.treeChanged.emit("")
        return tempName
    
    def getLayers(self,extraMode=False):
        resList = []
        
        if self.drawBottomLayer and self.bottomLayer:
            if self.drawBottomItem.checkState(0) == Qt.CheckState.Checked:
                resList.append(self.drawBottomLayer)
                
            for i in range(self.extraLevelINode.childCount()):
                item : QTreeWidgetItem = self.extraLevelINode.child(i)
                if item.parent():
                    if item.checkState(0) == Qt.CheckState.Checked:
                        resList.append(self.layerDict[item.text(0)])

            if self.fishnetBottomLayer and self.fishnetBottomItem.checkState(0) == Qt.CheckState.Checked:
                resList.append(self.fishnetBottomLayer)
            
            if extraMode:
                if self.rightActiveKey == 3:
                    resList.append(self.layerDict[self.rightKey3])
                elif self.rightActiveKey == 4:
                    resList.append(self.layerDict[self.rightKey4])

                if self.extraBottomLayer:
                    resList.append(self.extraBottomLayer)
            else:
                if self.leftActiveKey == 1:
                    resList.append(self.layerDict[self.leftKey1])
                elif self.leftActiveKey == 2:
                    resList.append(self.layerDict[self.leftKey2])

                if self.bottomLayer:
                    resList.append(self.bottomLayer)
        return resList
    

class AvatarTextWidget(NavigationWidget):
    """ Avatar widget """

    def __init__(self, text: str, img: QImage = None, parent=None):
        super().__init__(isSelectable=False, parent=parent)
        self.text = text
        self.avatar = img
        if self.avatar:
            self.avatar = self.avatar.scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.setStyleSheet("AvatarWidget{font: 14px 'Segoe UI', 'Microsoft YaHei'}")

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.SmoothPixmapTransform | QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)

        if self.isPressed:
            painter.setOpacity(0.7)

        # draw background
        if self.isEnter:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        # draw avatar
        painter.translate(8, 6)

        if self.avatar:
            painter.setBrush(QBrush(self.avatar))
            painter.drawEllipse(0, 0, 24, 24)
        else:
            c = 255 if isDarkTheme() else 0
            painter.setBrush(QColor(c, c, c, 50))
            painter.drawEllipse(0, 0, 24, 24)

            font = QFont(self.font())
            font.setPixelSize(12)
            painter.setFont(font)
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)
            painter.drawText(QRect(0, 0, 24, 24), Qt.AlignCenter, self.text[0].upper())

        painter.translate(-8, -6)

        if not self.isCompacted:
            painter.setPen(Qt.white if isDarkTheme() else Qt.black)
            painter.setFont(self.font())
            painter.drawText(QRect(44, 0, 255, 36), Qt.AlignVCenter, self.text)
            

class BetterCardWidget(BackgroundAnimationWidget, QFrame):

    clicked = pyqtSignal()
    checkChanged = pyqtSignal()

    def __init__(self,isCheckable,text,iconPath,w=60,h=60, parent=None,iconSize=None,disableIconPath=None,shortcut=None):
        super().__init__(parent)
        self._borderRadius = 5
        self._isClickEnabled = True
        self.isCheckable = isCheckable
        self.checked = False

        self.text = text
        self.iconPath = iconPath

        self.setMinimumSize(QtCore.QSize(w, h))
        self.setMaximumSize(QtCore.QSize(w, h))
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(1,4,1,1)

        self.IconWidget = IconWidget(self)
        self.commonIcon = QIcon(self.iconPath)
        if disableIconPath:
            self.disableIcon = QIcon(disableIconPath)
        else:
            self.disableIcon = None

        self.IconWidget.setIcon(self.commonIcon)

        if iconSize:
            self.IconWidget.setMinimumHeight(iconSize)
            self.IconWidget.setMaximumHeight(iconSize)
        else:
            self.IconWidget.setMinimumHeight(h-30)
            self.IconWidget.setMaximumHeight(h-30)
        self.verticalLayout.addWidget(self.IconWidget)
        self.BodyLabel = BodyLabel(self)
        self.BodyLabel.setMinimumSize(QtCore.QSize(16777215, 9))
        self.BodyLabel.setMaximumSize(QtCore.QSize(16777215, 30))
        self.BodyLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.BodyLabel.setText(self.text)
        font = QFont(self.BodyLabel.font())
        font.setPointSize(8)
        self.BodyLabel.setFont(font)
        self.BodyLabel.setWordWrap(True)
        self.verticalLayout.addWidget(self.BodyLabel)
    
        if shortcut:
            self.shortcut = QShortcut(QKeySequence(shortcut),self.parent())
            self.shortcut.activated.connect(self.click)
            self.setToolTip("快捷键(ShortCut): "+shortcut)
            self.installEventFilter(ToolTipFilter(self,0))
    
    def setEnabled(self, a0: bool) -> None:
        if self.disableIcon:
            if a0:
                self.IconWidget.setIcon(self.commonIcon)
            else:
                self.IconWidget.setIcon(self.disableIcon)
        return super().setEnabled(a0)

    def mouseReleaseEvent(self, e):
        if self.isCheckable:
            self.checked = not self.checked
            self.checkChanged.emit()
        super().mouseReleaseEvent(e)
        self.clicked.emit()
    
    def click(self):
        event = QMouseEvent(QEvent.Type.MouseButtonPress,self.pos(),Qt.LeftButton,Qt.LeftButton,Qt.NoModifier)
        QApplication.postEvent(self,event)

        event = QMouseEvent(QEvent.Type.MouseButtonRelease,self.pos(),Qt.LeftButton,Qt.LeftButton,Qt.NoModifier)
        QApplication.postEvent(self,event)

        
    def setClickEnabled(self, isEnabled: bool):
        self._isClickEnabled = isEnabled
        self.update()
    
    def isClickEnabled(self):
        return self._isClickEnabled

    def isChecked(self):
        return self.checked

    def setChecked(self,status):
        if self.isCheckable:
            self.checked = status
            self.checkChanged.emit()
            self.paintEvent(None)
    
    def setText(self,text):
        self.BodyLabel.setText(text)
    
    def _hoverBackgroundColor(self):
        return QColor(218, 218, 218, 64 if isDarkTheme() else 64)
    
    def _normalBackgroundColor(self):
        return QColor(255, 255, 255, 13 if isDarkTheme() else 64)

    def _pressedBackgroundColor(self):
        return QColor(255, 255, 255, 8 if isDarkTheme() else 64)
    
    def getBorderRadius(self):
        return self._borderRadius

    def setBorderRadius(self, radius: int):
        self._borderRadius = radius
        self.update()
    
    def paintEvent(self, e):
        painter = QPainter(self)
        if not painter.isActive():
            print("skip this painter")
            return 
        painter.setRenderHints(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = self.borderRadius
        d = 2 * r

        isDark = isDarkTheme()

        # draw background
        painter.setPen(Qt.NoPen)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self.isChecked():
            if isDark:
                painter.setBrush(QColor(33,162,173,60))
            else:
                painter.setBrush(QColor(33,162,173,60))
        else:
            if isDark:
                painter.setBrush(QColor(33,36,33))
            else:
                painter.setBrush(self.backgroundColor)
        painter.drawRoundedRect(rect, r, r)
    
    borderRadius = pyqtProperty(int, getBorderRadius, setBorderRadius)

def getYoyiFont(fontSize=14, weight=QFont.Normal):
    """ create font

    Parameters
    ----------
    fontSize: int
        font pixel size

    weight: `QFont.Weight`
        font weight
    """
    font = QFont()
    font.setFamilies(['Segoe UI', 'Microsoft YaHei', 'PingFang SC'])
    font.setPixelSize(fontSize)
    font.setWeight(weight)
    return font

class HorizontalLabel(FluentLabelBase):
    def getFont(self):
        return getYoyiFont(14)
    
    def initLabel(self):
        self.setWordWrap(True)
        self.setMinimumWidth(27)
        self.setMaximumWidth(27)


class BetterPillToolButton(PillToolButton):
    
    def paintEvent(self, e):

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        isDark = isDarkTheme()
        if not self.isChecked():
            rect = self.rect().adjusted(1, 1, -1, -1)
            borderColor = QColor(255, 255, 255, 18) if isDark else QColor(0, 0, 0, 15)
            #borderColor = QColor(255, 255, 255, 18) if isDark else QColor(33,162,173)

            if not self.isEnabled():
                bgColor = QColor(255, 255, 255, 11) if isDark else QColor(249, 249, 249, 75)
            elif self.isPressed or self.isHover:
                bgColor = QColor(255, 255, 255, 21) if isDark else QColor(249, 249, 249, 128)
            else:
                bgColor = QColor(255, 255, 255, 15) if isDark else QColor(243, 243, 243, 194)

        else:
            if not self.isEnabled():
                bgColor = QColor(255, 255, 255, 40) if isDark else QColor(0, 0, 0, 55)
                borderColor = QColor(0, 0, 0, 15)
            elif self.isPressed:
                #bgColor = ThemeColor.DARK_2.color() if isDark else ThemeColor.LIGHT_3.color()
                bgColor = QColor(33,162,173,60)
                borderColor = QColor(33,162,173)
            elif self.isHover:
                #bgColor = ThemeColor.DARK_1.color() if isDark else ThemeColor.LIGHT_1.color()
                bgColor = QColor(33,162,173,60)
                borderColor = QColor(33,162,173)
            else:
                #bgColor = themeColor()
                bgColor = QColor(33,162,173,60)
                borderColor = QColor(33,162,173)

            #borderColor = Qt.transparent
            rect = self.rect()

        painter.setPen(Qt.transparent)
        painter.setBrush(bgColor)
        r = rect.height() / 2

        painter.drawRoundedRect(rect, r, r)

        painter.setPen(borderColor)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, r, r)
        
        ToggleToolButton.paintEvent(self, e)
    