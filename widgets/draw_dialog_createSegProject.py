import datetime
import os
import os.path as osp
import re
import traceback

from ui.draw_dialog.segDrawCreateProject import Ui_segCreateProjectDialog

from PyQt5.QtCore import Qt, QPoint,QThread,pyqtSignal,QVariant,QStringListModel
from PyQt5.QtWidgets import QAbstractItemView,QApplication, QDialog, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QCursor,QIcon
from qgis.core import QgsRasterLayer,QgsVectorLayer,QgsProject,QgsCoordinateTransform,QgsGeometry,QgsFeature

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox,MenuAnimationType)
from qfluentwidgets import FluentIcon as FIF

from widgets.draw_dialog_selectCateWindow import selectClsfyDialogClass,selectDetectionDialogClass
from widgets.draw_dialog_pixelClassifyMapWindow import PixelClassifyMapWindowClass
from widgets.projectListDialog import LocalProjectListDialogClass
from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,createDir,saveSampleWorkYaml,readYamlToDict,checkAllFileList,saveYamlForList,saveYamlForDict,readYamlToList
from yoyiUtils.qgisFunction import saveShpFunc,createFishNet
from yoyiUtils.yoyiDialogThread import createLocalProjectRunClass,createWmsProjectRunClass,createLocalDirProjectRunClass
from yoyiUtils.yoyiDefault import classifyCMClass,detecCMClass
from appConfig import *

PROJECT = QgsProject.instance()

class SegDrawCreateProjectDialogClass(Ui_segCreateProjectDialog,QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.tabWidget.tabBar().hide()
        self.tabWidget.setCurrentIndex(0)
        self.tifModePb.setChecked(True)

        # icon -- local
        self.selectTifPb.setIcon(FIF.MORE)
        self.selectShpPb.setIcon(FIF.MORE)
        self.selectMosaicPb.setIcon(FIF.MORE)
        self.selectTifDirPb.setIcon(FIF.MORE)
        self.selectLabelDirPb.setIcon(FIF.MORE)

        # icon -- wms
        self.selectExtentPb.setIcon(FIF.MORE)

        # le read only
        self.selectTifLe.setReadOnly(True)
        self.selectShpLe.setReadOnly(True)
        self.selectMosaicLe.setReadOnly(True)

        self.setShpLayoutVisible(False)
        self.setMosaicLayoutVisible(False)
        self.setLabelDirLayoutVisible(False)

        # segsize
        self.segSizeSb.setValue(512)

        # process
        self.IndeterminateProgressBar.stop()
        self.ProgressBar.hide()


    def initMember(self):

        self.projectDir = None

        self.cateType = 0  # 0 语义分割 1 目标检测

        self.typeNameList = []  # type list
        self.classifyCM = classifyCMClass()
        self.detecCM = detecCMClass()
        self.tempSize = [0,0]

        self.slm = QStringListModel()
        self.slm.setStringList(self.typeNameList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ListView.customContextMenuRequested.connect(self.on_custom_menu_requested)



    def connectFunc(self):
        self.modePbGroup.buttonClicked.connect(self.modePbGroupClicked)
        self.importShpCb.clicked.connect(lambda : self.setShpLayoutVisible(self.importShpCb.isChecked()))
        self.importMosaicCb.clicked.connect(lambda : self.setMosaicLayoutVisible(self.importMosaicCb.isChecked()))
        self.importLabelDirCb.clicked.connect(lambda: self.setLabelDirLayoutVisible(self.importLabelDirCb.isChecked()))
        
        # wms
        self.selectExtentPb.clicked.connect(
            lambda: qtTriggeredCommonDialog().addFileTriggered(self.selectExtentShp, filterType='shp', parent=self))

        # 本地影像勾画模式
        self.selectTifPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileTriggered(self.selectTifLe,parent=self))
        self.selectTifLe.textChanged.connect(self.selectTifLeTextChanged)

        # 样本勾画模式
        self.selectTifDirPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectTifDirLe,parent=self))
        self.selectTifDirLe.textChanged.connect(self.selectTifDirLeTextChanged)
        self.selectLabelDirPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectLabelDirLe,parent=self))
        self.selectLabelDirLe.textChanged.connect(self.selectLabelDirLeTextChanged)

        # 导入矢量、 导入镶嵌线
        self.selectShpPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileTriggered(self.selectShpLe,filterType='shp',parent=self))
        self.selectMosaicPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileTriggered(self.selectMosaicLe,filterType='shp',parent=self))

        # 创建分类类别
        self.segOrDetecGroup.buttonToggled.connect(self.segOrDetecGroupToggled)
        self.selectClassifyType.clicked.connect(self.selectSegmentTypeClicked)
        self.importClassifyType.clicked.connect(self.importSegmentTypeClicked)

        self.runPB.clicked.connect(self.runPbClicked)

    def setShpLayoutVisible(self,isVisible=True):
        if isVisible:
            self.selectShpLe.show()
            self.selectShpPb.show()
        else:
            self.selectShpLe.hide()
            self.selectShpPb.hide()

    def setMosaicLayoutVisible(self,isVisible=True):
        if isVisible:
            self.selectMosaicLe.show()
            self.selectMosaicPb.show()
        else:
            self.selectMosaicLe.hide()
            self.selectMosaicPb.hide()
    
    def setLabelDirLayoutVisible(self,isVisible=True):
        if isVisible:
            self.selectLabelDirLe.show()
            self.selectLabelDirPb.show()
            self.labelPostLabel.show()
            self.labelPostLineEdit.show()
        else:
            self.selectLabelDirLe.hide()
            self.selectLabelDirPb.hide()
            self.labelPostLabel.hide()
            self.labelPostLineEdit.hide()

    def modePbGroupClicked(self):
        if self.tifModePb.isChecked():
            self.tabWidget.setCurrentIndex(0)
            self.importShpCb.setEnabled(True)
            self.selectShpPb.setEnabled(True)
        elif self.wmsModePb.isChecked():
            self.tabWidget.setCurrentIndex(1)
            self.importShpCb.setEnabled(True)
            self.selectShpPb.setEnabled(True)
        else:
            self.tabWidget.setCurrentIndex(2)
            self.importShpCb.setEnabled(False)
            self.selectShpPb.setEnabled(False)

    def selectTifLeTextChanged(self):
        if osp.exists(self.selectTifLe.text()):
            tempLayer = QgsRasterLayer(self.selectTifLe.text())
            rdp = tempLayer.dataProvider()
            if rdp.dataType(1) != 1:
                MessageBox('警告', f"该影像不是uint8数据类型，无法勾画", self).exec_()
                self.selectTifLe.setText("")
                self.tifSize.setText("？？？")
                self.tempSize = [0,0]
                return
            else:
                self.tifSize.setText(f"{tempLayer.height()},{tempLayer.width()}")
                self.tempSize = [tempLayer.height(), tempLayer.width()]
                del tempLayer
                self.projectNameLe.setText(osp.basename(self.selectTifLe.text()).split(".")[0]+"_勾画_日期:"+datetime.datetime.now().strftime('%Y年%m月%d日'))
        else:
            self.tifSize.setText("？？？")
            self.tempSize = [0,0]
    
    def selectTifDirLeTextChanged(self):
        if osp.exists(self.selectTifDirLe.text()) and osp.isdir(self.selectTifDirLe.text()):
            imgList = checkAllFileList(self.selectTifDirLe.text(),postType="img")
            if len(imgList) > 0:
                imgFirst = imgList[0]
                imgPost = osp.basename(imgFirst).split(".")[-1]
                self.imgPostLineEdit.setText(imgPost)
                self.projectNameLe.setText(osp.basename(self.selectTifDirLe.text())+"_文件夹勾画_日期:"+datetime.datetime.now().strftime('%Y年%m月%d日'))
    
    def selectLabelDirLeTextChanged(self):
        if osp.exists(self.selectLabelDirLe.text()) and osp.isdir(self.selectLabelDirLe.text()):
            imgList = checkAllFileList(self.selectLabelDirLe.text(),postType="img")
            if len(imgList) > 0:
                imgFirst = imgList[0]
                imgPost = osp.basename(imgFirst).split(".")[-1]
                self.labelPostLineEdit.setText(imgPost)

    def segOrDetecGroupToggled(self):
        if len(self.typeNameList) > 0:
            w = MessageBox('警告', '切换勾画模式会清空类别表，继续吗？', self)
            w.yesButton.setText('确定')
            w.cancelButton.setText('取消')
            if w.exec():
                self.typeNameList = []
                self.slm.setStringList(self.typeNameList)
            else:
                if self.segmentRadioButton.isChecked():
                    self.detectionRadioButton.setChecked()
                if self.detectionRadioButton.isChecked():
                    self.segmentRadioButton.setChecked()
  


    def selectSegmentTypeClicked(self):
        if self.segmentRadioButton.isChecked():
            dialog = selectClsfyDialogClass(self)
        else:
            dialog = selectDetectionDialogClass(self)
        dialog.exec()
        if dialog.resName:
            if dialog.resName not in self.typeNameList:
                self.typeNameList.append(dialog.resName)
                self.slm.setStringList(self.typeNameList)
                self.ListView.setCurrentIndex(self.slm.index(0,0))
            else:
                MessageBox('警告', f'类别重复！', self).exec_()
        dialog.deleteLater()
    
    def importSegmentTypeClicked(self):
        localProjectDir = yoyiSetting().configSettingReader.value('localProject', type=str)
        segmentProjectDir = osp.join(localProjectDir, "segment")
        projectSelectDialog = LocalProjectListDialogClass(segmentProjectDir, self)
        projectSelectDialog.exec_()
        if projectSelectDialog.selectedProject:
            nameList = readYamlToList(osp.join(segmentProjectDir,projectSelectDialog.selectedProject,"project.codemap"))
            for name in nameList:
                if name not in self.typeNameList:
                    self.typeNameList.append(name)
            self.slm.setStringList(self.typeNameList)
            self.ListView.setCurrentIndex(self.slm.index(0, 0))
        projectSelectDialog.deleteLater()

    
    def deleteType(self):
        curIndex = self.ListView.currentIndex().row()
        if curIndex >=0:
            self.typeNameList.pop(curIndex)
            self.slm.setStringList(self.typeNameList)
        else:
            MessageBox('警告', f'未选中类别', self).exec_()

    def on_custom_menu_requested(self,pos):
        cusMenu = RoundMenu(parent=self)
        cusMenu.setItemHeight(50)
        deleteSelected = Action(FIF.DELETE, '删除所选要素')
        deleteSelected.triggered.connect(self.deleteType)
        cusMenu.addAction(deleteSelected)
        curPos : QPoint = QCursor.pos()
        cusMenu.exec_(QPoint(curPos.x(), curPos.y()),aniType=MenuAnimationType.NONE)


    def runPbClicked(self):
        pattern = r"[^a-zA-Z0-9\u4e00-\u9fa5]"
        projectName = re.sub(pattern,"",self.projectNameLe.text())
        print(projectName)
        if projectName == "" :
            MessageBox('警告', f'项目名非法或为空', self).exec_()
            return
        localProjectDir = yoyiSetting().configSettingReader.value('localProject', type=str)
        segmentProjectDir = osp.join(localProjectDir, "segment")
        absProjectDir = osp.join(segmentProjectDir, projectName)
        if osp.exists(absProjectDir):
            MessageBox('警告', f'项目已存在', self).exec_()
            return

        createDir(localProjectDir)
        createDir(segmentProjectDir)
        
        if len(self.typeNameList) < 2:
            w = MessageBox('警告', '您的类别<=2,是要创建通用勾画方式吗(不填写属性表)？', self)
            w.yesButton.setText('是的')
            w.cancelButton.setText('不是')

            if w.exec():
                if len(self.typeNameList) == 0:
                    self.typeNameList.append("目标")
                # saveYamlForDict(defaultSaveShpYsi, saveColorMap)
            else:
                return
        
        if self.importShpCb.isChecked() and osp.exists(self.selectShpLe.text()):
            extraShpPath = self.selectShpLe.text()
        else:
            extraShpPath = None
        
        # 单一影像勾画
        if self.tifModePb.isChecked():
            if not osp.exists(self.selectTifLe.text()):
                MessageBox('警告', f'勾画影像路径为空或不合法！', self).exec_()
                return

            segSize = self.segSizeSb.value()
            if self.tempSize[0] < (segSize // 2) or self.tempSize[1] < (segSize // 2):
                MessageBox('警告', f'您选择的影像尺寸小于裁剪尺寸的一半，无法创建作业', self).exec_()
                return

            self.drawTif = self.selectTifLe.text()

            workDirConfigTxt = os.path.join(absProjectDir, "project.config")
            createDir(absProjectDir)
            saveYamlForDict(osp.join(absProjectDir, "project.codemap"), self.classifyCM.getColorMapByNameList(self.typeNameList))
            saveSampleWorkYaml(workDirConfigTxt, DRAW_TYPE_SEG if self.cateType == 0 else DRAW_TYPE_OD,tifPath=self.drawTif, curIndex=0, segSize=segSize)


            if self.importMosaicCb.isChecked() and osp.exists(self.selectMosaicLe.text()):
                mosaicPath = self.selectMosaicLe.text()
            else:
                mosaicPath = None

            self.setEnabled(False)
            self.IndeterminateProgressBar.start()
            self.createClsfyProjectThread = createLocalProjectRunClass(self.selectTifLe.text(), absProjectDir,
                                                                       segSize,
                                                                       mosaicPath=mosaicPath,
                                                                       extraShp=extraShpPath,
                                                                       parent=self)
            self.createClsfyProjectThread.signal_over.connect(self.finishRunThread)
            self.createClsfyProjectThread.finished.connect(self.createClsfyProjectThread.deleteLater)
            self.createClsfyProjectThread.start()
        # 在线底图勾画
        elif self.wmsModePb.isChecked():
            xSegNum = self.xSegNum.value()
            ySegNum = self.ySegNum.value()

            extentShp = self.selectExtentShp.text()

            self.drawWms = self.selectXYZTilesLE.text()

            workDirConfigTxt = os.path.join(absProjectDir, "project.config")
            createDir(absProjectDir)
            saveYamlForDict(osp.join(absProjectDir, "project.codemap"), self.classifyCM.getColorMapByNameList(self.typeNameList))
            saveSampleWorkYaml(workDirConfigTxt, DRAW_TYPE_WMS_SEG,tifPath=self.drawWms, segSize=[xSegNum, ySegNum], curIndex=0)

            self.setEnabled(False)
            self.IndeterminateProgressBar.start()
            self.createWmsProjectThread = createWmsProjectRunClass(extentShp, absProjectDir, xSegNum, ySegNum, extraShp=extraShpPath, parent=self)
            self.createWmsProjectThread.signal_over.connect(self.finishRunThread)
            self.createWmsProjectThread.finished.connect(self.createWmsProjectThread.deleteLater)
            self.createWmsProjectThread.start()
        # 数据集勾画
        else:
            if not osp.exists(self.selectTifDirLe.text()):
                MessageBox('警告', f'勾画影像路径为空或不合法！', self).exec_()
                return
            
            imgPost = self.imgPostLineEdit.text()
            labelPost = self.labelPostLineEdit.text()
            imgList = checkAllFileList(self.selectTifDirLe.text(),postType=imgPost)
            if len(imgList) == 0:
                MessageBox('警告', f'文件夹中没有合法图像', self).exec_()
                return
            

            MessageBox('信息', f'请填写像素值与分类标签映射表', self).exec_()
            dialog = PixelClassifyMapWindowClass(self.typeNameList,parent=self)
            dialog.exec()
            print(dialog.completeStatus,dialog.pixelMap,dialog.nodataValue)
            if dialog.completeStatus:
                pixelMap = dialog.pixelMap
                nodataValue = dialog.nodataValue
            else:
                return
            dialog.deleteLater()


            self.drawTif = self.selectTifDirLe.text()
            createDir(absProjectDir)
            saveYamlForDict(osp.join(absProjectDir, "project.codemap"), self.classifyCM.getColorMapByNameList(self.typeNameList))
            saveYamlForDict(osp.join(absProjectDir, "project.pixelmap"), pixelMap)
            workDirConfigTxt = os.path.join(absProjectDir, "project.config")
            saveSampleWorkYaml(workDirConfigTxt, DRAW_TYPE_SEG if self.cateType == 0 else DRAW_TYPE_OD,
                               tifPath=self.drawTif, curIndex=0, segSize=512,extraLabelDir=self.selectLabelDirLe.text()
                               ,extraImgPost=imgPost
                               ,extraLabelPost=labelPost)
            self.setEnabled(False)
            self.ProgressBar.show()
            self.createClsfyProjectThread = createLocalDirProjectRunClass(imgList, absProjectDir,pixelMap=pixelMap,nodataValue=nodataValue,labelDir=self.selectLabelDirLe.text(),labelPost=labelPost,parent=self)
            self.createClsfyProjectThread.signal_process.connect(self.changeProgressBar)
            self.createClsfyProjectThread.signal_over.connect(self.finishRunThread)
            self.createClsfyProjectThread.finished.connect(self.createClsfyProjectThread.deleteLater)
            self.createClsfyProjectThread.start()

    def changeProgressBar(self,status):
        self.ProgressBar.setValue(status)

    def finishRunThread(self,resDir):
        self.setEnabled(True)
        self.IndeterminateProgressBar.stop()

        if os.path.exists(resDir):
            self.projectDir = resDir
            MessageBox('成功',"生成成功", self).exec_()
        else:
            self.projectDir = None
            MessageBox('警告',resDir,self).exec_()

        self.close()






