from ui.mapToolInputAttr import Ui_DockWidget
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtWidgets import QMenu, QAction,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QDockWidget,QLineEdit
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from qgis.core import QgsLayerTreeNode, QgsLayerTree, QgsMapLayerType,\
    QgsVectorLayer, QgsProject,QgsMarkerSymbol,QgsFillSymbol,QgsLineSymbol,\
    QgsFeatureRenderer,QgsSingleSymbolRenderer,QgsApplication,QgsSimpleLineSymbolLayer,\
    QgsRasterLayer,QgsTaskManager, QgsMessageLog,QgsProcessingAlgRunnerTask, QgsApplication,\
    QgsProcessingContext, QgsProcessingFeedback,QgsProject,QgsTask,Qgis,QgsColorRampShader,QgsPalettedRasterRenderer,\
    QgsRasterShader,QgsSingleBandPseudoColorRenderer,QgsFeature,QgsGeometry,QgsPointXY
PROJECT = QgsProject.instance()

class inputAttrWindowClass(QDockWidget,Ui_DockWidget):
    def __init__(self,mapTool,feat,mainWindow):
        super(inputAttrWindowClass, self).__init__(mainWindow)
        self.setupUi(self)
        self.mapTool = mapTool
        self.feat : QgsFeature = feat
        self.mainWindow = mainWindow
        self.initUI()
        self.connectFunc()
        self.center()

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 2)

    def closeEvent(self, e):
        self.mapTool.reset()
        e.accept()

    def addLayoutBotton(self,fieldName):
        splitter = QtWidgets.QSplitter(self.verticalLayoutWidget_4)
        splitter.setOrientation(QtCore.Qt.Horizontal)
        splitter.setObjectName("splitter")
        label = QtWidgets.QLabel(splitter)
        label.setObjectName(fieldName+"_label")
        label.setText(fieldName)
        label.setMinimumWidth(100)
        lineEdit = QtWidgets.QLineEdit(splitter)
        lineEdit.setObjectName(fieldName+"_line")
        lineEdit.setText("None")
        self.attrsLayout.addWidget(splitter)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.attrsLayout.addItem(spacerItem)
        self.attrLineDir[fieldName] = lineEdit

    def addFeature(self):
        for name in self.feat.fields().names():
            tempLine : QLineEdit = self.attrLineDir[name]
            if tempLine.text() != "None":
                self.feat.setAttribute(name,tempLine.text())
        if self.mapTool.wkbType == "rectangle":
            self.feat.setGeometry(self.mapTool.r)
        elif self.mapTool.wkbType == "polygon":
            self.feat.setGeometry(self.mapTool.p)
        elif self.mapTool.wkbType == "circle":
            pointsXY = [[]]
            for point in self.mapTool.points[0:-1]:
                pointsXY[0].append(QgsPointXY(point))
            self.feat.setGeometry(QgsGeometry.fromPolygonXY(pointsXY))
        self.mapTool.editLayer.addFeature(self.feat)
        # self.editLayer.updateExtents()
        self.mapTool.canvas.refresh()
        self.mapTool.reset()
        # 动态更新撤销重做
        self.mainWindow.updateShpUndoRedoButton()
        self.close()

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.setFixedSize(self.size())
        self.setWindowTitle("属性编辑")
        self.attrLineDir = {}
        for name in self.feat.fields().names():
            self.addLayoutBotton(name)

    def connectFunc(self):
        self.add.clicked.connect(self.addFeature)
        self.cancel.clicked.connect(self.close)