import os
import re
import yaml
from PyQt5.QtCore import Qt
from ui.draw_dialog.addSegmentTypeDialog import Ui_SegmentType
from ui.draw_dialog.addDetectionTypeDialog import Ui_DetectionType
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtWidgets import QMenu, QAction,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog
from qgis.core import QgsFeature,QgsFillSymbol,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter

from qfluentwidgets import MessageBox

from appConfig import *
from yoyiUtils.yoyiDefault import classifyCMClass,detecCMClass
import random

class selectClsfyDialogClass(Ui_SegmentType,QDialog):
    def __init__(self,parent=None):
        super(selectClsfyDialogClass, self).__init__(parent)
        self.setupUi(self)
        self.center()
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.classifyCmc = classifyCMClass()
        for yoyiCM in self.classifyCmc.cateIList:
            self.selectI.addItem(yoyiCM.name)
        self.selectI.setCurrentIndex(0)
        self.addCateII()
        self.addCateIII()
        self.selectI.setCurrentIndex(0)
        self.resName = None
        self.resCode = None

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def connectFunc(self):
        self.selectI.currentIndexChanged.connect(self.addCateII)
        self.selectII.currentIndexChanged.connect(self.addCateIII)
        self.saAdd.clicked.connect(self.addCategory)
        self.saCancel.clicked.connect(self.close)

    def addCateII(self):
        self.selectII.clear()
        self.selectII.addItem("不选择")
        currentNameI = self.selectI.currentText()
        currentCodeI = self.classifyCmc.getCodeByName(currentNameI)
        for yoyiCM in self.classifyCmc.cateIIList:
            if yoyiCM.parentCode == currentCodeI:
                self.selectII.addItem(yoyiCM.name)
        self.selectII.setCurrentIndex(0)

    def addCateIII(self):
        self.selectIII.clear()
        self.selectIII.addItem("不选择")
        currentNameII = self.selectII.currentText()
        if currentNameII != "不选择":
            currentCodeII = self.classifyCmc.getCodeByName(currentNameII)
            for yoyiCM in self.classifyCmc.cateIIIList:
                if yoyiCM.parentCode == currentCodeII:
                    self.selectIII.addItem(yoyiCM.name)
        self.selectIII.setCurrentIndex(0)

    def addCategory(self):
        pattern = r"[^a-zA-Z0-9\u4e00-\u9fa5]"
        diyName = re.sub(pattern, "", self.diyLineEdit.text())
        if self.diyCheckBox.isChecked() and diyName != "":
            if diyName == STRING_FullClassify:
                MessageBox('警告', "不允许的名称", self).exec_()
                return
            self.resName = diyName
            self.resCode = diyName
            self.close()
        elif self.selectIII.currentText() != "不选择":
            currentNameIII = self.selectIII.currentText()
            currentCodeIII = self.classifyCmc.getCodeByName(currentNameIII)
            self.resCode = currentCodeIII
            self.resName = currentNameIII
            self.close()
        elif self.selectII.currentText() != "不选择":
            currentNameII = self.selectII.currentText()
            currentCodeII = self.classifyCmc.getCodeByName(currentNameII)
            self.resCode = currentCodeII
            self.resName = currentNameII
            self.close()
        else:
            currentNameI = self.selectI.currentText()
            currentCodeI = self.classifyCmc.getCodeByName(currentNameI)
            self.resCode = currentCodeI
            self.resName = currentNameI
            self.close()

class selectDetectionDialogClass(Ui_DetectionType,QDialog):
    def __init__(self,parent=None):
        super(selectDetectionDialogClass, self).__init__(parent)
        self.setupUi(self)
        self.center()
        self.initUI()
        self.connectFunc()

    def initUI(self):
        self.classifyCmc = detecCMClass()
        for yoyiCM in self.classifyCmc.cateIList:
            self.selectI.addItem(yoyiCM.name)
        self.addCateII()
        self.selectI.setCurrentIndex(0)
        self.resName = None
        self.resCode = None

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def connectFunc(self):
        self.selectI.currentIndexChanged.connect(self.addCateII)
        self.saAdd.clicked.connect(self.addCategory)
        self.saCancel.clicked.connect(self.close)

    def addCateII(self):
        self.selectII.clear()
        self.selectII.addItem("不选择")
        currentNameI = self.selectI.currentText()
        currentCodeI = self.classifyCmc.getCodeByName(currentNameI)
        for yoyiCM in self.classifyCmc.cateIIList:
            if yoyiCM.parentCode == currentCodeI:
                self.selectII.addItem(yoyiCM.name)
        self.selectII.setCurrentIndex(0)

    def addCategory(self):
        pattern = r"[^a-zA-Z0-9\u4e00-\u9fa5]"
        diyName = re.sub(pattern, "", self.diyLineEdit.text())
        if self.diyCheckBox.isChecked() and diyName != "":
            if diyName == STRING_FullClassify:
                MessageBox('警告', "不允许的名称", self).exec_()
                return
            self.resName = diyName
            self.resCode = diyName
            self.close()
        elif self.selectII.currentText() != "不选择":
            currentNameII = self.selectII.currentText()
            currentCodeII = self.classifyCmc.getCodeByName(currentNameII)
            self.resCode = currentCodeII
            self.resName = currentNameII
            self.close()
        else:
            currentNameI = self.selectI.currentText()
            currentCodeI = self.classifyCmc.getCodeByName(currentNameI)
            self.resCode = currentCodeI
            self.resName = currentNameI
            self.close()