from ui.rectangeMapToolDialog import Ui_Dialog
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtWidgets import QMenu, QAction,QDesktopWidget,QDialog
from PyQt5.QtGui import QColor
from qgis.core import QgsProject

PROJECT = QgsProject.instance()

class mapToolRectangleWindowClass(QDialog,Ui_Dialog):
    def __init__(self,mapTool,mainWindow,isHorizontal=True):
        super(mapToolRectangleWindowClass, self).__init__(mainWindow)
        self.setupUi(self)
        self.mapTool = mapTool
        self.mainWindow = mainWindow
        self.isHorizontal = isHorizontal
        self.initUI()
        self.connectFunc()
        self.center()

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) // 1.2, (screen.height() - size.height()) // 10)

    def initUI(self):
        self.setFixedSize(self.size())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        #self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
        self.comboBox.addItem("水平矩形")
        self.comboBox.addItem("旋转矩形")
        if self.isHorizontal:
            self.comboBox.setCurrentIndex(0)
        else:
            self.comboBox.setCurrentIndex(1)
        self.extraMapTool = None

    def setExtraMapTool(self,mapTool):
        self.extraMapTool = mapTool

    def connectFunc(self):
        self.comboBox.currentIndexChanged.connect(self.changeRectangleMapToolType)

    def changeRectangleMapToolType(self):
        if self.comboBox.currentIndex() == 0:
            self.mapTool.drawType = 0
            if self.extraMapTool:
                self.extraMapTool.drawType = 0
        else:
            self.mapTool.drawType = 1
            if self.extraMapTool:
                self.extraMapTool.drawType = 1
        self.mapTool.reset()
        if self.extraMapTool:
            self.extraMapTool.reset()