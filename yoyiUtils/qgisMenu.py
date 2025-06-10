import os
import os.path as osp
import traceback
from shutil import copyfile

from osgeo import gdal
from datetime import datetime
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt,QPoint
from PyQt5.QtGui import QPalette,QColor,QCursor,QIcon
from PyQt5.QtWidgets import QMenu, QAction,QFileDialog,QMessageBox,QTableView,QDialog
from qgis.core import QgsLayerTreeNode, QgsLayerTree, QgsMapLayerType,QgsVectorLayer, QgsProject\
        ,QgsVectorFileWriter,QgsWkbTypes,Qgis,QgsFillSymbol,QgsSingleSymbolRenderer,QgsVectorLayerCache\
        ,QgsMapLayer,QgsRasterLayer,QgsLayerTreeGroup,QgsLayerTreeLayer,QgsCoordinateReferenceSystem,QgsCoordinateTransform,QgsMapSettings
from qgis.gui import QgsLayerTreeViewMenuProvider, QgsLayerTreeView, QgsLayerTreeViewDefaultActions, QgsMapCanvas,QgsMessageBar,\
    QgsAttributeTableModel,QgsAttributeTableView,QgsAttributeTableFilterModel,QgsGui,QgsAttributeDialog,QgsProjectionSelectionDialog,QgsMultiBandColorRendererWidget
from qfluentwidgets import MessageBox,RoundMenu, setTheme, Theme, Action, MenuAnimationType, FluentIcon, CheckableMenu, MenuIndicatorType

from yoyiUtils.attributeDialog import AttributeDialog
from yoyiUtils.yoyiTranslate import yoyiTrans
from widgets.layerPropWindowWidget import LayerPropWindowWidgeter
from widgets.draw_dialog_shpLabelingDialog import ShpLabelingDialogClass

import yoyirs_rc

PROJECT = QgsProject.instance()

class menuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self,mainWindow,yoyiTrs:yoyiTrans, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layerTreeView: QgsLayerTreeView = mainWindow.layerTreeView
        self.mapCanvas: QgsMapCanvas = mainWindow.mapCanvas
        self.mainWindows = mainWindow
        self.yoyiTrs = yoyiTrs

    def createContextMenu(self):
        try:
            menu = RoundMenu(parent=self.mainWindows)
            self.actions : QgsLayerTreeViewDefaultActions = self.layerTreeView.defaultActions()
            if not self.layerTreeView.currentIndex().isValid():
                # 清除图层 deleteAllLayer
                actionDeleteAllLayer =Action(QIcon(":/img/resources/menu_clear.png"), self.yoyiTrs._translate('清除图层'))
                actionDeleteAllLayer.triggered.connect(lambda: self.mainWindows.deleteAllLayer())
                menu.addAction(actionDeleteAllLayer)

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
                actionDeleteSelectedLayers.triggered.connect(self.mainWindows.deleteSelectedLayer)
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
                    actionZoomToLayer = Action(QIcon(":/img/resources/menu_zoomToLayer.png"), self.yoyiTrs._translate('缩放到图层'))
                    actionZoomToLayer.triggered.connect(lambda: self.zoomToLayer(layer))
                    menu.addAction(actionZoomToLayer)

                    if layer.type() == QgsMapLayerType.VectorLayer:
                        
                        actionZoomToSelected = Action(QIcon(":/img/resources/menu_zoomToLayer.png"), self.yoyiTrs._translate('缩放到选中'))
                        actionZoomToSelected.triggered.connect(lambda: self.zommToSelected(layer))
                        menu.addAction(actionZoomToSelected)

                        actionOpenAttributeDialog = Action(QIcon(":/img/resources/menu_tabel.png"), self.yoyiTrs._translate('打开属性表'))
                        actionOpenAttributeDialog.triggered.connect(lambda: self.openAttributeDialog(layer))
                        menu.addAction(actionOpenAttributeDialog)

                        actionLabeling = Action(FluentIcon.FONT_SIZE,self.yoyiTrs._translate('标注'))
                        actionLabeling.triggered.connect(lambda: self.openLabelingDialog(layer))
                        menu.addAction(actionLabeling)
                    #
                    actionOpenLayerProp = Action(QIcon(":/img/resources/menu_prop.png"), self.yoyiTrs._translate('属性'))
                    actionOpenLayerProp.triggered.connect(lambda : self.openLayerPropTriggered(layer))
                    menu.addAction(actionOpenLayerProp)

                    actionDeleteLayer = Action(QIcon(":/img/resources/menu_close.png"), self.yoyiTrs._translate('移除选中图层'))
                    actionDeleteLayer.triggered.connect(lambda: self.mainWindows.deleteLayer(layer))
                    menu.addAction(actionDeleteLayer)
                    #

            curPos: QPoint = QCursor.pos()
            menu.exec_(QPoint(curPos.x(), curPos.y()), aniType=MenuAnimationType.NONE)
            return
        except:
            print(traceback.format_exc())

    # Node
    def zoomToLayer(self,layer):
        mapSetting: QgsMapSettings = self.mapCanvas.mapSettings()
        mapCrs = mapSetting.destinationCrs()
        crsDest = layer.crs()
        transformContext = PROJECT.transformContext()
        xform = QgsCoordinateTransform(crsDest, mapCrs, transformContext)
        trueExtent = xform.transformBoundingBox(layer.extent())
        print(trueExtent)
        self.mapCanvas.setExtent(trueExtent)
        self.mapCanvas.refresh()
    
    def zommToSelected(self,layer:QgsVectorLayer):
        if layer.selectedFeatureCount() > 0:
            mapSetting: QgsMapSettings = self.mapCanvas.mapSettings()
            mapCrs = mapSetting.destinationCrs()
            crsDest = layer.crs()
            transformContext = PROJECT.transformContext()
            xform = QgsCoordinateTransform(crsDest, mapCrs, transformContext)
            trueExtent = xform.transformBoundingBox(layer.boundingBoxOfSelected())
            self.mapCanvas.setExtent(trueExtent)
            self.mapCanvas.refresh()

    def openAttributeDialog(self, layer):
        tempAttributeDialogName = "Ad_" + datetime.now().strftime('%m%d%H%M%S')
        #exec(f"self.{tempAttributeDialogName} = AttributeDialog(None,self.mapCanvas, layer)")
        # setattr(self,
        #         tempAttributeDialogName,
        #         AttributeDialog(None,self.mapCanvas, layer))
        # exec(f"self.{tempAttributeDialogName}.show()")
        self.ad = AttributeDialog(None,self.mapCanvas, layer)
        self.ad.show()

    def openLayerPropTriggered(self, layer:QgsMapLayer):
        try:
            lp = LayerPropWindowWidgeter(layer, self.mapCanvas,self.yoyiTrs,parent=self.mainWindows)
            lp.show()
        except:
            print(traceback.format_exc())
    
    def openLabelingDialog(self,layer):
        labelingDialog = ShpLabelingDialogClass(self.yoyiTrs,layer,self.mapCanvas,self.mainWindows)
        labelingDialog.exec()
    
    # Group
    def deleteGroup(self,group:QgsLayerTreeGroup):
        reply = MessageBox(self.yoyiTrs._translate('信息'),self.yoyiTrs._translate('确定要删除组？'),self.mainWindows)
        reply.yesButton.setText(self.yoyiTrs._translate('确认'))
        reply.cancelButton.setText(self.yoyiTrs._translate('取消'))
        if reply.exec():
            PROJECT.layerTreeRoot().removeChildNode(group)
