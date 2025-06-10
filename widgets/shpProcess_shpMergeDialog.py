import sys
import os
import os.path as osp

from ui.shp_process_dialog.shpMergeDialog import Ui_shpMergeDialog

from PyQt5.QtCore import Qt, QPoint,QVariant,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QFileDialog,QAbstractItemView
from PyQt5.QtGui import QFont,QIcon,QCursor

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsWkbTypes,QgsRasterLayer,QgsVectorLayer,QgsField,QgsRectangle,QgsMapSettings
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            MenuAnimationType, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,checkAllFileList
from yoyiUtils.yoyiTranslate import yoyiTrans
import yoyirs_rc

PROJECT = QgsProject.instance()

class ShpMergeDialogClass(Ui_shpMergeDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.parentMapCanvas : QgsMapCanvas = self.parentWindow.mapCanvas
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.shpList = None
        self.resPath = None
        self.crs = None 

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

        self.selectLayerMenu = RoundMenu(parent=self)
        self.selectLayerCrsMenu = RoundMenu(parent=self)
        self.mergeList = []  

        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            crsAction =  Action(text=layer.name(),parent=self)
            self.selectLayerCrsMenu.addAction(crsAction)
            if layer.type() == QgsMapLayerType.VectorLayer:
                action = Action(text=layer.name(),parent=self)
                self.selectLayerMenu.addAction(action)
        
        self.selectLayerSPB.setFlyout(self.selectLayerMenu)
        self.selectLayerCrsSPB.setFlyout(self.selectLayerCrsMenu)
        self.selectSaveFilePB.setIcon(FIF.MORE)

        # 列表
        self.slm = QStringListModel()
        self.slm.setStringList(self.mergeList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ListView.customContextMenuRequested.connect(self.on_custom_menu_requested)
    
    def connectFunc(self):
        # merge list
        self.selectLayerMenu.triggered.connect(self.selectLayerMenuTriggered)
        self.selectFilePB.clicked.connect(self.selectFilePBClicked)
        self.selectDirPB.clicked.connect(self.selectDirPBClicked)
        self.clearListViewPb.clicked.connect(self.clearListViewPbClicked)
        # crs
        self.selectLayerCrsMenu.triggered.connect(self.selectLayerCrsMenuTriggered)
        self.selectMapcanvasCrsPB.clicked.connect(self.selectMapcanvasCrsPBClicked)
        self.selectMorePB.clicked.connect(self.selectMorePBClicked)

        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.resLE,'shp',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)
    
    def on_custom_menu_requested(self,pos):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(FIF.DELETE, self.yoyiTrs._translate('删除所选'))
        deleteSelected.triggered.connect(self.deleteSource)
        cusMenu.addAction(deleteSelected)
        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)
    
    def deleteSource(self):
        curIndex = self.ListView.currentIndex().row()
        if curIndex >=0:
            self.mergeList.pop(curIndex)
            self.slm.setStringList(self.mergeList)
        else:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('未选中'), self).exec_() 
    
    def addSourceInListView(self,source):
        if source not in self.mergeList:
            self.mergeList.append(source)
            self.slm.setStringList(self.mergeList)
            self.ListView.setCurrentIndex(self.slm.index(0,0))
        else:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('路径重复'), self).exec_()
    
    def addSourceListInListView(self,sourceList):
        for source in sourceList:
            source = source.replace("\\","/")
            if source not in self.mergeList:
                self.mergeList.append(source)
        self.slm.setStringList(self.mergeList)
        self.ListView.setCurrentIndex(self.slm.index(0,0))
    
    def selectLayerMenuTriggered(self,action):
        currentLayerName = action.text()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        self.addSourceInListView(currentLayer.source())
    
    def selectFilePBClicked(self):
        file, ext = QFileDialog.getOpenFileName(self, self.yoyiTrs._translate('选择矢量文件'), "", "ShapeFile(*.shp;*SHP);;GPKG(*.gpkg);;GeoJSON(*.geojson)")
        if file:
            self.addSourceInListView(file)
    
    def selectDirPBClicked(self):
        fileDir = QFileDialog.getExistingDirectory(self, self.yoyiTrs._translate('选择文件夹'), "")
        if fileDir:
            shpList = checkAllFileList(fileDir,"extraShapeFile")
            if len(shpList) > 0:
                self.addSourceListInListView(shpList)
            else:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效矢量'), self).exec_()

    def clearListViewPbClicked(self):
        w = MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('您确定要清空吗？'), self)
        w.yesButton.setText(self.yoyiTrs._translate('确认'))
        w.cancelButton.setText(self.yoyiTrs._translate('取消'))
        if w.exec():
            self.mergeList = []
            self.slm.setStringList(self.mergeList)
    # crs
    def selectLayerCrsMenuTriggered(self,action):
        currentLayerName = action.text()
        currentLayer : QgsVectorLayer = PROJECT.mapLayersByName(currentLayerName)[0]
        currentCrs = currentLayer.crs().authid()
        self.targetCrsLE.setText(currentCrs)
    
    def selectMapcanvasCrsPBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        self.targetCrsLE.setText(mapSetting.destinationCrs().authid())

    def selectMorePBClicked(self):
        mapSetting : QgsMapSettings = self.parentMapCanvas.mapSettings()
        dialog = QgsProjectionSelectionDialog()
        dialog.setWindowIcon(QIcon(":/img/resources/logo.png"))
        dialog.setCrs(mapSetting.destinationCrs())
        dialog.exec()
        if dialog.hasValidSelection():
            self.targetCrsLE.setText(dialog.crs().authid())
        dialog.deleteLater()

    
    def runPBClicked(self):
        if self.resLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        if len(self.mergeList) < 2:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('至少需要两个图层'), self).exec_()
            return
        
        self.shpList = self.mergeList
        self.resPath = self.resLE.text()
        self.crs = self.targetCrsLE.text() 

        self.close()