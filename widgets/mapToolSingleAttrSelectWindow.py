from ui.attrSelectDialog import Ui_Dialog
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QAbstractItemView,QMenu, QAction,QDesktopWidget,QDialog,QColorDialog,QMessageBox,QSizePolicy,QDockWidget,QLineEdit
from PyQt5.QtGui import QColor
from qgis.core import QgsLayerTreeNode, QgsLayerTree, QgsMapLayerType,\
    QgsVectorLayer, QgsProject,QgsMarkerSymbol,QgsFillSymbol,QgsLineSymbol,\
    QgsFeatureRenderer,QgsSingleSymbolRenderer,QgsApplication,QgsSimpleLineSymbolLayer,\
    QgsRasterLayer,QgsTaskManager, QgsMessageLog,QgsProcessingAlgRunnerTask, QgsApplication,\
    QgsProcessingContext, QgsProcessingFeedback,QgsProject,QgsTask,Qgis,QgsColorRampShader,QgsPalettedRasterRenderer,\
    QgsRasterShader,QgsSingleBandPseudoColorRenderer,QgsFeature,QgsGeometry,QgsPointXY
PROJECT = QgsProject.instance()

class selectSingleAttrWindowClass(QDialog,Ui_Dialog):
    def __init__(self,valueList,mainWindow=None):
        super(selectSingleAttrWindowClass, self).__init__(mainWindow)
        self.setupUi(self)
        self.valueList  = valueList
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

        self.Slm = QStringListModel()
        self.Slm.setStringList(self.valueList)

        self.ListView.setModel(self.Slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ListView.setCurrentIndex(self.Slm.index(0,0))

        self.resIndex = -1

    def connectFunc(self):
        self.okPb.clicked.connect(self.addFeature)
        self.cancelPb.clicked.connect(self.rejectFeature)

    def closeEvent(self, e):
        e.accept()

    def addFeature(self):

        Index = self.ListView.currentIndex().row()
        self.resIndex = Index
        self.close()

    def rejectFeature(self):
        self.close()

