import sys
import os
import os.path as osp

from ui.tif_process_dialog.rasterMergeDialog import Ui_rasterMergeDialog

from PyQt5.QtCore import Qt, QPoint,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView,QFileDialog
from PyQt5.QtGui import QFont,QCursor

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox,MenuAnimationType,info_bar)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList
from yoyiUtils.yoyiTranslate import yoyiTrans
import appConfig
PROJECT = QgsProject.instance()

class RasterMergeDialogClass(Ui_rasterMergeDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.tifList = None
        self.resampleIndex = None
        self.resPath = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.selectLayerMenu = RoundMenu(parent=self)
        self.sourceDict = {}
        self.mergeList = []
        # 选择图层 
        for layer in PROJECT.mapLayers().values():
            layer : QgsMapLayer
            layerSourcePath: str = layer.source()
            if layerSourcePath.split(".")[-1] in appConfig.SUPPORT_TIF_POST_LIST:
                action = Action(text=layer.name(),parent=self)
                self.selectLayerMenu.addAction(action)
                self.sourceDict[layer.name()] = layerSourcePath
        self.selectLayerSPB.setFlyout(self.selectLayerMenu)

        # 列表
        self.slm = QStringListModel()
        self.slm.setStringList(self.mergeList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ListView.customContextMenuRequested.connect(self.on_custom_menu_requested)

        # other
        # dataTypeList = ["Int8","Int16","UInt16","UInt32","Int32","Float32","Float64"]
        # self.dataTypeCb.addItems(dataTypeList)
        # self.dataTypeCb.setCurrentIndex(0)
        self.selectSaveFilePB.setIcon(FIF.MORE)

    def connectFunc(self):
        self.selectLayerMenu.triggered.connect(self.selectLayerMenuTriggered)
        self.selectFilePB.clicked.connect(self.selectFilePBClicked)
        self.selectDirPB.clicked.connect(self.selectDirPBClicked)
        self.clearListViewPb.clicked.connect(self.clearListViewPbClicked)
        self.selectSaveFilePB.clicked.connect(lambda: qtTriggeredCommonDialog().selectSaveFileTriggered(self.saveLE,'tif',parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
        self.cancelPB.clicked.connect(self.close)

    def on_custom_menu_requested(self,pos):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(FIF.DELETE, self.yoyiTrs._translate('删除所选路径'))
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
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_() 

    def addSourceInListView(self,tifSource):
        if tifSource not in self.mergeList:
            self.mergeList.append(tifSource)
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
        source = self.sourceDict[action.text()]
        self.addSourceInListView(source)
    
    def selectFilePBClicked(self):
        file, ext = QFileDialog.getOpenFileName(self, self.yoyiTrs._translate('选择栅格影像'), "", "GeoTIFF(*.tif;*tiff;*TIF;*TIFF)")
        if file:
            self.addSourceInListView(file)
    
    def selectDirPBClicked(self):
        fileDir = QFileDialog.getExistingDirectory(self, self.yoyiTrs._translate('选择文件夹'), "")
        if fileDir:
            tifList = checkTifList(fileDir)
            if len(tifList) > 0:
                self.addSourceListInListView(tifList)
            else:
                MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('没有有效影像'), self).exec_()
    
    def clearListViewPbClicked(self):
        w = MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('确认要清空列表?'), self)
        w.yesButton.setText(self.yoyiTrs._translate('确认'))
        w.cancelButton.setText(self.yoyiTrs._translate('取消'))
        if w.exec():
            self.mergeList = []
            self.slm.setStringList(self.mergeList)
    
    def runPBClicked(self):
        
        if len(self.mergeList) == 0:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('列表为空'), self).exec_()
            return
        if self.saveLE.text() == "":
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('地址非法'), self).exec_()
            return
        
        self.tifList = self.mergeList
        if self.nearestCHB.isChecked():
            self.resampleIndex = 0
        elif self.linearCHB.isChecked():
            self.resampleIndex = 1
        else:
            self.resampleIndex = 2
        self.resPath = self.saveLE.text()

        self.close()