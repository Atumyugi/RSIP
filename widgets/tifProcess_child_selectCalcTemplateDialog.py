import sys
import os
import os.path as osp

from appConfig import STRING_EXPRESSION_VALID,STRING_EXPRESSION_INVALID

from ui.tif_process_dialog.selectCalcTemplateDialog import Ui_selectCalcTemplateDialog

from PyQt5.QtCore import Qt, QPoint,QStringListModel
from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout,QAbstractItemView,QFileDialog
from PyQt5.QtGui import QFont,QCursor

from qgis.core import QgsProject,QgsMapLayer,QgsMapLayerType,QgsLayerTreeGroup,QgsRasterLayer,QgsRectangle,QgsMapSettings,QgsCoordinateReferenceSystem
from qgis.gui import QgsMapCanvas,QgsProjectionSelectionDialog
from qgis.analysis import QgsRasterCalcNode,QgsRasterCalculatorEntry

from qfluentwidgets import (CardWidget, setTheme, Theme, IconWidget, BodyLabel,SubtitleLabel, CaptionLabel, PushButton,
                            TransparentToolButton, RoundMenu, Action,MessageBox,ToolTipFilter)
from qfluentwidgets import FluentIcon as FIF

from yoyiUtils.qtTriggeredCommon import qtTriggeredCommonDialog
from yoyiUtils.yoyiFile import checkTifList

NDVITip = """
由于植被在近红外波段处有较强的反射，其反射率值较高，而在红波段处有较强的吸收，
反射率值较低，因此归一化差值植被指数（NDVI）通过计算近红外波段和红波段之间的
差异来定量化植被的生长状况。该指数可反映植被的健康情况及植被的长势，由于计算简
单，指示性好，被广泛应 用于农业、林业、生态环境等领域，同时也是生态物理参数反
演的重要输入参数，是目前应用最为 广泛的植被指数之一。在典型的光谱植被指数中，
NDVI (opens new window)是最适合监测作物生长动态的指数之一，因为它测量植物中
的光合作用的活性生物量。然而，该植被指数对土壤亮度和大气影响非常敏感，在 EVI、
SAVI、ARVI、GCL 或 SIPI 等其他指数中有所缓解。
公式：
NDVI = (NIR - RED) / (NIR + RED) 特点：NDVI 是遥感中最常见的植被指数。它可以
在整个作物生产季节使用，除非植被覆盖太稀少，因此它的光谱反射率太低。
何时使用：NDVI 值在作物最活跃生长阶段的季节中期最准确。
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/ndvi.htm
"""

REClTip = """
ReCI 植被指数对受氮滋养的叶子中的叶绿素含量有反应。ReCI 显示了冠层的光合活性。
公式：
ReCI = (NIR / RED) - 1
特点：由于叶绿素含量直接取决于植物中的氮含量，这是植物“绿色”的原因，因此遥感中
的这种植被指数有助于检测黄色或落叶区域。
何时使用：ReCI 值在植被活跃发育阶段最有用，但不适用于收获季节。
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

NDRETip = """
NDRE指数结合了近红外 (NIR) 光谱波段和特定波段，用于可见红色
和Red-NIR 过渡区（所谓的红边区域）之间的窄范围。为获得最佳数据精度，建议将 NDRE 
与 NDVI 结合使用。
公式：
NDRE = (NIR - RED EDGE) / (NIR + RED EDGE)
特点：给定的植被指数适用于高密度树冠覆盖。
何时使用：NDRE 通常用于监测已达到成熟阶段的作物
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

MSAVITip = """
MSAVI植被指数旨在减轻土壤对作物监测结果的影响。因此，它适用于
NDVI 无法提供准确值的情况，特别是裸土比例高、植被稀少或植物中叶绿素含量低的情况。
公式：
MSAVI = (2 * (NIR + 1) - sqrt ((2 * NIR + 1)^2 - 8 * (NIR - RED))) / 2
特点：由于 MSAVI 针对土壤效应进行了调整，并且对田间的早期植被敏感，因此即使地球上
几乎没有作物覆盖，它也能正常工作。
何时使用：MSAVI 在作物生产季节刚开始时很有用 - 当幼苗开始生长时。
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/msavi.htm
"""

GNDVITip = """
绿光归一化差值植被指数 (GNDVI) 是用于评估光合活性的植被指数，并且是用于确定植物冠层吸收的水氮的常用植被指数。
在没有红波段时，检测枯萎或老化的作物并测量叶子中的氮含量，监测茂密树冠或成熟阶段的植被。
公式：
GNDVI = (NIR - Green) / (NIR + Green)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/gnvdi.htm
"""

SAVITip = """
调节土壤的植被指数 (SAVI) 是试图通过土壤亮度校正系数最小化土壤亮度影响的植被指数。
它通常用在植被覆盖率较低的干旱区域，其输出值在 -1.0 到 1.0 之间。
植被稀疏区域，土壤暴露，会影响红波段和近红外波段的反射率值，从而影响 NDVI 的估算结果。
为了消除土壤背景的影响，Huete 提出了土壤调节植被指数，在 NDVI 的基础上加入土壤调节因子 L。
L 从 -1 到 +1 不等，具体取决于问题区域的绿色植被密度。
在绿色植被高的地区 L=0，在这种情况下，SAVI 与 NDVI 相同。相反，对于低绿色植被区，L = 1。
最典型的是，L 设置为 0.5 以适应大多数土地覆盖。
适用于分析青苗；适用于植被稀疏（不到总面积的 15%）和裸露土壤表面的干旱地区。
公式：
SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/savi.htm
"""

OSAVITip = """
OSAVI 植被指数是修改后的 SAVI，也使用 NIR 和红光谱中的反射率。
两个指标的区别在于 OSAVI 考虑了冠层背景调整因子的标准值（0.16）。
当冠层覆盖率较低时，与 SAVI 相比，该调整允许 OSAVI 的土壤变化更大。
OSAVI 对超过 50% 的冠层覆盖率具有更好的敏感性。
公式：
OSAVI = (NIR - RED) / (NIR + RED + 0.16)
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

ARVITip = """
耐大气植被指数 (ARVI) 对大气因素（例如气溶胶）相对不敏感。
如公式所示，Kaufman 与Tanré通过将红波段测量值加倍并增加蓝波段来校正 NDVI，以减轻大气散射效应。
与其他指标相比，ARVI对气溶胶不敏感，特别适用于监测因燃烧秸秆的农田和经常被烟尘覆盖的热带山区。
适用于大气气溶胶含量高的地区（如雨、雾、灰尘、烟雾、空气污染）。
公式：
ARVI = (NIR - (2 * RED) + BLUE) / (NIR + (2 * RED) + BLUE)
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

EVITip = """
增强型植被指数 (EVI) 是一个经过优化的植被指数，它类似于 NDVI，但是对于背景和大气噪音不是很敏感。
EVI 相比于 NDVI 具有较强的抗大气干扰能力以及抗噪音能力，更适用于气溶胶含量较高的天气状况下，以及植被茂盛区。
适用于分析具有大量叶绿素的地球区域（如热带雨林），最好是地形影响最小的区域（非山区）。
公式：
EVI = 2.5*(NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/evi.htm
"""

SIPITip = """
结构不敏感色素植被指数 (SIPI) 有利于分析具有可变冠层结构的植被。它估计了类胡萝卜素与叶绿素的比率：增加的值表明植被压力。
增加的 SIPI 值（高类胡萝卜素和低叶绿素）可能意味着作物病害，通常会导致植被中的叶绿素损失。
适用于在冠层结构或 LAI 高度可变的地区监测植物健康，以识别作物病害或其他压力原因的早期迹象。
公式:
SIPI = (NIR - BLUE) / (NIR - RED)
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

GCITip = """
绿色叶绿素植被指数 (GCI) 用于估计各种植物中叶绿素的含量。
叶绿素含量反映植被的生理状态；它在受胁迫的植物中降低，因此可以用作植被健康的衡量标准。
通过使用具有宽 NIR 和绿色波长的卫星传感器，可以通过 GCI 植被指数更好地预测叶绿素量。
适用于监测季节性、环境压力或使用的杀虫剂对植被健康的影响。
公式：
GCI = NIR / GREEN - 1
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

NDWITip = """
归一化差值水体指数（NDWI）用绿光波段和近红外波段的差异比值来增强水体信息，并减弱植被、土壤、建筑物等地物的信息。
该指数在纯水体提取方面具有很大的优势，然而该指数不能很好地抑制山体阴影以及高建筑物阴影。
适用于检测被淹的农田；现场分配洪水；检测灌溉农田；湿地分配。
公式：
NDWI = (GREEN - NIR) / (GREEN + NIR)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/ndwi.htm
"""

MNDWITip = """
针对 NDWI 不能很好地抑制高建筑物阴影的问题，
徐涵秋在 NDVI 的基础上提出了改进的归一化差值水体指数（MNDWI），
将中红外波段替代近红外波段。S1为中红外 1 波段地表反射率。
利用该公式计算出来的建筑物的 MNDWI 值会明显减小，
因此能在一定程度上抑制高建筑物的阴影，但是不能较好地去除冰雪或者山体阴影的影响。
适用于存在高建筑物的阴影的水体。
公式：
MNDWI = (GREEN - S1) / (GREEN + S1)
来源：
https://www.gisrsdata.com/pages/9a8b5b
"""

NDMITip = """
归一化差值水分指数（NDMI）是 Hardisky 等人通过计算近红外与短波红外之间的差异来定量化反映植被冠层的水分含量情况。
特点：在卫星遥感数据中，由于植被在短波红外波段对水分的强吸收，导致植被在短波红外波段的反射率相对于近红外波段的反射率要小，
因此 NDMI 与冠层水分含量高度相关，可以用来估计植被水分含量，
而且 NDMI 与地表温度之间存在较强的相关性，因此也常用于分析地表温度的变化情况。
适用于查看作物水分含量与地表温度的变化情况。
公式：
NDMI = (NIR - S1) / (NIR + S1)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/ndmi.htm
"""

VARITip = """
可见大气阻力指数 (VARI) 非常适合 RGB 或彩色图像，因为它适用于电磁光谱的整个可见部分（包括红色、绿色和蓝色波段）。
它的具体任务是在强烈的大气影响下增强植被，同时平滑光照变化。
VARI 可用于以下卫星传感器：Sentinel-2、Landsat-8、GeoEye-1、Pleiades-1、Quickbird 和 IKONOS。
由于对大气影响的敏感性较低，VARI 在不同大气厚度条件下对植被监测的误差小于 10%。
何时使用：当需要对大气影响的敏感性最低时，进行作物状态评估。
公式：
VARI = (GREEN - RED) / (GREEN + RED - BLUE)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/vari.htm
"""

NBRTip = """
归一化燃烧指数（NBR）是 Lopez 等人提出来的，通过计算近红外波段和短波红外波段的比值来增强火烧迹地的特征信息。
根据定义，标准化燃烧率用于突出火灾后的燃烧区域。NBR 植被指数方程包括 NIR 和 SWIR 波长的测量值：
健康植被在 NIR 光谱中显示出高反射率，而最近烧毁的植被区域在 SWIR 光谱中具有高反射率。
该植被指数计算基于具有 NIR 和 SWIR 波段的栅格图像，例如来自 Landsat-7、Landsat-8 或 MODIS。
值的范围在 +1 和 -1 之间。
NBR 指数在过去几年中变得尤为重要，因为极端天气条件导致近期破坏森林生物量的野火显着增加。
适用于火烧迹地信息提取以及监测火烧区域植被的恢复状况。
公式：
NBR = (NIR - SWIR) / (NIR + SWIR)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/nbr.htm
"""

NDSITip = """
归一化差分雪盖指数 (NDSI) 用于在忽略云覆盖的情况下，
使用 MODIS（波段 4 和波段 6）和 Landsat TM（波段 2 和波段 5）识别雪覆盖。
因为该指数为比值型，所以同样会减轻大气效应。
在这些的波段中，雪在 SWIR 具有高反射率并且在可见光绿色波段具有低反射率。
而在这些波段中，云的反射率都很高。因此此指数可用于区分云和雪。
公式：
NDSI = (GREEN - SWIR) / (GREEN + SWIR)
来源：
https://www.gisrsdata.com/pages/9a8b5b
https://pro.arcgis.com/zh-cn/pro-app/latest/arcpy/image-analyst/ndsi.htm
"""



class SelectCalcTemplateDialogClass(Ui_selectCalcTemplateDialog,QDialog):
    def __init__(self,bandList,parent=None):
        super().__init__(parent)
        self.parentWindow = parent
        self.bandList : list = bandList
        self.setupUi(self)
        self.initMember()
        self.initUI()
        self.connectFunc()
    
    def initMember(self):
        self.templateString = None
    
    def initUI(self):
        self.setWindowFlags(self.windowFlags() &~ Qt.WindowContextHelpButtonHint)
        self.redBandCb.addItems(self.bandList)
        self.greenBandCb.addItems(self.bandList)
        self.blueBandCb.addItems(self.bandList)
        self.nirBandCb.addItems(self.bandList)
        self.redEdgeBandCb.addItems(self.bandList)
        self.s1BandCb.addItems(self.bandList)
        self.swirBandCb.addItems(self.bandList)

        if len(self.bandList) == 3:
            self.redBandCb.setCurrentIndex(0)
            self.greenBandCb.setCurrentIndex(1)
            self.blueBandCb.setCurrentIndex(2)
        elif len(self.bandList) > 3:
            self.redBandCb.setCurrentIndex(2)
            self.greenBandCb.setCurrentIndex(1)
            self.blueBandCb.setCurrentIndex(0)
            self.nirBandCb.setCurrentIndex(3)

        self.ndviPb.installEventFilter(ToolTipFilter(self.ndviPb))
        self.ndviPb.setToolTip(NDVITip)

        self.reclPb.installEventFilter(ToolTipFilter(self.reclPb))
        self.reclPb.setToolTip(REClTip)

        self.ndrePb.installEventFilter(ToolTipFilter(self.ndrePb))
        self.ndrePb.setToolTip(NDRETip)

        self.msaviPb.installEventFilter(ToolTipFilter(self.msaviPb))
        self.msaviPb.setToolTip(MSAVITip)

        self.gndviPb.installEventFilter(ToolTipFilter(self.gndviPb))
        self.gndviPb.setToolTip(GNDVITip)

        self.saviPb.installEventFilter(ToolTipFilter(self.saviPb))
        self.saviPb.setToolTip(SAVITip)

        self.osaviPb.installEventFilter(ToolTipFilter(self.osaviPb))
        self.osaviPb.setToolTip(OSAVITip)

        self.arviPb.installEventFilter(ToolTipFilter(self.arviPb))
        self.arviPb.setToolTip(ARVITip)

        self.eviPb.installEventFilter(ToolTipFilter(self.eviPb))
        self.eviPb.setToolTip(EVITip)

        self.sipiPb.installEventFilter(ToolTipFilter(self.sipiPb))
        self.sipiPb.setToolTip(SIPITip)

        self.gciPb.installEventFilter(ToolTipFilter(self.gciPb))
        self.gciPb.setToolTip(GCITip)

        self.ndwiPb.installEventFilter(ToolTipFilter(self.ndwiPb))
        self.ndwiPb.setToolTip(NDWITip)

        self.mndwiPb.installEventFilter(ToolTipFilter(self.mndwiPb))
        self.mndwiPb.setToolTip(MNDWITip)

        self.ndmiPb.installEventFilter(ToolTipFilter(self.ndmiPb))
        self.ndmiPb.setToolTip(NDMITip)

        self.variPb.installEventFilter(ToolTipFilter(self.variPb))
        self.variPb.setToolTip(VARITip)

        self.nbrPb.installEventFilter(ToolTipFilter(self.nbrPb))
        self.nbrPb.setToolTip(NBRTip)

        self.ndsiPb.installEventFilter(ToolTipFilter(self.ndsiPb))
        self.ndsiPb.setToolTip(NDSITip)
    
    def connectFunc(self):
        self.ndviPb.clicked.connect(self.ndviPbClicked)
        self.reclPb.clicked.connect(self.reclPbClicked)
        self.ndrePb.clicked.connect(self.ndrePbClicked)
        self.msaviPb.clicked.connect(self.msavisPbClicked)
        self.gndviPb.clicked.connect(self.gndviPbClicked)
        self.saviPb.clicked.connect(self.saviPbClicked)
        self.osaviPb.clicked.connect(self.osaviPbClicked)
        self.arviPb.clicked.connect(self.arviPbClicked)
        self.eviPb.clicked.connect(self.eviPbClicked)
        self.sipiPb.clicked.connect(self.sipiPbClicked)
        self.gciPb.clicked.connect(self.gciPbClicked)
        self.ndwiPb.clicked.connect(self.ndwiPbClicked)
        self.mndwiPb.clicked.connect(self.mndwiPbClicked)
        self.ndmiPb.clicked.connect(self.ndmiPbClicked)
        self.variPb.clicked.connect(self.variPbClicked)
        self.nbrPb.clicked.connect(self.nbrPbClicked)
        self.ndsiPb.clicked.connect(self.ndsiPbClicked)
    
    def ndviPbClicked(self):
        templateString = " ({NIR} - {RED}) / ({NIR} + {RED}) ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def reclPbClicked(self):
        templateString = " ({NIR} / {RED}) - 1 ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def ndrePbClicked(self):
        templateString = " ({NIR} - {RED_EDGE}) / ({NIR} + {RED_EDGE}) ".format(
            NIR = self.nirBandCb.currentText(),
            RED_EDGE = self.redBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def msavisPbClicked(self):
        templateString = " (2 * ({NIR} + 1) - sqrt ((2 * {NIR} + 1)^2 - 8 * ({NIR} - {RED}))) / 2 ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def gndviPbClicked(self):
        templateString = " ({NIR} - {GREEN}) / ({NIR} + {GREEN}) ".format(
            NIR = self.nirBandCb.currentText(),
            GREEN = self.greenBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def saviPbClicked(self):
        templateString = " ({NIR} - {RED}) / ({NIR} + {RED} + {L}) * (1 + {L}) ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText(),
            L = "L"
        )
        self.templateString = templateString
        self.close()

    def osaviPbClicked(self):
        templateString = " ({NIR} - {RED}) / ({NIR} + {RED} + 0.16)".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def arviPbClicked(self):
        templateString = " ({NIR} - (2 * {RED}) + {BLUE}) / ({NIR} + (2 * {RED}) + {BLUE})".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText(),
            BLUE = self.blueBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def eviPbClicked(self):
        templateString = " 2.5*({NIR} - {RED}) / ({NIR} + 6*{RED} - 7.5*{BLUE} + 1) ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText(),
            BLUE = self.blueBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def sipiPbClicked(self):
        templateString = " ({NIR} - {BLUE}) / ({NIR} - {RED}) ".format(
            NIR = self.nirBandCb.currentText(),
            RED = self.redBandCb.currentText(),
            BLUE = self.blueBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def gciPbClicked(self):
        templateString = " ({NIR} / {GREEN}) - 1 ".format(
            NIR = self.nirBandCb.currentText(),
            GREEN = self.greenBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def ndwiPbClicked(self):
        templateString = " ({GREEN} - {NIR}) / ({GREEN} + {NIR}) ".format(
            NIR = self.nirBandCb.currentText(),
            GREEN = self.greenBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def mndwiPbClicked(self):
        templateString = " ({GREEN} - {S1}) / ({GREEN} + {S1}) ".format(
            S1 = self.s1BandCb.currentText(),
            GREEN = self.greenBandCb.currentText()
        )
        self.templateString = templateString
        self.close()
    
    def ndmiPbClicked(self):
        templateString = " ({NIR} - {S1}) / ({NIR} + {S1}) ".format(
            NIR = self.nirBandCb.currentText(),
            S1 = self.s1BandCb.currentText()
        )
        self.templateString = templateString
        self.close()
    
    def variPbClicked(self):
        templateString = " ({GREEN} - {RED}) / ({GREEN} + {RED} - {BLUE}) ".format(
            RED = self.redBandCb.currentText(),
            GREEN = self.greenBandCb.currentText(),
            BLUE = self.blueBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def nbrPbClicked(self):
        templateString = " ({NIR} - {SWIR}) / ({NIR} + {SWIR}) ".format(
            NIR = self.nirBandCb.currentText(),
            SWIR = self.swirBandCb.currentText()
        )
        self.templateString = templateString
        self.close()

    def ndsiPbClicked(self):
        templateString = " ({GREEN} - {SWIR}) / ({GREEN} + {SWIR}) ".format(
            GREEN = self.greenBandCb.currentText(),
            SWIR = self.swirBandCb.currentText()
        )
        self.templateString = templateString
        self.close()
