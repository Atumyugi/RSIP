
import os
import os.path as osp

from ui.draw_dialog.spectralCurveDialog import Ui_spectralCurveDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为SimHei
plt.rcParams['axes.unicode_minus'] = False  # 设置正确显示负号

from PyQt5.QtCore import Qt,QEasingCurve,QStringListModel,pyqtSignal
from PyQt5.QtWidgets import QDesktopWidget,QDialog,QMessageBox,QVBoxLayout,QAbstractItemView,QFileDialog
from PyQt5.QtGui import QPen,QFont,QColor,QPainter

from qgis.core import QgsRasterLayer,QgsProject,QgsVectorLayer,QgsField,QgsRasterDataProvider,QgsFeature,QgsPoint,QgsPointXY,QgsGeometry
from qgis.gui import QgsLayerTreeView,QgsMapToolIdentifyFeature,QgsMapCanvas

from yoyiUtils.custom_maptool import IdentifyRasterMapTool
PROJECT = QgsProject.instance()

class SpectralCurveWindowClass(Ui_spectralCurveDialog,QDialog):
    dialogClosed = pyqtSignal(bool)
    def __init__(self,mapCanvas,rasterLayer,parent=None): 
        super(SpectralCurveWindowClass, self).__init__(parent)
        self.setupUi(self)
        self.mainWindow = parent
        self.mapCanvas : QgsMapCanvas = mapCanvas
        self.rasterLayer : QgsRasterLayer = rasterLayer
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def closeEvent(self, e):
        self.dialogClosed.emit(True)
        e.accept()
        

    def initMember(self):
        self.pointList = []
        self.valueList = []
        
    def initUI(self):
        self.addCurveChart(0,0)
        self.slm = QStringListModel()
        self.slm.setStringList(self.pointList)
        self.ListView.setModel(self.slm)
        self.ListView.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.identifyTool = IdentifyRasterMapTool(self.mapCanvas,self.rasterLayer,self)
        self.identifyTool.setCursor(Qt.WhatsThisCursor)
        #self.identifyTool.deactivated.connect(self)
    
    def addCurveChart(self,row,column):
        self.figure, self.ax = plt.subplots()

        # 隐藏X轴
        #self.ax.set_xticks([])
        #self.ax.spines['bottom'].set_visible(False)
        self.pltCanvas = FigureCanvasQTAgg(self.figure)

        # 图例和标题
        self.ax.set_title("光谱曲线")

        #self.ax.legend(loc='upper center')

        self.chartLayout.addWidget(self.pltCanvas,row,column)

    
    def connectFunc(self):
        self.startCollectPb.clicked.connect(self.startCollectPbClicked)
        self.clearPointsPb.clicked.connect(self.clearPointsPbClicked)
    
    
    def startCollectPbClicked(self):
        if self.mapCanvas.mapTool():
            self.mapCanvas.mapTool().deactivate()
        self.mapCanvas.setMapTool(self.identifyTool)
    
    def showFeatureByTif(self, bandInfo: dict,x,y):
        if not self.collectionModePb.isChecked():
            self.clearPointsPbClicked()
            #self.ax.set_title("光谱曲线")
        print(bandInfo)
        bands = []
        bands_label = []
        pixels = []
        for band,value in bandInfo.items():
            bands.append(band)
            bands_label.append(f"B{band}")
            pixels.append(value)
        
        self.ax.plot(bands,pixels,marker='o')

        for band,pixel in zip(bands,pixels):
            self.ax.text(band,pixel,pixel)

        self.ax.set_xticks(bands)
        self.ax.set_xticklabels(bands_label)

        self.pltCanvas.draw()

        self.valueList.append(bandInfo)
        self.pointList.append(f"{len(self.valueList)}_{x:.4f}_{y:.4f}")
        self.slm.setStringList(self.pointList)

    
    def clearPointsPbClicked(self):
        self.ax.clear()
        self.pltCanvas.draw()
        self.pointList = []
        self.valueList = []
        self.slm.setStringList(self.pointList)
        


        