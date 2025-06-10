from ui.draw_dialog.tifRenderDialog import Ui_Dialog
from PyQt5 import QtCore,QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDesktopWidget,QDialog
from qgis.core import QgsRasterLayer,QgsProject,QgsRasterRenderer,QgsBrightnessContrastFilter,QgsRasterDataProvider
PROJECT = QgsProject.instance()

class multiBandTifAttrWindowClass(QDialog,Ui_Dialog):
    def __init__(self,layer,window):
        super(multiBandTifAttrWindowClass, self).__init__(window)
        self.setupUi(self)

        self.layer : QgsRasterLayer = layer

        self.center()
        self.initUI()
        self.connectFunc()

    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()
        # 获取窗口的尺寸信息
        size = self.geometry()
        # 将窗口移动到指定位置
        self.move((screen.width() - size.width()) / 2, (screen.height() - size.height()) / 4)

    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)  # 关闭窗口销毁对象
        self.setWindowTitle('影像渲染')
        self.bandCount = self.layer.bandCount()  # 总共有多少个波段
        self.layerRender: QgsRasterRenderer = self.layer.renderer()
        self.layerBrightnessContrastFilter: QgsBrightnessContrastFilter = self.layer.brightnessFilter()
        self.layerDataProvider: QgsRasterDataProvider = self.layer.dataProvider()
        self.redRender = self.layerRender.redBand()
        self.greenRender = self.layerRender.greenBand()
        self.blueRender = self.layerRender.blueBand()
        for i in range(self.bandCount):
            self.redBand.addItem(str(i+1))
        for i in range(self.bandCount):
            self.greenBand.addItem(str(i+1))
        for i in range(self.bandCount):
            self.blueBand.addItem(str(i+1))
        self.setInitUI()
        self.updateBrightnessLabelValue()
        self.updateGammaLabelValue()
        self.updateContrastLabelValue()
        self.updateOpacityLabelValue()

    def connectFunc(self):
        self.brightnessSlider.valueChanged.connect(self.updateBrightnessLabelValue)
        self.gammaSlider.valueChanged.connect(self.updateGammaLabelValue)
        self.contrastSlider.valueChanged.connect(self.updateContrastLabelValue)
        self.opacitySlider.valueChanged.connect(self.updateOpacityLabelValue)
        self.saRestore.clicked.connect(self.setDefalutUI)
        self.saSave.clicked.connect(self.changeRender)
        self.saCancel.clicked.connect(lambda: self.close())

    # 初始化渲染设置
    def setInitUI(self):
        self.redBand.setCurrentIndex(self.redRender - 1)
        self.greenBand.setCurrentIndex(self.greenRender - 1)
        self.blueBand.setCurrentIndex(self.blueRender - 1)
        self.brightnessSlider.setValue(self.layerBrightnessContrastFilter.brightness())
        self.gammaSlider.setValue(self.layerBrightnessContrastFilter.gamma() * 10)
        self.contrastSlider.setValue(self.layerBrightnessContrastFilter.contrast())
        self.opacitySlider.setValue(self.layerRender.opacity() * 100)
        self.noDataSpinBox.setValue(self.layerDataProvider.NoDataCapabilities)

    # 设为默认值
    def setDefalutUI(self):
        """
        rgb 不变
        亮度 brightness 0
        gamma  10 -> 也就是1.0  这里的gammaSlider / 10 才是真正的值
        对比度 contrast 0
        透明度 opacity 100
        Nodata 0
        """
        self.redBand.setCurrentIndex(self.redRender - 1)
        self.greenBand.setCurrentIndex(self.greenRender - 1)
        self.blueBand.setCurrentIndex(self.blueRender - 1)
        self.brightnessSlider.setValue(0)
        self.gammaSlider.setValue(10)
        self.contrastSlider.setValue(0)
        self.opacitySlider.setValue(100)
        self.noDataSpinBox.setValue(0)

    # 实时显示亮度值
    def updateBrightnessLabelValue(self):
        self.brightLabel.setText(str(self.brightnessSlider.value()))

    # 实时显示gamma值
    def updateGammaLabelValue(self):
        self.gammaLabel.setText(str(self.gammaSlider.value() / 10.0))

    # 实时显示对比度
    def updateContrastLabelValue(self):
        self.contrastLabel.setText(str(self.contrastSlider.value()))

    # 实时显示透明度
    def updateOpacityLabelValue(self):
        self.opacityLabel.setText(str(self.opacitySlider.value()) + "%")

    # 渲染
    def changeRender(self):
        # 波段渲染
        redTemp = self.redBand.currentIndex() + 1
        greenTemp = self.greenBand.currentIndex() + 1
        blueTemp = self.blueBand.currentIndex() + 1
        self.layerRender.setRedBand(redTemp)
        self.layerRender.setGreenBand(greenTemp)
        self.layerRender.setBlueBand(blueTemp)
        # 亮度渲染
        self.layerBrightnessContrastFilter.setBrightness(self.brightnessSlider.value())
        # gamma 渲染
        self.layerBrightnessContrastFilter.setGamma(self.gammaSlider.value() / 10.0)
        # 对比度渲染
        self.layerBrightnessContrastFilter.setContrast(self.contrastSlider.value())
        # 透明度渲染
        self.layerRender.setOpacity(self.opacitySlider.value() / 100.0)
        # 无数据值渲染
        for i in range(self.bandCount):
            self.layerDataProvider.setNoDataValue(i + 1, int(self.noDataSpinBox.value()))
        self.layer.triggerRepaint()