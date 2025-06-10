
import traceback
from qgis.core import QgsMapLayer,QgsVectorLayer,QgsRasterLayer,QgsProject,QgsStyle,QgsProjectStyleSettings,QgsSingleSymbolRenderer,QgsCategorizedSymbolRenderer
from qgis.gui import QgsRendererRasterPropertiesWidget,QgsSymbolLayerWidget,QgsSingleSymbolRendererWidget,QgsCategorizedSymbolRendererWidget,QgsNewVectorLayerDialog
from PyQt5.QtCore import QModelIndex,Qt,pyqtSignal
from PyQt5.QtGui import QFont
from ui.layerPropWindow import Ui_LayerProp
from PyQt5.QtWidgets import QWidget,QDialog,QListWidgetItem,QTabBar
from yoyiUtils.qgisLayerUtils import getRasterLayerAttrs,getVectorLayerAttrs
from yoyiUtils.yoyiTranslate import yoyiTrans
from appConfig import PROJECT_STYLE_XML,yoyiSetting

PROJECT = QgsProject.instance()

class LayerPropWindowWidgeter(Ui_LayerProp,QDialog):
    shpRenderChanged = pyqtSignal(list)
    def __init__(self,layer,mapCanvas,yoyiTrs:yoyiTrans,extraMapCanvas=None,parent=None):
        """
        # tab 信息含义：
        0 栅格信息 1 矢量信息 2 栅格图层渲染 3 矢量图层渲染
        :param layer:
        :param parent:
        """
        super(LayerPropWindowWidgeter,self).__init__(parent)
        self.layer = layer
        self.mapCanvas = mapCanvas
        self.yoyiTrs = yoyiTrs
        self.extraMapCanvas = extraMapCanvas
        self.setupUi(self)

        self.yoyiStyle = QgsStyle(self)
        self.yoyiStyle.importXml(PROJECT_STYLE_XML)

        self.initUI()
        self.connectFunc()
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.isDark = yoyiSetting().configSettingReader.value('windowStyle',type=int)
        self.DarkCOLOR = yoyiSetting().configSettingReader.value('darkBgColor', type=tuple)
        layerbar = self.tabWidget.findChild(QTabBar)
        layerbar.hide()
        renderBar = self.comboTabWidget.findChild(QTabBar)
        renderBar.hide()
        self.listWidget.setCurrentRow(0)
        self.initInfomationTab()
        self.decideRasterNVector(0)
        
        self.vecterRenderCB.addItems([self.yoyiTrs._translate("单一渲染"),self.yoyiTrs._translate("分类渲染")])
        self.vecterRenderCB.setCurrentIndex(0)
        self.comboTabWidget.setCurrentIndex(0)

        self.rasterSourceLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.vectorSourceLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        #a = QgsNewVectorLayerDialog(self)
        #a.runAndCreateLayer()
        

    def connectFunc(self):
        self.listWidget.itemClicked.connect(self.listWidgetItemClicked)
        self.okPb.clicked.connect(lambda : self.renderApplyPbClicked(needClose=True))
        self.cancelPb.clicked.connect( self.close )
        self.applyPb.clicked.connect(lambda : self.renderApplyPbClicked(needClose=False))
        self.vecterRenderCB.currentIndexChanged.connect(self.vecterRenderCBChanged)

    # 切换矢量渲染方式
    def vecterRenderCBChanged(self):
        self.comboTabWidget.setCurrentIndex(self.vecterRenderCB.currentIndex())

    def initInfomationTab(self):
        if type(self.layer) == QgsRasterLayer:
            rasterLayerDict = getRasterLayerAttrs(self.layer)
            self.rasterNameLabel.setText(rasterLayerDict['name'])
            self.rasterSourceLabel.setText(rasterLayerDict['source'])
            self.rasterMemoryLabel.setText(rasterLayerDict['memory'])
            self.rasterExtentLabel.setText(rasterLayerDict['extent'])
            self.rasterWidthLabel.setText(rasterLayerDict['width'])
            self.rasterHeightLabel.setText(rasterLayerDict['height'])
            self.rasterDataTypeLabel.setText(rasterLayerDict['dataType'])
            self.rasterBandNumLabel.setText(rasterLayerDict['bands'])
            self.rasterCrsLabel.setText(rasterLayerDict['crs'])
            self.rasterRenderWidget = QgsRendererRasterPropertiesWidget(self.layer, self.mapCanvas,parent=self)
            if self.isDark:
                self.rasterRenderWidget.setStyleSheet(f" background:rgb({self.DarkCOLOR[0]}, {self.DarkCOLOR[1]}, {self.DarkCOLOR[2]}) ; color:#ffffff ")
            self.rasterLayerRenderScrollArea.setWidget(self.rasterRenderWidget)

        elif type(self.layer) == QgsVectorLayer:
            self.layer : QgsVectorLayer
            vectorLayerDict = getVectorLayerAttrs(self.layer)
            self.vectorNameLabel.setText(vectorLayerDict['name'])
            self.vectorSourceLabel.setText(vectorLayerDict['source'])
            self.vectorMemoryLabel.setText(vectorLayerDict['memory'])
            self.vectorExtentLabel.setText(vectorLayerDict['extent'])
            self.vectorGeoTypeLabel.setText(vectorLayerDict['geoType'])
            self.vectorFeatureNumLabel.setText(vectorLayerDict['featureNum'])
            self.vectorEncodingLabel.setText(vectorLayerDict['encoding'])
            self.vectorCrsLabel.setText(vectorLayerDict['crs'])
            self.vectorDpLabel.setText(vectorLayerDict['dpSource'])

            # single Render
            if type(self.layer.renderer()) == QgsSingleSymbolRenderer:
                self.vectorSingleRenderWidget = QgsSingleSymbolRendererWidget(self.layer,self.yoyiStyle,self.layer.renderer())
            else:
                self.vectorSingleRenderWidget = QgsSingleSymbolRendererWidget(self.layer,self.yoyiStyle,None)
            if self.isDark:
                self.vectorSingleRenderWidget.setStyleSheet(f" background:rgb({self.DarkCOLOR[0]}, {self.DarkCOLOR[1]}, {self.DarkCOLOR[2]}) ; color:#ffffff ")
            self.shpSingleRenderScrollArea.setWidget(self.vectorSingleRenderWidget)

            # category Render
            if type(self.layer.renderer()) == QgsCategorizedSymbolRenderer:
                self.vectorCateGoryRenderWidget = QgsCategorizedSymbolRendererWidget(self.layer,self.yoyiStyle,self.layer.renderer())
            else:
                self.vectorCateGoryRenderWidget = QgsCategorizedSymbolRendererWidget(self.layer,self.yoyiStyle,None)
            
            self.shpCategoryRenderScrollArea.setWidget(self.vectorCateGoryRenderWidget)
            if self.isDark:
                self.vectorCateGoryRenderWidget.setStyleSheet(f" background:rgb({self.DarkCOLOR[0]}, {self.DarkCOLOR[1]}, {self.DarkCOLOR[2]}) ; color:#ffffff ")

    def decideRasterNVector(self,index):
        if index == 0:
            if type(self.layer) == QgsRasterLayer:
                self.tabWidget.setCurrentIndex(0)
            elif type(self.layer) == QgsVectorLayer:
                self.tabWidget.setCurrentIndex(1)
        elif index == 1:
            if type(self.layer) == QgsRasterLayer:
                self.tabWidget.setCurrentIndex(2)
            elif type(self.layer) == QgsVectorLayer:
                self.tabWidget.setCurrentIndex(3)


    def listWidgetItemClicked(self,item:QListWidgetItem):
        tempIndex = self.listWidget.indexFromItem(item).row()
        self.decideRasterNVector(tempIndex)


    def renderApplyPbClicked(self,needClose=False):
        if self.tabWidget.currentIndex() <= 1:
            return
        elif type(self.layer) == QgsRasterLayer:
            self.rasterRenderWidget : QgsRendererRasterPropertiesWidget
            self.rasterRenderWidget.apply()
        elif type(self.layer) == QgsVectorLayer:
            #self.vectorRenderWidget : QgsSingleSymbolRendererWidget
            self.layer : QgsVectorLayer
            if self.comboTabWidget.currentIndex() == 0:
                renderer: QgsSingleSymbolRenderer = self.vectorSingleRenderWidget.renderer()
                self.layer.setRenderer(renderer)
            else:
                renderer = self.vectorCateGoryRenderWidget.renderer()
                self.layer.setRenderer(renderer)

            if type(renderer) == QgsSingleSymbolRenderer:
                color = renderer.symbol().color()
                print(color)
            else:
                color = None
            self.shpRenderChanged.emit([self.layer.name(),color])
        
        self.layer.triggerRepaint()
        self.mapCanvas.refresh()
        if self.extraMapCanvas:
            self.extraMapCanvas.refresh()
        if needClose:
            self.close()


