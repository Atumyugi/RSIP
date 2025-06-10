
import os.path as osp

from ui.infer_dialog.splitDatasetDialog import Ui_splitDatasetDialog

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from qgis.core import QgsProject

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList,checkAllFileList,checkPostFileList
from yoyiUtils.yoyiTranslate import yoyiTrans
from yoyiUtils.yoyiValid import isValidDirName

PROJECT = QgsProject.instance()

class SplitDatasetDialogClass(Ui_splitDatasetDialog,QDialog):
    def __init__(self,yoyiTrs:yoyiTrans,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.yoyiTrs = yoyiTrs
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.imgDirPath = None 
        self.labelDirPath = None
        self.imgDirPost = None
        self.labelDirPost = None

        self.validRatio = None
        self.testRatio = None
        self.shuffle = None

        self.trainSetDirName = None
        self.validSetDirName = None
        self.testSetDirName = None
        self.imgDirName = None
        self.labelDirName = None

        self.resDirPath = None

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)

        # icon
        self.selectTifDirPb.setIcon(FIF.MORE)
        self.selectLabelDirPb.setIcon(FIF.MORE)
        self.selectSaveDirPB.setIcon(FIF.MORE)

        # le read only
        self.selectTifDirLe.setReadOnly(True)
        self.imgPostLineEdit.setReadOnly(True)
        self.selectLabelDirLe.setReadOnly(True)
        self.labelPostLineEdit.setReadOnly(True)
    
    def connectFunc(self):
        self.selectTifDirPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectTifDirLe,parent=self))
        self.selectTifDirLe.textChanged.connect(self.selectTifDirLeTextChanged)
        self.selectLabelDirPb.clicked.connect(lambda : qtTriggeredCommonDialog().addFileDirTriggered(self.selectLabelDirLe,parent=self))
        self.selectLabelDirLe.textChanged.connect(self.selectLabelDirLeTextChanged)

        self.selectSaveDirPB.clicked.connect(lambda: qtTriggeredCommonDialog().addFileDirTriggered(self.resLE,parent=self))
        self.runPB.clicked.connect(self.runPBClicked)
    
    def selectTifDirLeTextChanged(self):
        if osp.exists(self.selectTifDirLe.text()) and osp.isdir(self.selectTifDirLe.text()):
            imgList = checkAllFileList(self.selectTifDirLe.text(),postType="img")
            if len(imgList) > 0:
                imgFirst = imgList[0]
                imgPost = osp.basename(imgFirst).split(".")[-1]
                self.imgPostLineEdit.setText(imgPost)
    
    def selectLabelDirLeTextChanged(self):
        if osp.exists(self.selectLabelDirLe.text()) and osp.isdir(self.selectLabelDirLe.text()):
            imgList = checkAllFileList(self.selectLabelDirLe.text(),postType="label")
            if len(imgList) > 0:
                imgFirst = imgList[0]
                imgPost = osp.basename(imgFirst).split(".")[-1]
                self.labelPostLineEdit.setText(imgPost)
    
    def runPBClicked(self):
        # 通过pb的路径
        imgDirPath = self.selectTifDirLe.text()
        if imgDirPath == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.SelectImgFolderLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        labelDirPath = self.selectLabelDirLe.text()
        if labelDirPath == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.SelectLabelFolderLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        resDirPath = self.resLE.text()
        if resDirPath == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.resDirLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        # 判断图片个数是否超过10个
        imgPost = self.imgPostLineEdit.text()
        if imgPost == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.imgPostLabel.text()} {self.yoyiTrs._translate("为空")}', self).exec_()
            return
        
        labelPost = self.labelPostLineEdit.text()
        if labelPost == "":
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.labelPostLabel.text()} {self.yoyiTrs._translate("为空")}', self).exec_()
            return

        imgList = checkPostFileList(imgDirPath,[imgPost],True)
        labelList = checkPostFileList(labelDirPath,[labelPost],True)
        imgLabelIntersectSet = set([i.split(".")[0] for i in imgList]) & set([i.split(".")[0] for i in labelList])
        if len(imgLabelIntersectSet) < 10:
            MessageBox(self.yoyiTrs._translate('警告'), self.yoyiTrs._translate('影像和标签匹配对少于10'), self).exec_()
            return

        # 通过line edit的路径
        trainSetDirName = self.trainSetNameLE.text()
        if not isValidDirName(trainSetDirName):
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.trainSetLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        validSetDirName = self.validSetNameLE.text()
        if not isValidDirName(validSetDirName):
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.validSetLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        testSetDirName = self.testSetNameLE.text()
        if not isValidDirName(testSetDirName):
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.testSetLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return
        
        imgDirName = self.imgDirNameLE.text()
        if not isValidDirName(imgDirName):
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.imgDirNameLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return

        labelDirName = self.labelDirNameLE.text()
        if not isValidDirName(labelDirName):
            MessageBox(self.yoyiTrs._translate('警告'), f'{self.labelDirNameLabel.text()} {self.yoyiTrs._translate("地址非法")}', self).exec_()
            return

        self.imgDirPath = imgDirPath 
        self.labelDirPath = labelDirPath
        self.imgDirPost = imgPost
        self.labelDirPost = labelPost

        self.validRatio = self.valRatioSpinBox.value() / 100
        self.testRatio = self.testRatioSpinBox.value() / 100
        self.shuffle = self.shuffleCb.isChecked()
        
        self.trainSetDirName = trainSetDirName
        self.validSetDirName = validSetDirName
        self.testSetDirName = testSetDirName
        self.imgDirName = imgDirName
        self.labelDirName = labelDirName

        self.resDirPath = resDirPath

        self.close()