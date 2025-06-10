from appConfig import *
from ui.cdAttrSelectDialogNew import Ui_Dialog
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtCore import QStringListModel,Qt
from PyQt5.QtWidgets import QAbstractItemView,QMenu, QAction,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QDockWidget,QLineEdit
from PyQt5.QtGui import QColor
from qgis.core import QgsProject
from qfluentwidgets import MessageBox

PROJECT = QgsProject.instance()

PreIndex = 0
LateIndex = 0

class selectAttrWindowClass(Ui_Dialog,QDialog):
    def __init__(self,fieldValueDict,mainWindow=None):
        super(selectAttrWindowClass, self).__init__(mainWindow)
        self.setupUi(self)
        self.fieldValueDict : dict = fieldValueDict
        self.initUI()
        self.connectFunc()
        self.center()

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        # self.setFixedSize(self.size())
        self.attrCbDict = {}
        self.labelAttrTableLists = {}

        self.keyList = self.fieldValueDict['QDLDM'][0]
        self.valueList = self.fieldValueDict['QDLDM'][1]

        self.preValueList = self.valueList
        self.lateValueList = self.valueList
        self.preSlm = QStringListModel()
        self.preSlm.setStringList(self.preValueList)
        self.lateSlm = QStringListModel()
        self.lateSlm.setStringList(self.lateValueList)

        self.preListView.setModel(self.preSlm)
        self.preListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preListView.setCurrentIndex(self.preSlm.index(PreIndex if PreIndex<len(self.preValueList) else 0,0))

        self.lateListView.setModel(self.lateSlm)
        self.lateListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lateListView.setCurrentIndex(self.lateSlm.index(LateIndex if LateIndex<len(self.lateValueList) else 0,0))

        self.resDict = None

    def connectFunc(self):
        self.okPb.clicked.connect(self.addFeature)
        self.cancelPb.clicked.connect(self.rejectFeature)

    def closeEvent(self, e):
        e.accept()

    def addFeature(self):

        preIndex = self.preListView.currentIndex().row()
        lateIndex = self.lateListView.currentIndex().row()

        if preIndex == lateIndex:
            MessageBox('提示', "不允许左右属性相同", self).exec_()
            return 
                

        resDict = [self.valueList[preIndex] + STRING_Right + self.valueList[lateIndex],self.keyList[preIndex],self.keyList[lateIndex]]

        self.resDict = resDict
        global PreIndex
        PreIndex = preIndex
        global LateIndex
        LateIndex = lateIndex
        self.close()

    def rejectFeature(self):
        self.close()

