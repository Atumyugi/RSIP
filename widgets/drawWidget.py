
from ui.jointWorkWindow import Ui_YoyiJointWorkWindow
from PyQt5.QtCore import QVariant,QStringListModel,QCoreApplication
from PyQt5 import QtCore
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout,QStatusBar,QAbstractItemView,\
    QTableWidgetItem, QHeaderView,QMainWindow,QSpacerItem,\
        QDialog,QColorDialog,QMessageBox,QSizePolicy,QProgressBar,QDockWidget,QFileDialog,QHBoxLayout,QApplication
from qgis.core import QgsLayerTreeModel,QgsRectangle,QgsFeature,QgsVectorTileLayer,QgsRasterLayer,QgsProject,Qgis,QgsColorRampShader\
    ,QgsPalettedRasterRenderer,QgsVectorLayer,QgsField,QgsVectorFileWriter,QgsTextFormat,\
    QgsSnappingConfig,QgsTolerance,QgsSimpleLineSymbolLayer,QgsSingleSymbolRenderer,QgsGeometry,\
    QgsDataSourceUri,QgsMapLayerType
from qgis.gui import QgsMapToolIdentifyFeature,QgsLayerTreeView,QgsMessageBar,QgsMapCanvas,QgsMapToolPan
import traceback

from qfluentwidgets import MessageBox,BodyLabel,SubtitleLabel,setFont,InfoBar,InfoBarPosition,ToolTipFilter,PrimarySplitPushButton

from appConfig import *

from widgets.draw_dialog_webSelectProjectTypeDialog import WebSelectProjectTypeDialogClass
from widgets.draw_dialog_webSampleProjectListDialog import WebSampleProjectListDialogClass
from widgets.draw_dialog_webAttrEditDialog import WebAttrEditDialogClass
from widgets.draw_dialog_webSelectRejectReason import WebSelectRejectReasonDialogClass
from widgets.draw_dialog_webInputBookmarkNameDialog import WebInpuBookmarkNameDialogClass
from widgets.commonTool_openXYZTilesDialog import OpenXYZTilesDialogClass

from yoyiUtils.custom_maptool import DoubleMapCanvas,DoublePanTool,IdentifyRasterMapTool,RecTangleSelectFeatureMapTool
from yoyiUtils.custom_maptool_web import *
from yoyiUtils.custom_widget import YoyiTreeLayerWidget,BetterPillToolButton
from yoyiUtils.custom_widget import YoyiTreeView
from yoyiUtils.yoyiRenderProp import yoyiShpPropClass,createShpLabel
from yoyiUtils.yoyiSamRequest import rsdmWeber
from yoyiUtils.qgisLayerUtils import loadWmsasLayer
PROJECT = QgsProject.instance()

# dialog = WebSampleProjectListDialogClass(self.parentWindow.userId,self)
# dialog.exec()
# feat.setGeometry(QgsGeometry.fromWkt(wkt))
class JointWorkWindowClass(Ui_YoyiJointWorkWindow,QMainWindow):
    def __init__(self, parent=None):
        super(JointWorkWindowClass, self).__init__(parent)
        self.parentWindow = parent
        self.setting = yoyiSetting()
        self.spMapCanvas = None
        self.setupUi(self)
        self.setupDIYUI()
        #self.dockWidgetTop.setTitleBarWidget(QWidget(self))

        self.emptyLabel = SubtitleLabel("请点击右上角↗打开项目",self)
        self.emptyLabel.setAlignment(Qt.AlignCenter)
        setFont(self.emptyLabel, 35)
        self.emptyLabel_right = SubtitleLabel("请点击右上角↗打开项目",self)
        self.emptyLabel_right.setAlignment(Qt.AlignCenter)
        setFont(self.emptyLabel_right, 35)

        self.hl = QHBoxLayout(self.leftFrame)
        self.hl.setContentsMargins(0, 0, 0, 0)
        self.hl.addWidget(self.emptyLabel)

        self.hl_right = QHBoxLayout(self.rightFrame)
        self.hl_right.setContentsMargins(0, 0, 0, 0)
        self.hl_right.addWidget(self.emptyLabel_right)
        
        self.spMapCanvas = DoubleMapCanvas(self)
        self.spMapCanvas.setParallelRenderingEnabled(True)
        self.spMapCanvas.setCachingEnabled(True)
        self.hl.addWidget(self.spMapCanvas)
        self.spMapCanvas.hide()

        self.rightMapCanvas = DoubleMapCanvas(self)
        self.rightMapCanvas.setParallelRenderingEnabled(True)
        self.rightMapCanvas.setCachingEnabled(True)
        self.hl_right.addWidget(self.rightMapCanvas)
        self.rightMapCanvas.hide()

        self.spMapCanvas.setDoubleCanvas(self.rightMapCanvas)
        self.rightMapCanvas.setDoubleCanvas(self.spMapCanvas)

        self.spMapCanvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4490"))
        self.rightMapCanvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4490"))

        self.mapSetting: QgsMapSettings = self.spMapCanvas.mapSettings()
        self.mapCrs = self.mapSetting.destinationCrs()

        # yoyiTrans
        self.yoyiTrs = self.parentWindow.yoyiTrans
        self.yspc = yoyiShpPropClass()

        # 左侧图层树
        vl = QVBoxLayout(self.dockWidgetContentsLeft)

        self.layerTree = YoyiTreeView(self.spMapCanvas,self.yoyiTrs,self,extraMapCanvas=self.rightMapCanvas,openQuickKey=True)
        vl.addWidget(self.layerTree.layerTreeView)

        # 状态栏
        self.statusBar = QStatusBar(self)
        self.statusBar.setMaximumHeight(30)
        self.statusXY = BodyLabel('{:<40}'.format(''),self)  # x y 坐标状态
        self.statusBar.addWidget(self.statusXY)

        self.statusScaleComboBox = PrimarySplitPushButton(self) ## 比例尺状态
        #self.statusScaleComboBox.setFixedWidth(120)
        self.scaleMenu = RoundMenu(parent=self)
        scaleList = ["1:10","1:100","1:500", "1:1000", "1:2500", "1:5000", "1:10000", "1:25000", "1:100000", "1:500000", "1:1000000"]
        for scaleStr in scaleList:
            action = Action(text=scaleStr,parent=self)
            self.scaleMenu.addAction(action)
        self.scaleMenu.triggered.connect(self.changeScaleForString)
        self.statusScaleComboBox.setFlyout(self.scaleMenu)
        self.statusBar.addWidget(self.statusScaleComboBox)

        self.spMapCanvas.scaleChanged.connect(self.showScale)

        self.tempStatusLabel = BodyLabel('{:<40}'.format(''),self)  # 临时坐标状态
        self.statusBar.addWidget(self.tempStatusLabel)
        self.setStatusBar(self.statusBar)

        self.spMapCanvas.xyCoordinates.connect(self.showXY)
        self.rightMapCanvas.xyCoordinates.connect(self.showXY)

        # 书签
        self.bookMarkDict = {}
        self.bookMarkIndex = 1
        self.refreshBookMark()

        # 允许拖拽文件触发事件
        self.setAcceptDrops(True)

        # 左下要素表一些初始化
        self.featurePageSizeComboBox.addItem(text="10/条页",userData=10)
        self.featurePageSizeComboBox.addItem(text="20/条页",userData=20)
        self.featurePageSizeComboBox.addItem(text="50/条页",userData=50)
        self.featurePageSizeComboBox.setCurrentIndex(0)

        self.featureStatusFilterCb.addItem(text="按时间倒序",userData='time')
        self.featureStatusFilterCb.addItem(text="按时间正序",userData=None)
        self.featureStatusFilterCb.addItem(text="按字段1倒序",userData='remark1des')
        self.featureStatusFilterCb.addItem(text="按字段1正序",userData='remark1')
        self.featureStatusFilterCb.addItem(text="按字段2倒序",userData='remark2des')
        self.featureStatusFilterCb.addItem(text="按字段2正序",userData='remark2')
        self.featureStatusFilterCb.addItem(text="按字段3倒序",userData='remark3des')
        self.featureStatusFilterCb.addItem(text="按字段3正序",userData='remark3')


        # 右侧格网一些初始化
        self.pageSizeComboBox.addItem(text="10/条页",userData=10)
        self.pageSizeComboBox.addItem(text="20/条页",userData=20)
        self.pageSizeComboBox.addItem(text="50/条页",userData=50)
        self.pageSizeComboBox.setCurrentIndex(0)

        self.controlList = [
            # 上面
            self.addRasterLayer,self.addVectorLayer,self.addXYZTilesLayer,
            self.rejectPointMapToolPb,self.commitMagicPB,self.addBookmarkPb,self.deleteBookmarkPb,
            self.leftChangePb1,self.leftChangePb2,self.rightChangePb3,self.rightChangePb4,
            self.leftBottomInfoPb,self.rightBottomInfoPb,self.selectFishnetMapToolPb,
            # 左下
            self.featurePageSizeComboBox,self.lastFeaturePagePb,self.nextFeaturePagePb,self.featureJumpPb,
            self.featureStatusFilterCb,self.featureTableWidget,
            # 右边上部分
            self.panMapToolPb,self.magicMapToolPb,self.polygonMapToolPb,self.rectangleMapToolPb,self.circleMapToolPb,self.pointMapToolPb,
            self.lastPb,self.selectMapToolPb,self.nextPb,self.rotateMapToolPb,self.rescaleMapToolPb,self.line2PolyMapToolPb,
            
            self.splitMapToolPb,self.vertexMapToolPb,self.reshapeMapToolPb,self.pasteMapToolPb,self.rejectPB,
            self.deleteFeaturePb,self.mergeMapToolPb,self.changeAttrPb,
            # 右边下部分
            self.pageSizeComboBox,
            self.lastPagePb,self.nextPagePb,self.jumpPb,self.TableWidget,
            # 状态栏
            self.statusScaleComboBox
        ]
        # 协同解译 部分控件不允许使用

        self.changeEnables(False)
        self.firstLoad = True
        self.rsdmReq = rsdmWeber()

        # 一些状态成员变量
        self.taskName = None
        self.taskId =None
        self.taskTypeId = None
        self.taskProjectType = None
        self.drawServerLayer = None
        self.fishnetServerLayer = None
        self.extraLayerDict = {}
        self.infoBar : InfoBar = None

        self.remark1PreAttr = None #选属性时候的index
        self.remark2PreAttr = None
        self.remark3PreAttr = None

        self.dontOpenWindow = False # 勾画完属性后直接不弹窗口直接勾画

        self.rejectMissIsChecked = False
        self.rejectFaultIsChecked = False
        self.rejectTrimIsChecked = False
        self.rejectClassIsChecked = False

        self.stopStatusConnect = False  # 停止某些connectFunc

        self.featureQueryList = [] #专业模式下 查询要素的list，留存还没有修改之前的要素id列表

        self.projectConnectFunc() # 项目相关
        self.featureTableConnectFunc() #属性表相关
        self.fishnetConnectFunc() # 渔网表更新相关
        self.topBarConnectFunc()
        self.mapToolConnectFunc() # 地图工具
        self.rightBarConnectFunc()
    
    def setupDIYUI(self):
        # qewrt
        self.panMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.panMapToolPb.setIcon(QIcon(':/img/resources/gis/gis_pan.png'))
        self.panMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.panMapToolPb.setToolTip('Pan (Q) Drag the Map Canvas to Move')
        self.panMapToolPb.installEventFilter(ToolTipFilter(self.panMapToolPb,0))
        self.panMapToolPb.setShortcut("Q")
        self.hl_qwer.addWidget(self.panMapToolPb)

        self.magicMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.magicMapToolPb.setIcon(QIcon(':/img/resources/infer/clsfy_magic.png'))
        self.magicMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.magicMapToolPb.setToolTip('Magic Wand (W) Intelligently Extracts Contours')
        self.magicMapToolPb.installEventFilter(ToolTipFilter(self.magicMapToolPb,0))
        self.magicMapToolPb.setShortcut("W")
        self.hl_qwer.addWidget(self.magicMapToolPb)

        self.polygonMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.polygonMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_polygon.png'))
        self.polygonMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.polygonMapToolPb.setToolTip('Draw Feature Tool (E) Double Click to Open Stream Mode, Single Click to Close')
        self.polygonMapToolPb.installEventFilter(ToolTipFilter(self.polygonMapToolPb,0))
        self.polygonMapToolPb.setShortcut("E")
        self.hl_qwer.addWidget(self.polygonMapToolPb)

        self.rectangleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rectangleMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_rectangle.png'))
        self.rectangleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rectangleMapToolPb.setToolTip('Draw Rectangle Feature Tool (R)')
        self.rectangleMapToolPb.installEventFilter(ToolTipFilter(self.rectangleMapToolPb,0))
        self.rectangleMapToolPb.setShortcut("R")
        self.hl_qwer.addWidget(self.rectangleMapToolPb)

        self.circleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.circleMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_circle.png'))
        self.circleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.circleMapToolPb.setToolTip('Draw Circle Feature Tool (T)')
        self.circleMapToolPb.installEventFilter(ToolTipFilter(self.circleMapToolPb,0))
        self.circleMapToolPb.setShortcut("T")
        self.hl_qwer.addWidget(self.circleMapToolPb)

        self.pointMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.pointMapToolPb.setIcon(QIcon(':/img/resources/gis/edit_point.png'))
        self.pointMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.pointMapToolPb.setToolTip('绘制点矢量 (Y)')
        self.pointMapToolPb.installEventFilter(ToolTipFilter(self.pointMapToolPb,0))
        self.pointMapToolPb.setShortcut("Y")
        self.hl_qwer.addWidget(self.pointMapToolPb)

        #asdfg
        self.lastPb = BetterPillToolButton(self.dockWidgetContents)
        self.lastPb.setIcon(QIcon(':/img/resources/last.png'))
        self.lastPb.setIconSize(QtCore.QSize(30,30))
        self.lastPb.setToolTip('last fishnet (A)')
        self.lastPb.installEventFilter(ToolTipFilter(self.lastPb,0))
        self.lastPb.setShortcut("A")
        self.lastPb.setCheckable(False)
        self.hl_asdf.addWidget(self.lastPb)

        self.selectMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.selectMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_select_multi.png'))
        self.selectMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.selectMapToolPb.setToolTip('Select Feature Tool (S) Drag to Move the Selected Feature, Right Click for Menu Bar')
        self.selectMapToolPb.installEventFilter(ToolTipFilter(self.selectMapToolPb,0))
        self.selectMapToolPb.setShortcut("S")
        self.hl_asdf.addWidget(self.selectMapToolPb)

        self.nextPb = BetterPillToolButton(self.dockWidgetContents)
        self.nextPb.setIcon(QIcon(':/img/resources/next.png'))
        self.nextPb.setIconSize(QtCore.QSize(30,30))
        self.nextPb.setToolTip('next fishnet (D)')
        self.nextPb.installEventFilter(ToolTipFilter(self.nextPb,0))
        self.nextPb.setShortcut("D")
        self.nextPb.setCheckable(False)
        self.hl_asdf.addWidget(self.nextPb)

        self.rotateMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rotateMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_rotate.png'))
        self.rotateMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rotateMapToolPb.setToolTip('Rotate Feature Tool (F)')
        self.rotateMapToolPb.installEventFilter(ToolTipFilter(self.rotateMapToolPb,0))
        self.rotateMapToolPb.setShortcut("F")
        self.hl_asdf.addWidget(self.rotateMapToolPb)

        self.rescaleMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.rescaleMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_scale.png'))
        self.rescaleMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.rescaleMapToolPb.setToolTip('rescale Feature Tool (G)')
        self.rescaleMapToolPb.installEventFilter(ToolTipFilter(self.rescaleMapToolPb,0))
        self.rescaleMapToolPb.setShortcut("G")
        self.hl_asdf.addWidget(self.rescaleMapToolPb)

        # self.identifyMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        # self.identifyMapToolPb.setIcon(QIcon(':/img/resources/gis/gis_identify.png'))
        # self.identifyMapToolPb.setIconSize(QtCore.QSize(30,30))
        # self.identifyMapToolPb.setToolTip('识别工具(H)')
        # self.identifyMapToolPb.installEventFilter(ToolTipFilter(self.identifyMapToolPb,0))
        # self.identifyMapToolPb.setShortcut("H")
        # self.hl_asdf.addWidget(self.identifyMapToolPb)

        self.line2PolyMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.line2PolyMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_line2Poly.png'))
        self.line2PolyMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.line2PolyMapToolPb.setToolTip('轨迹化面工具(H)')
        self.line2PolyMapToolPb.installEventFilter(ToolTipFilter(self.line2PolyMapToolPb,0))
        self.line2PolyMapToolPb.setShortcut("H")
        self.hl_asdf.addWidget(self.line2PolyMapToolPb)

        #zxcvb
        self.splitMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.splitMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_clip_polygon.png'))
        self.splitMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.splitMapToolPb.setToolTip('Cut Feature Tool (Z)')
        self.splitMapToolPb.installEventFilter(ToolTipFilter(self.splitMapToolPb,0))
        self.splitMapToolPb.setShortcut("Z")
        self.hl_zxcv.addWidget(self.splitMapToolPb)

        self.vertexMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.vertexMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_vertexTool.png'))
        self.vertexMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.vertexMapToolPb.setToolTip('Vertex Edit Tool (X)')
        self.vertexMapToolPb.installEventFilter(ToolTipFilter(self.vertexMapToolPb,0))
        self.vertexMapToolPb.setShortcut("X")
        self.hl_zxcv.addWidget(self.vertexMapToolPb)

        self.reshapeMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.reshapeMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_clip_1.png'))
        self.reshapeMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.reshapeMapToolPb.setToolTip('Reshape Feature Tool(C)')
        self.reshapeMapToolPb.installEventFilter(ToolTipFilter(self.reshapeMapToolPb,0))
        self.reshapeMapToolPb.setShortcut("C")
        self.hl_zxcv.addWidget(self.reshapeMapToolPb)

        self.pasteMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.pasteMapToolPb.setIcon(QIcon(':/img/resources/gis/gis_copyFeature.png'))
        self.pasteMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.pasteMapToolPb.setToolTip('Paste Feature Tool (V)')
        self.pasteMapToolPb.installEventFilter(ToolTipFilter(self.pasteMapToolPb,0))
        self.pasteMapToolPb.setShortcut("V")
        self.hl_zxcv.addWidget(self.pasteMapToolPb)

        self.rejectPB = BetterPillToolButton(self.dockWidgetContents)
        self.rejectPB.setIcon(QIcon(':/img/resources/gis/shp_fillhole.png'))
        self.rejectPB.setIconSize(QtCore.QSize(30,30))
        self.rejectPB.setToolTip('驳回 (B)')
        self.rejectPB.installEventFilter(ToolTipFilter(self.rejectPB,0))
        self.rejectPB.setShortcut("B")
        self.rejectPB.setCheckable(False)
        self.hl_zxcv.addWidget(self.rejectPB)

        self.lineBuffer2PolyPb = BetterPillToolButton(self.dockWidgetContents)
        self.lineBuffer2PolyPb.setIcon(QIcon(':/img/resources/gis/shp_lineBuffer.png'))
        self.lineBuffer2PolyPb.setIconSize(QtCore.QSize(30,30))
        self.lineBuffer2PolyPb.setToolTip('线缓冲化面工具 (N)')
        self.lineBuffer2PolyPb.installEventFilter(ToolTipFilter(self.lineBuffer2PolyPb,0))
        self.lineBuffer2PolyPb.setShortcut("N")
        self.hl_zxcv.addWidget(self.lineBuffer2PolyPb)
        # F1 F2
        self.mergeMapToolPb = BetterPillToolButton(self.dockWidgetContents)
        self.mergeMapToolPb.setIcon(QIcon(':/img/resources/gis/shp_merge.png'))
        self.mergeMapToolPb.setIconSize(QtCore.QSize(30,30))
        self.mergeMapToolPb.setToolTip('Merge Selected Features (F1)')
        self.mergeMapToolPb.installEventFilter(ToolTipFilter(self.mergeMapToolPb,0))
        self.mergeMapToolPb.setShortcut("F1")
        self.mergeMapToolPb.setCheckable(False)
        self.hl_f1234.addWidget(self.mergeMapToolPb)

        self.changeAttrPb = BetterPillToolButton(self.dockWidgetContents)
        self.changeAttrPb.setIcon(QIcon(':/img/resources/gis/shp_modify_attr.png'))
        self.changeAttrPb.setIconSize(QtCore.QSize(30,30))
        self.changeAttrPb.setToolTip('Modify Attributes (F2)')
        self.changeAttrPb.installEventFilter(ToolTipFilter(self.changeAttrPb,0))
        self.changeAttrPb.setShortcut("F2")
        self.changeAttrPb.setCheckable(False)
        self.hl_f1234.addWidget(self.changeAttrPb)

        self.staticPb = BetterPillToolButton(self.dockWidgetContents)
        self.staticPb.setIcon(QIcon(':/img/resources/tifProcess/calNorm.png'))
        self.staticPb.setIconSize(QtCore.QSize(30,30))
        self.staticPb.setToolTip('统计信息 (F3)')
        self.staticPb.installEventFilter(ToolTipFilter(self.staticPb,0))
        self.staticPb.setShortcut("F3")
        self.staticPb.setCheckable(False)
        self.hl_f1234.addWidget(self.staticPb)

    def retranslateDiyUI(self):
        _translate = QCoreApplication.translate

        self.panMapToolPb.setToolTip(_translate("DIYDialog", "Pan (Q) Drag the Map Canvas to Move"))
        self.magicMapToolPb.setToolTip(_translate("DIYDialog", "Magic Wand (W) Intelligently Extracts Contours"))
        self.polygonMapToolPb.setToolTip(_translate("DIYDialog", "Draw Feature Tool (E) Double Click to Open Stream Mode, Single Click to Close"))
        self.rectangleMapToolPb.setToolTip(_translate("DIYDialog", "Draw Rectangle Feature Tool (R)"))
        self.circleMapToolPb.setToolTip(_translate("DIYDialog", "Draw Circle Feature Tool (T)"))

        self.lastPb.setToolTip(_translate("DIYDialog", "last fishnet (A)"))
        self.selectMapToolPb.setToolTip(_translate("DIYDialog", "Select Feature Tool (S) Drag to Move the Selected Feature, Right Click for Menu Bar"))
        self.nextPb.setToolTip(_translate("DIYDialog", "next fishnet (D)"))
        self.rotateMapToolPb.setToolTip(_translate("DIYDialog", "Rotate Feature Tool (F)"))
        self.rescaleMapToolPb.setToolTip(_translate("DIYDialog", "rescale Feature Tool (G)"))

        self.splitMapToolPb.setToolTip(_translate("DIYDialog", "Cut Feature Tool (Z)"))
        self.vertexMapToolPb.setToolTip(_translate("DIYDialog", "Vertex Edit Tool (X)"))
        self.reshapeMapToolPb.setToolTip(_translate("DIYDialog", "Reshape Feature Tool(C)"))
        self.pasteMapToolPb.setToolTip(_translate("DIYDialog", "Paste Feature Tool (V)"))

        self.deleteFeaturePb.setToolTip(_translate("DIYDialog", "Delete Feature Tool (Del)"))
        self.mergeMapToolPb.setToolTip(_translate("DIYDialog", "Merge Selected Features (F1)"))
        self.changeAttrPb.setToolTip(_translate("DIYDialog", "Modify Attributes (F2)"))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, a0, QDropEvent=None):
        if self.taskId:
            mimeData: QtCore.QMimeData = a0.mimeData()
            filePathList = [u.path()[1:] for u in mimeData.urls()]
            print(filePathList)
            for filePath in filePathList:
                if osp.isfile(filePath) and filePath.split(".")[-1] in ["tif", "TIF", "tiff", "TIFF", "GTIFF", "png", "jpg","shp","gpkg"]:
                    self.layerTree.addExtraItemByFile(filePath,needMsg=False)
    
    def showXY(self, point):
        x = point.x()
        y = point.y()
        self.statusXY.setText(f'{x:.6f}, {y:.6f}')
    
    def showScale(self, scale):
        self.statusScaleComboBox.setText(f"1:{int(scale)}")
    
    def changeScaleForString(self,action):
        scaleStr = action.text()
        try:
            left,right = scaleStr.split(":")[0],scaleStr.split(":")[-1]
            if int(left)==1 and int(right)>0 and int(right)!=int(self.spMapCanvas.scale()):
                self.spMapCanvas.zoomScale(int(right))
                self.rightMapCanvas.zoomScale(int(right))
                #self.spMapCanvas.refresh()
                #self.rightMapCanvas.refresh()
        except Exception as e:
            print(traceback.format_exc())

    def changeEnables(self,states):
        for control in self.controlList:
            control.setEnabled(states)
        
    def delMapTool(self):
        self.polygonMapTool = None
        self.rectangleMapTool = None
        self.circleMapTool = None
        self.selectMapTool = None
        self.rotateMapTool = None
        self.rescaleMapTool = None
        self.pasteMapTool = None
        self.vertexMapTool = None
        self.reshapeMapTool = None
        self.splitMapTool = None
        self.fillHoleMapTool = None

        self.polygonMapToolRight = None
        self.rectangleMapToolRight = None
        self.circleMapToolRight = None
        self.selectMapToolRight = None
        self.rotateMapToolRight = None
        self.rescaleMapToolRight = None
        self.pasteMapToolRight = None
        self.vertexMapToolRight = None
        self.reshapeMapToolRight = None
        self.splitMapToolRight = None
        self.fillHoleMapToolRight = None

    def unsetMemberUI(self):
        self.panMapToolPb.click()
        self.delMapTool()
        self.layerTree.saveLayerHistory(self.taskId)
        self.layerTree.clearTreeView()
        

        self.tifLayer = None
        self.tifIILayer = None
        self.drawLayer = None
        self.taskId = None
        self.extraLayerDict = {}

        # 停止 connect
        self.stopStatusConnect = True
    
    def initMember(self):
        self.tifLayer = loadWmsasLayer(self.tifPath,self.tifName)
        self.tifIILayer = loadWmsasLayer(self.tifPathII,self.tifNameII)
        self.samInfer = samWeber(self.tifPath)
        self.samInferRight = samWeber(self.tifPathII)

        self.drawLayer = QgsVectorLayer("MultiPolygon", "#INTERDRAW#交互式勾画图层", "memory")
        pr = self.drawLayer.dataProvider()
        pr.addAttributes([QgsField("FeatureId", QVariant.String),
                          QgsField("remark1", QVariant.String),
                          QgsField("remark2", QVariant.String),
                          QgsField("remark3", QVariant.String),
                          QgsField("isUpdate",QVariant.Int)])
        self.drawLayer.updateFields()  # 告诉矢量图层从提供者获取更改
        self.drawLayer.setRenderer(self.yspc.createDiySymbol(color=f"255,0,0",lineWidth='0.7',isFull=False))

        self.drawLayer.setCrs(QgsCoordinateReferenceSystem("EPSG:4490"))
        self.drawLayer.triggerRepaint()
        self.drawLayer.startEditing()

        self.layerTree.bottomLayer = self.tifLayer
        self.layerTree.extraBottomLayer = self.tifIILayer
        self.layerTree.drawBottomLayer = self.drawLayer
        self.initUI()

    def initUI(self):
        # 初始化 勾画模式类型 False为普通模式 True为专业模式
        self.preloadMode = False
        # 初始化图层排列
        self.emptyLabel.hide()
        self.emptyLabel_right.hide()
        self.spMapCanvas.show()
        self.rightMapCanvas.show()

        # 项目名
        self.projectLabel.setText(self.taskName)
        netMode = yoyiSetting().configSettingReader.value('netMode',type=int)
        geoserverUrl  = GeoserverUrlDict[netMode]

        for name,url in self.extraLayerDict.items():
            self.layerTree.addExtraItemByUrl(url,"辅助@"+name,isLocalType=False,isChecked=False)

        uriExtent = QgsDataSourceUri()
        uriExtent.setParam('url',f"{geoserverUrl}/geoserver/china/wms?version%3D1.1.1")
        uriExtent.setParam('crs','EPSG:4326')
        uriExtent.setParam('dpiMode','4')
        uriExtent.setParam('format','image/png')
        uriExtent.setParam('layers','china')
        uriExtent.setParam('styles','')
        uriExtent.setParam('IgnoreGetMapUrl','1')
        self.layerTree.addExtraItemByUrl(uriExtent,"省市县界",isLocalType=False)

        uri = QgsDataSourceUri()
        # if self.taskProjectType in [appConfig.WebDrawQueryType.Review,appConfig.WebDrawQueryType.Random]:
        if self.taskProjectType == appConfig.WebDrawQueryType.Review:
            uri.setParam('url',f"{geoserverUrl}/geoserver/interpretation_tool/wms?version%3D1.1.1&CQL_FILTER=(task_id='{self.taskId}' AND audit_name='{self.parentWindow.userId}')")
        elif self.taskProjectType == appConfig.WebDrawQueryType.Random:
            uri.setParam('url',f"{geoserverUrl}/geoserver/interpretation_tool/wms?version%3D1.1.1&CQL_FILTER=(task_id='{self.taskId}' AND random_name='{self.parentWindow.userId}')")
        else:
            uri.setParam('url',f"{geoserverUrl}/geoserver/interpretation_tool/wms?version%3D1.1.1&CQL_FILTER=(task_id='{self.taskId}' AND repair_name='{self.parentWindow.userId}')")
        uri.setParam('crs','EPSG:4490')
        uri.setParam('dpiMode','4')
        uri.setParam('format','image/png')
        uri.setParam('layers','forest_plot_grid')
        uri.setParam('styles','')
        uri.setParam('IgnoreGetMapUrl','1')
        self.fishnetServerLayer = self.layerTree.addExtraItemByUrl(uri,"作业渔网",isLocalType=False)

        
        uriRejectPoint = QgsDataSourceUri()
        uriRejectPoint.setParam('url',f"{geoserverUrl}/geoserver/interpretation_tool/wms?version%3D1.1.1&CQL_FILTER=task_id='{self.taskId}'")
        uriRejectPoint.setParam('crs','EPSG:4490')
        uriRejectPoint.setParam('dpiMode','4')
        uriRejectPoint.setParam('format','image/png')
        uriRejectPoint.setParam('layers','back_point')
        uriRejectPoint.setParam('styles','')
        uriRejectPoint.setParam('IgnoreGetMapUrl','1')
        self.rejectPointLayer = self.layerTree.addExtraItemByUrl(uriRejectPoint,"打标点位",isLocalType=False)

        if self.preloadMode:
            self.drawServerLayer = self.drawLayer
            createShpLabel(self.drawLayer,f'concat("remark1" ,\' \',"remark2",\' \',"remark3")',r=255,g=255,b=20,isExpression=True)
            self.drawLayer.triggerRepaint()
        else:
            uriDraw = QgsDataSourceUri()
            uriDraw.setParam('url',f"{geoserverUrl}/geoserver/interpretation_tool/wms?version%3D1.1.1&CQL_FILTER=task_id='{self.taskId}'")
            uriDraw.setParam('crs','EPSG:4490')
            uriDraw.setParam('dpiMode','4')
            uriDraw.setParam('format','image/png')
            uriDraw.setParam('layers','forest_plot_refine')
            uriDraw.setParam('styles','')
            uriDraw.setParam('IgnoreGetMapUrl','1')
            self.drawServerLayer = self.layerTree.addExtraItemByUrl(uriDraw,"作业矢量底图",isLocalType=False)

        # 加载历史记录
        self.layerTree.loadLayerHistory(self.taskId)

        # 初始化右侧的格网表
        self.pageSizeComboBox.setCurrentIndex(0)
        self.TableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.TableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.TableWidget.setWordWrap(True)
        self.TableWidget.setColumnCount(3)
        self.TableWidget.setHorizontalHeaderLabels(['格网ID','当前状态','工作角色'])
        self.TableWidget.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.TableWidget.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.TableWidget.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        # 初始化左侧的属性表
        self.featurePageSizeComboBox.setCurrentIndex(0)
        self.featureTableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.featureTableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.featureTableWidget.setWordWrap(True)
        self.featureTableWidget.setColumnCount(4)
        self.featureTableWidget.setHorizontalHeaderLabels(['FID','字段1','字段2','字段3'])
        self.featureTableWidget.horizontalHeader().setMinimumSectionSize(100)
        self.featureTableWidget.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.featureTableWidget.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.featureTableWidget.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)

        # 初始化状态筛选 comboBox
        self.stopStatusConnect = True
        if self.taskProjectType == appConfig.WebDrawQueryType.Draw:
            self.statusFilterCb.clear()
            for statusText,statusCode in appConfig.DRAW_JINGXIU_STATUS_DICT.items():
                self.statusFilterCb.addItem(text=statusText,userData=statusCode)
            self.statusFilterCb.setCurrentIndex(1)
        elif self.taskProjectType == appConfig.WebDrawQueryType.Review:
            self.statusFilterCb.clear()
            for statusText,statusCode in appConfig.DRAW_ZHIJIAN_STATUS_DICT.items():
                self.statusFilterCb.addItem(text=statusText,userData=statusCode)
            self.statusFilterCb.setCurrentIndex(1)
        else:
            self.statusFilterCb.clear()
            for statusText,statusCode in appConfig.DRAW_CHOUJIAN_STATUS_DICT.items():
                self.statusFilterCb.addItem(text=statusText,userData=statusCode)
            self.statusFilterCb.setCurrentIndex(1)
        self.stopStatusConnect = False

        self.refreshFishnet(1,self.pageSizeComboBox.currentData(),self.statusFilterCb.currentData())
        self.refreshFeatureTable(1,self.featurePageSizeComboBox.currentData())
        # 改变控件的状态
        self.changeEnables(True)
        self.dockWidget_leftDown.setEnabled(not self.preloadMode)

    def featureTableConnectFunc(self):
        self.featureTableWidget.itemSelectionChanged.connect(self.featureTableWidgetDoubleClicked)
        self.lastFeaturePagePb.clicked.connect(self.lastFeaturePagePbClicked)
        self.nextFeaturePagePb.clicked.connect(self.nextFeaturePagePbClicked)
        self.featurePageSizeComboBox.currentIndexChanged.connect(self.commonFeatureTableChangedFunc)
        self.featureStatusFilterCb.currentIndexChanged.connect(self.commonFeatureTableChangedFunc)
        self.featureJumpPb.clicked.connect(self.featureJumpPbClicked)
    
    def featureTableWidgetDoubleClicked(self):
        print("trigger")
        selectedItems =  self.featureTableWidget.selectedItems()
        if len(selectedItems) > 0:
            self.changeFeatureTable(self.featureTableWidget.selectedItems()[0].row(),True)

    def changeFeatureTable(self,index,setExtent=False):
        if len(self.featureIdList) > 0:
            tempExtent : QgsRectangle = self.featureExtentList[index]
            if setExtent:
                center_x = (tempExtent.xMinimum() + tempExtent.xMaximum()) / 2
                center_y = (tempExtent.yMinimum() + tempExtent.yMaximum()) / 2
                # 计算新的宽度和高度（翻倍）
                new_width = tempExtent.width() * 2
                new_height = tempExtent.height() * 2
                new_rect = QgsRectangle(center_x - new_width / 2, center_y - new_height / 2, center_x + new_width / 2, center_y + new_height / 2)
                self.featureTableWidget.selectRow(index)
                self.spMapCanvas.setExtent(new_rect)
                self.rightMapCanvas.setExtent(new_rect)
                self.drawServerLayer.triggerRepaint()

                tempId = self.featureIdList[index]
                self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
                queryCode,queryRes = self.rsdmReq.queryFeaturesByPoint(center_x,center_y,self.taskId)
                if queryCode and len(queryRes) > 0:
                    for tempDict in queryRes:
                        if tempDict['properties']['id'] == tempId:
                            tempWkt = str(tempDict['geometry']).replace('\'','\"')
                            tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.drawLayer.fields(), None)[0]
                            tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                            tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                            tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                            tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                            self.drawLayer.addFeature(tempFeature)
                            self.drawLayer.selectAll()
                            break
            else:
                self.featureTableWidget.clearSelection()
        else:
            self.featureTableWidget.clearSelection()

    def updateFeatureTable(self):
        page = self.featurePageIndexSpinBox.value()
        pageSize = self.featurePageSizeComboBox.currentData()
        selectedItems =  self.featureTableWidget.selectedItems()
        if len(selectedItems) > 0:
            row = self.featureTableWidget.selectedItems()[0].row()
        else:
            row = 0
        self.refreshFeatureTable(page,pageSize,row)

    def refreshFeatureTable(self,pageNo,pageSize,keepRow=0,setExtent=False):
        print('pageSize',pageSize)
        self.featureIdList = []
        self.featureExtentList = []

        if self.taskProjectType == appConfig.WebDrawQueryType.Draw:
            userId = self.parentWindow.userId
        else:
            userId = ""

        reqStatus,reqDict = self.rsdmReq.queryFeatureList(
            taskId=self.taskId,
            userId=userId,
            pageNo=pageNo,
            pageSize=pageSize,
            order= self.featureStatusFilterCb.currentData(),
        )
        if reqStatus:
            contents = reqDict['contents']
            total = reqDict['total']
            pageSize = reqDict['pageSize']
            currentPage = reqDict['currentPage']
            self.totalFeaturePage = reqDict['pages']
            #表外设置
            self.featureTotalLabel.setText(f"{(currentPage-1)*pageSize+1}-{currentPage*pageSize if currentPage*pageSize<total else total} 共{total}条, 共{self.totalFeaturePage}页, 当前第{currentPage}页 ")
            self.featurePageIndexSpinBox.setValue(currentPage)
            #表内设置
            self.featureTableWidget.setRowCount(0)
            self.featureTableWidget.setRowCount(pageSize)
            for index,tabelContent in enumerate(contents):
                tempGeometry = QgsGeometry.fromWkt(tabelContent['shape'])
                tempExtent = tempGeometry.boundingBox()
                self.featureIdList.append(tabelContent['id'])
                self.featureExtentList.append(tempExtent)
                self.featureTableWidget.setItem(index,0,QTableWidgetItem(tabelContent['id']))
                self.featureTableWidget.setItem(index,1,QTableWidgetItem(tabelContent['remark1']))
                self.featureTableWidget.setItem(index,2,QTableWidgetItem(tabelContent['remark2']))
                self.featureTableWidget.setItem(index,3,QTableWidgetItem(tabelContent['remark3']))
            self.changeFeatureTable(keepRow,setExtent)
        else:
            MessageBox('错误',reqDict,self).exec_()
    
    def lastFeaturePagePbClicked(self):
        currentPage = self.featurePageIndexSpinBox.value() - 1
        if currentPage < 1:
            currentPage = 1
        currentPageSize = self.featurePageSizeComboBox.currentData()
        self.refreshFeatureTable(currentPage,currentPageSize,setExtent=True)
    
    def nextFeaturePagePbClicked(self):
        currentPage = self.featurePageIndexSpinBox.value() + 1
        if currentPage > self.totalFeaturePage:
            currentPage = self.totalFeaturePage
        currentPageSize = self.featurePageSizeComboBox.currentData()
        self.refreshFeatureTable(currentPage,currentPageSize,setExtent=True)
        self.featureTableWidget.setFocus()
        
    def featureJumpPbClicked(self):
        currentPage = self.featurePageIndexSpinBox.value()
        if currentPage < 1:
            currentPage = 1
        elif currentPage > self.totalFeaturePage:
            currentPage = self.totalFeaturePage
        currentPageSize = self.featurePageSizeComboBox.currentData()
        self.refreshFeatureTable(currentPage,currentPageSize,setExtent=True)
        self.featureTableWidget.setFocus()
    
    def commonFeatureTableChangedFunc(self):
        currentPage = 1
        currentPageSize = self.featurePageSizeComboBox.currentData()
        self.refreshFeatureTable(currentPage,currentPageSize,setExtent=True)

    def fishnetConnectFunc(self):
        self.TableWidget.clicked.connect(self.TableWidgetClicked)
        self.lastPagePb.clicked.connect(self.lastPagePbClicked)
        self.nextPagePb.clicked.connect(self.nextPagePbClicked)
        self.pageSizeComboBox.currentIndexChanged.connect(self.commonChangedFunc)
        self.statusFilterCb.currentIndexChanged.connect(self.commonChangedFunc)
        self.jumpPb.clicked.connect(self.pageIndexSpinBoxChanged)

        self.lastPb.clicked.connect(self.lastPbClicked)
        self.nextPb.clicked.connect(self.nextPbClicked)
        self.rejectPB.clicked.connect(self.rejectPBClicked)
    
    def TableWidgetClicked(self):
        selectedItems =  self.TableWidget.selectedItems()
        if len(selectedItems) > 0:
            self.changeMapTif(self.TableWidget.selectedItems()[0].row())

    def changeMapTif(self,index):
        if len(self.fishnetIdList) > 0:
            if index >= len(self.fishnetIdList):
                currentPage = self.pageIndexSpinBox.value()
                if currentPage == self.totalPage:
                    MessageBox('提示','您已经是最后一个任务了',self).exec_()
                    self.TableWidget.clearSelection()
                    return
                currentPageSize = self.pageSizeComboBox.currentData()
                currentStatus = self.statusFilterCb.currentData()
                self.refreshFishnet(currentPage+1,currentPageSize,currentStatus)
            else:
                print("当前格网ID：",self.fishnetIdList[index])
                if self.preloadMode:
                    # 如果是专业模式 
                    # 第一步 获取当前渔网id，并获取当前渔网id内的所有要素，
                    # 将要素的featureId 存到一个list，以留存 在提交后，判断哪些要素有变化、新增
                    # 将self.drawLayer 要素存到 self.drawLayer 中
                    xmin,ymin,xmax,ymax = self.fishnetExtentList[index].xMinimum(),self.fishnetExtentList[index].yMinimum(),self.fishnetExtentList[index].xMaximum(),self.fishnetExtentList[index].yMaximum()
                    querySuccess,queryRes = self.rsdmReq.queryFeaturesByExtent(xmin,ymin,xmax,ymax,self.taskId)
                    if querySuccess:
                        self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
                        self.drawLayer.commitChanges(False)
                        self.preloadQueryIdList = []
                        tempFeatureList = []
                        for tempDict in queryRes:
                            tempWkt = str(tempDict['geometry']).replace('\'','\"')
                            tempFeature = QgsJsonUtils.stringToFeatureList(tempWkt, self.drawLayer.fields(), None)[0]
                            tempFeature.setAttribute('FeatureId',tempDict['properties']['id'])
                            tempFeature.setAttribute('remark1',tempDict['properties']['remark1'])
                            tempFeature.setAttribute('remark2',tempDict['properties']['remark2'])
                            tempFeature.setAttribute('remark3',tempDict['properties']['remark3'])
                            tempFeature.setAttributes([tempDict['properties']['id'],tempDict['properties']['remark1'],tempDict['properties']['remark2'],tempDict['properties']['remark3'],0])
                            self.preloadQueryIdList.append(tempDict['properties']['id'])
                            tempFeatureList.append(tempFeature)
                        self.drawLayer.addFeatures(tempFeatureList)
                    else:
                        pass
                else:
                    self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
                    
                tempExtent = self.fishnetExtentList[index]
                self.spMapCanvas.setExtent(tempExtent)
                self.rightMapCanvas.setExtent(tempExtent)
                self.drawServerLayer.triggerRepaint()
                self.spMapCanvas.refresh()
                self.rightMapCanvas.refresh()
                self.TableWidget.selectRow(index)
                # 显示驳回原因
                self.errorReasonLabel.setText(self.rejectReasonList[index])
                self.randomRejectReasonLabel.setText(self.randomRejectReasonList[index])

                if self.infoBar:
                    try:
                        self.infoBar.close()
                        self.infoBar.deleteLater()
                        self.infoBar = None
                    except Exception as e:
                        pass
                if self.rejectReasonList[index] != ""  and self.taskProjectType == appConfig.WebDrawQueryType.Draw:
                    self.infoBar = InfoBar.warning(
                        title=f"质检驳回原因",
                        content=self.rejectReasonList[index],
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.BOTTOM,
                        duration=-1,
                        parent=self
                    )
                elif self.randomRejectReasonList[index] != "" and self.taskProjectType == appConfig.WebDrawQueryType.Review:
                    self.infoBar = InfoBar.warning(
                        title=f"抽检驳回原因",
                        content=self.randomRejectReasonList[index],
                        orient=Qt.Horizontal,
                        position=InfoBarPosition.BOTTOM,
                        duration=-1,
                        parent=self
                    )
        else:
            self.TableWidget.clearSelection()
    
    def refreshFishnet(self,pageNo,pageSize,status=None,jumpFinalRow=False,keepRow=0,preId=None,changeMap=True):
        self.fishnetIdList = []
        self.fishnetExtentList : list[QgsRectangle] = []
        self.rejectReasonList = []
        self.randomRejectReasonList = []
        reqStatus,reqDict = self.rsdmReq.queryDesktopProduceFishnetList(
            taskId=self.taskId,
            userId=self.parentWindow.userId,
            pageNo=pageNo,
            pageSize=pageSize,
            status=status,
            queryType=self.taskProjectType
        )
        if reqStatus:
            contents = reqDict['contents']
            total = reqDict['total']
            pageSize = reqDict['pageSize']
            currentPage = reqDict['currentPage']
            self.totalPage = reqDict['pages']

            #表外设置
            self.fishnetsTotalLabel.setText(f"{(currentPage-1)*pageSize+1}-{currentPage*pageSize if currentPage*pageSize<total else total} 共{total}条, 共{self.totalPage}页, 当前第{currentPage}页 ")
            self.pageIndexSpinBox.setValue(currentPage)

            #表内设置
            self.TableWidget.setRowCount(0)
            self.TableWidget.setRowCount(pageSize)
            for index,tabelContent in enumerate(contents):
                tempGeometry = QgsGeometry.fromWkt(tabelContent['shape'])
                tempExtent = tempGeometry.boundingBox()#.buffered(0.0005)
                self.fishnetIdList.append(tabelContent['id'])
                self.fishnetExtentList.append(tempExtent)
                self.rejectReasonList.append(tabelContent['reassignReason'] if tabelContent['reassignReason'] else "")
                self.randomRejectReasonList.append(tabelContent['randomReassignReason'] if tabelContent['randomReassignReason'] else "")
                self.TableWidget.setItem(index,0,QTableWidgetItem(str(tabelContent['sorter'])))
                self.TableWidget.setItem(index,1,QTableWidgetItem(tabelContent['status_dictText']))
                self.TableWidget.setItem(index,2,QTableWidgetItem(tabelContent['repairRealName']))
            
            if changeMap:
                if jumpFinalRow:
                    self.changeMapTif(len(contents)-1)
                else:
                    if preId:
                        currentId = self.fishnetIdList[keepRow]
                        if currentId != preId:
                            self.changeMapTif(keepRow)
                        else:
                            self.changeMapTif(keepRow+1)
                    else:
                        self.changeMapTif(keepRow)
        else:
            MessageBox('错误',reqDict,self).exec_()
    
    def lastPagePbClicked(self):
        currentPage = self.pageIndexSpinBox.value() - 1
        if currentPage < 1:
            currentPage = 1
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        self.refreshFishnet(currentPage,currentPageSize,currentStatus)
    
    def nextPagePbClicked(self):
        currentPage = self.pageIndexSpinBox.value() + 1
        if currentPage > self.totalPage:
            currentPage = self.totalPage
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        self.refreshFishnet(currentPage,currentPageSize,currentStatus)
    
    def pageIndexSpinBoxChanged(self):
        currentPage = self.pageIndexSpinBox.value()
        if currentPage < 1:
            currentPage = 1
        elif currentPage > self.totalPage:
            currentPage = self.totalPage
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        self.refreshFishnet(currentPage,currentPageSize,currentStatus)
    
    def commonChangedFunc(self):
        if not self.stopStatusConnect:
            currentPage = 1
            currentPageSize = self.pageSizeComboBox.currentData()
            currentStatus = self.statusFilterCb.currentData()
            self.refreshFishnet(currentPage,currentPageSize,currentStatus)
    
    def lastPbClicked(self):
        selectedItems =  self.TableWidget.selectedItems()
        if len(selectedItems) > 0 and len(self.fishnetIdList) >0:
            currentRow = self.TableWidget.selectedItems()[0].row()
            if currentRow == 0: #需要翻到上一页的最后
                currentPage = self.pageIndexSpinBox.value()
                currentPageSize = self.pageSizeComboBox.currentData()
                currentStatus = self.statusFilterCb.currentData()
                if currentPage <= 1: #第一页没法翻了
                    MessageBox('提示', "当前为第一个任务", self).exec_()
                else:
                    self.refreshFishnet(currentPage-1,currentPageSize,currentStatus,jumpFinalRow=True)
            else:
                self.changeMapTif(currentRow-1)
        else:
            MessageBox('提示', "当前状态没有任务", self).exec_()
    
    def nextPbClicked(self):
        selectedItems =  self.TableWidget.selectedItems()
        currentPage = self.pageIndexSpinBox.value()
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        if len(selectedItems) > 0 and len(self.fishnetIdList) >0:
            currentRow = self.TableWidget.selectedItems()[0].row()
            currentId = self.fishnetIdList[currentRow]
            # todo: 在进行下一个网格作业前 若是专业模式，则需要先将当前的矢量进行上传
            # 下一个 api
            self.rsdmReq.nextGrid(currentId,self.taskProjectType)
            
            self.refreshFishnet(currentPage,currentPageSize,currentStatus,keepRow=currentRow,preId=currentId)
        else:
            print("len(selectedItems)",len(selectedItems),"len(self.fishnetIdList)",len(self.fishnetIdList))
            MessageBox('提示', "当前状态没有任务", self).exec_()

    # 当用户通过选择格网手段更新格网状态后，进行一次格网状态的更新
    def refreshCurrentRow(self):
        currentPage = self.pageIndexSpinBox.value()
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        self.refreshFishnet(currentPage,currentPageSize,currentStatus,keepRow=1,changeMap=False)
        self.TableWidget.selectRow(1)
        self.fishnetServerLayer.triggerRepaint()
        self.spMapCanvas.refresh()
        self.rightMapCanvas.refresh()
        if self.infoBar:
            try:
                self.infoBar.close()
                self.infoBar.deleteLater()
                self.infoBar = None
            except Exception as e:
                pass
        self.infoBar = InfoBar.success(
            title="消息",
            content="状态刷新成功",
            orient=Qt.Horizontal,
            position=InfoBarPosition.BOTTOM,
            duration=2000,
            parent=self
        )
    
    def rejectPBClicked(self):
        selectedItems =  self.TableWidget.selectedItems()
        currentPage = self.pageIndexSpinBox.value()
        currentPageSize = self.pageSizeComboBox.currentData()
        currentStatus = self.statusFilterCb.currentData()
        if len(selectedItems) > 0 and len(self.fishnetIdList) >0:
            if self.taskProjectType in [appConfig.WebDrawQueryType.Review,appConfig.WebDrawQueryType.Random]:
                if self.taskProjectType == appConfig.WebDrawQueryType.Review:
                    preReason = self.randomRejectReasonLabel.text()
                else:
                    preReason = ""
                dialog = WebSelectRejectReasonDialogClass(defaultReason=preReason,parent=self)
                dialog.exec()
                if dialog.rejectString:
                    currentRow = self.TableWidget.selectedItems()[0].row()
                    currentId = self.fishnetIdList[currentRow]
                    self.rsdmReq.reject(currentId,dialog.rejectString, self.taskProjectType)
                    self.refreshFishnet(currentPage,currentPageSize,currentStatus,keepRow=currentRow,preId=currentId)
                dialog.deleteLater()
            else:
                MessageBox('提示', "当前状态不可以进行驳回", self).exec_()
        else:
            MessageBox('提示', "当前状态没有任务", self).exec_()
                

    def projectConnectFunc(self):
        self.openProjectPb.clicked.connect(self.openProjectPbClicked)
        self.closeProjectPb.clicked.connect(self.closeProjectPbClicked)

    def openProjectPbClicked(self):
        if self.taskId:
            MessageBox('提示', "当前已打开项目，请先关闭项目", self).exec_()
            return
        typeSelectDialog = WebSelectProjectTypeDialogClass(self)
        typeSelectDialog.exec()

        queryType = typeSelectDialog.resType

        if queryType:
            dialog = WebSampleProjectListDialogClass(self.parentWindow.userId,queryType,self)
            dialog.exec()
            if dialog.resTaskName and dialog.resTaskId:
                self.layerTree.clearTreeView()
                
                self.tifLayer = None
                self.tifIILayer = None
                self.drawLayer = None
                self.extraLayerDict = {}

                self.taskName = dialog.resTaskName
                self.taskId = dialog.resTaskId
                self.taskTypeId = dialog.resTaskTypeId
                self.taskProjectType = queryType
                querySuccess,resImgList = self.rsdmReq.queryDesktopProduceImageList(self.taskId)
                query2Success,resRemarkContent = self.rsdmReq.queryRemarkType(self.taskTypeId)
                print("userId:",self.parentWindow.userId)
                print("taskId:",self.taskId)
                print("taskTypeId:",self.taskTypeId)
                print("imgList:",resImgList)

                if querySuccess and query2Success:
                    print(resImgList)
                    self.tifPathII = resImgList['current_image'][0]['imageUrl']
                    self.tifNameII = resImgList['current_image'][0]['imageName']

                    try:
                        self.tifPath = resImgList['before_image'][0]['imageUrl']
                        self.tifName = resImgList['before_image'][0]['imageName']
                    except Exception as e:
                        self.tifPath = self.tifPathII
                        self.tifName = self.tifNameII

                    self.extraLayerDict = {}
                    for extraLayerInfo in resImgList['assist_image']:
                        self.extraLayerDict[extraLayerInfo['imageName']] = extraLayerInfo['imageUrl']

                    remark1TypeString = resRemarkContent['remark1Type']
                    self.remark1String = resRemarkContent['remark1Name']
                    if remark1TypeString == appConfig.AttrType.String.value:
                        self.remark1Type = appConfig.AttrType.String
                        self.remark1List = []
                    elif remark1TypeString == appConfig.AttrType.List.value:
                        self.remark1Type = appConfig.AttrType.List
                        self.remark1List = resRemarkContent['remark1Classes'].split(',')
                    elif remark1TypeString == appConfig.AttrType.Int.value:
                        self.remark1Type = appConfig.AttrType.Int
                        self.remark1List = []
                    
                    remark2TypeString = resRemarkContent['remark2Type']
                    if remark2TypeString != "":
                        self.remark2String = resRemarkContent['remark2Name']
                        if remark2TypeString == appConfig.AttrType.String.value:
                            self.remark2Type = appConfig.AttrType.String
                            self.remark2List = []
                        elif remark2TypeString == appConfig.AttrType.List.value:
                            self.remark2Type = appConfig.AttrType.List
                            self.remark2List = resRemarkContent['remark2Classes'].split(',')
                        elif remark2TypeString == appConfig.AttrType.Int.value:
                            self.remark2Type = appConfig.AttrType.Int
                            self.remark2List = []
                    else:
                        self.remark2String = None
                        self.remark2Type = None
                        self.remark2List = None
                    
                    remark3TypeString = resRemarkContent['remark3Type']
                    if remark3TypeString != "":
                        self.remark3String = resRemarkContent['remark3Name']
                        if remark3TypeString == appConfig.AttrType.String.value:
                            self.remark3Type = appConfig.AttrType.String
                            self.remark3List = []
                        elif remark3TypeString == appConfig.AttrType.List.value:
                            self.remark3Type = appConfig.AttrType.List
                            self.remark3List = resRemarkContent['remark3Classes'].split(',')
                        elif remark3TypeString == appConfig.AttrType.Int.value:
                            self.remark3Type = appConfig.AttrType.Int
                            self.remark3List = []
                    else:
                        self.remark3String = None
                        self.remark3Type = None
                        self.remark3List = None

                    self.initMember()
                    MessageBox('提示', "项目打开完成", self).exec_()
            dialog.deleteLater()
        typeSelectDialog.deleteLater()

    def closeProjectPbClicked(self):
        if self.taskId:
            w = MessageBox(
                '关闭项目',
                '确认要关闭项目吗？',
                self
            )
            w.yesButton.setText('确认关闭')
            w.cancelButton.setText('取消')
        
            if w.exec():
                # 项目名
                self.projectLabel.setText('???')
                self.errorReasonLabel.setText('???')
                # 初始化右侧的格网表
                self.TableWidget.clear()
                self.featureTableWidget.clear()

                self.unsetMemberUI()
                self.spMapCanvas.hide()
                self.rightMapCanvas.hide()
                self.changeEnables(False)
                self.emptyLabel.show()
                self.emptyLabel_right.show()

    def updateMapcanvasLayers(self):
        self.spMapCanvas.refresh()
        self.rightMapCanvas.refresh()

    def topBarConnectFunc(self):
        self.addRasterLayer.clicked.connect(self.addRasterLayerClicked)
        self.addVectorLayer.clicked.connect(self.addVectorLayerClicked)
        self.addXYZTilesLayer.clicked.connect(self.addXYZTilesLayerClicked)

        self.leftChangePb1.clicked.connect(self.leftChangePb1Clicked)
        self.leftChangePb2.clicked.connect(self.leftChangePb2Clicked)
        self.rightChangePb3.clicked.connect(self.rightChangePb3Clicked)
        self.rightChangePb4.clicked.connect(self.rightChangePb4Clicked)

        self.leftBottomInfoPb.clicked.connect(self.leftBottomInfoPbClicked)
        self.rightBottomInfoPb.clicked.connect(self.rightBottomInfoPbClicked)

        self.commitMagicPB.clicked.connect(self.commitMagicPBClicked)
        self.addBookmarkPb.clicked.connect(self.addBookmarkPbClicked)
        self.deleteBookmarkPb.clicked.connect(self.deleteBookmarkPbClicked)

        self.selectFishnetMapToolPb.clicked.connect(self.selectFishnetMapToolPbClicked)

    def addRasterLayerClicked(self):
        file, ext = QFileDialog.getOpenFileName(self, '选择栅格影像', "", 'GeoTiff(*.tif;*tiff;*TIF;*TIFF)')
        if file:
            self.layerTree.addExtraItemByFile(file)
    
    def addVectorLayerClicked(self):
        file, ext = QFileDialog.getOpenFileName(self, '选择矢量文件', "", 'ShapeFile(*.shp;*.SHP)')
        if file:
            self.layerTree.addExtraItemByFile(file)
    
    def addXYZTilesLayerClicked(self):
        dialog = OpenXYZTilesDialogClass(yoyiTrans(),self)
        dialog.exec()
        if dialog.layerName and dialog.wmsPath:
            self.layerTree.addExtraItemByUrl(dialog.wmsPath,dialog.layerName,isLocalType=True)
        dialog.deleteLater()
    
    def leftChangePb1Clicked(self):
        if self.leftChangePb1.isChecked():
            if self.layerTree.leftKey1 and self.layerTree.leftKey1 not in self.layerTree.layerTypeDict.keys():
                MessageBox('信息', "未搜寻到绑定的图层", self).exec_()
                self.leftChangePb1.setChecked(False)
                return
            self.layerTree.leftActiveKey = 1
            self.leftChangePb2.setChecked(False)
            self.layerTree.refreshLayers()
        else:
            self.layerTree.leftActiveKey = None
            self.layerTree.refreshLayers()

    def leftChangePb2Clicked(self):
        if self.leftChangePb2.isChecked():
            if self.layerTree.leftKey2 and self.layerTree.leftKey2 not in self.layerTree.layerTypeDict.keys():
                MessageBox('信息', "未搜寻到绑定的图层", self).exec_()
                self.leftChangePb2.setChecked(False)
                return
            self.layerTree.leftActiveKey = 2
            self.leftChangePb1.setChecked(False)
            self.layerTree.refreshLayers()
        else:
            self.layerTree.leftActiveKey = None
            self.layerTree.refreshLayers()

    def rightChangePb3Clicked(self):
        if self.rightChangePb3.isChecked():
            if self.layerTree.rightKey3 and self.layerTree.rightKey3 not in self.layerTree.layerTypeDict.keys():
                MessageBox('信息', "未搜寻到绑定的图层", self).exec_()
                self.rightChangePb3.setChecked(False)
                return
            self.layerTree.rightActiveKey = 3
            self.rightChangePb4.setChecked(False)
            self.layerTree.refreshLayers()
        else:
            self.layerTree.rightActiveKey= None
            self.layerTree.refreshLayers()

    def rightChangePb4Clicked(self):
        if self.rightChangePb4.isChecked():
            if self.layerTree.rightKey4 and self.layerTree.rightKey4 not in self.layerTree.layerTypeDict.keys():
                MessageBox('信息', "未搜寻到绑定的图层", self).exec_()
                self.rightChangePb4.setChecked(False)
                return
            self.layerTree.rightActiveKey = 4
            self.rightChangePb3.setChecked(False)
            self.layerTree.refreshLayers()
        else:
            self.layerTree.rightActiveKey= None
            self.layerTree.refreshLayers()
    
    def leftBottomInfoPbClicked(self):
        if self.taskId:
            self.layerTree.openLayerProp(self.layerTree.bottomLayer)

    def rightBottomInfoPbClicked(self):
        if self.taskId:
            self.layerTree.openLayerProp(self.layerTree.extraBottomLayer)
    
    def refreshBookMark(self):
        self.addBookmarkMenu = RoundMenu(parent=self)
        self.deleteBookmarkMenu = RoundMenu(parent=self)
        for key in self.bookMarkDict.keys():
            action = Action(text=key,parent=self)
            actionD = Action(text=key,parent=self)
            self.addBookmarkMenu.addAction(action)
            self.deleteBookmarkMenu.addAction(actionD)
        self.addBookmarkMenu.triggered.connect(self.addBookmarkMenuTriggered)
        self.addBookmarkPb.setFlyout(self.addBookmarkMenu)

        self.deleteBookmarkMenu.triggered.connect(self.deleteBookmarkMenuTriggered)
        self.deleteBookmarkPb.setFlyout(self.deleteBookmarkMenu)

    def commitMagicPBClicked(self):
        if self.spMapCanvas.mapTool():
            if type(self.spMapCanvas.mapTool()) == WebSegAnyMapTool:
                self.magicMapTool.commitMagicTempPolygon()
                self.magicMapToolRight.commitMagicTempPolygon()
    
    def addBookmarkPbClicked(self):
        extent = self.rightMapCanvas.extent()
        dialog = WebInpuBookmarkNameDialogClass("",self)
        dialog.exec()
        if dialog.bookmarkName:
            bookMarkKey = f"@({self.bookMarkIndex}):{dialog.bookmarkName}"
            self.bookMarkDict[bookMarkKey] = extent
            self.bookMarkIndex += 1
            self.refreshBookMark()
        dialog.deleteLater()
    def deleteBookmarkPbClicked(self):
        reply = MessageBox("警告","确定要删除所有书签吗？",self)
        reply.yesButton.setText("删除所有")
        reply.cancelButton.setText("取消")
        if reply.exec():
            self.bookMarkDict = {}
            self.bookMarkIndex = 1
            self.refreshBookMark()

    def addBookmarkMenuTriggered(self,action):
        extent = self.bookMarkDict[action.text()]
        self.spMapCanvas.setExtent(extent)
        self.rightMapCanvas.setExtent(extent)
        self.spMapCanvas.refresh()
        self.rightMapCanvas.refresh()
    
    def deleteBookmarkMenuTriggered(self,action):
        key = action.text()
        self.bookMarkDict.pop(key)
        self.refreshBookMark()
    
    def selectFishnetMapToolPbClicked(self):
        if self.selectFishnetMapToolPb.isChecked():
            self.selectFishnetMapTool = SelectFishnetMapTool(self.spMapCanvas,
                                                             self.taskId,
                                                             self.taskProjectType,
                                                             self.parentWindow.userId,
                                                             self,
                                                             self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.selectFishnetMapTool)

            self.selectFishnetMapToolRight = SelectFishnetMapTool(self.rightMapCanvas,
                                                                  self.taskId,
                                                                  self.taskProjectType,
                                                                  self.parentWindow.userId,
                                                                  self,
                                                                  self.spMapCanvas
                                                                  )
            self.rightMapCanvas.setMapTool(self.selectFishnetMapToolRight)

            self.selectFishnetMapTool.deactivated.connect(lambda: self.selectFishnetMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
        



    def mapToolConnectFunc(self):

        self.panMapToolPb.clicked.connect(self.panMapToolTriggered)
        self.magicMapToolPb.clicked.connect(self.magicMapToolPbTriggered)
        self.polygonMapToolPb.clicked.connect(self.polygonMapToolPbTriggered)
        self.rectangleMapToolPb.clicked.connect(self.rectangleMapToolPbTriggered)
        self.circleMapToolPb.clicked.connect(self.circleMapToolPbTriggered)
        self.pointMapToolPb.clicked.connect(self.pointMapToolPbTriggered)
        # 特殊
        self.rejectPointMapToolPb.clicked.connect(self.rejectPointMapToolPbTriggered)

        self.selectMapToolPb.clicked.connect(self.selectMapToolTriggered)
        self.rotateMapToolPb.clicked.connect(self.rotateMapToolPbTriggered)
        self.rescaleMapToolPb.clicked.connect(self.rescaleMapToolPbTriggered)
        #self.identifyMapToolPb.clicked.connect(self.identifyMapToolPbTriggered)
        self.line2PolyMapToolPb.clicked.connect(self.line2PolyMapToolPbTriggered)

        self.splitMapToolPb.clicked.connect(self.splitMapToolPbTriggered)
        self.vertexMapToolPb.clicked.connect(self.vertexMapToolPbTriggered)
        self.reshapeMapToolPb.clicked.connect(self.reshapeMapToolPbTriggered)
        self.pasteMapToolPb.clicked.connect(self.pasteMapToolPbTriggered)
        self.lineBuffer2PolyPb.clicked.connect(self.lineBuffer2PolyPbTriggered)

        self.deleteFeaturePb.clicked.connect(self.deleteFeaturePbTriggered)
        self.changeAttrPb.clicked.connect(self.changeAttrPbTriggered)
        self.mergeMapToolPb.clicked.connect(self.mergeMapToolTriggered)

        
    
    # 地图工具
    def panMapToolTriggered(self):
        if self.panMapToolPb.isChecked():
            self.panMapTool = DoublePanTool(self.spMapCanvas,self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.panMapTool)
            self.panMapToolRight = DoublePanTool(self.rightMapCanvas, self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.panMapToolRight)

            self.panMapTool.deactivated.connect(lambda: self.panMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == DoublePanTool:
                    self.panMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def magicMapToolPbTriggered(self):
        if self.magicMapToolPb.isChecked():
            self.magicMapTool = WebSegAnyMapTool(self.spMapCanvas,
                                                self.samInfer,
                                                self.drawLayer,
                                                self,
                                                self.taskId,
                                                self.parentWindow.userId,
                                                self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.magicMapTool)
            self.magicMapToolRight = WebSegAnyMapTool(self.rightMapCanvas,
                                                self.samInfer,
                                                self.drawLayer,
                                                self,
                                                self.taskId,
                                                self.parentWindow.userId,
                                                self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.magicMapToolRight)
            self.magicMapTool.deactivated.connect(lambda: self.magicMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == WebSegAnyMapTool:
                    self.magicMapTool.reset()
                    self.magicMapToolRight.reset()
                    self.magicMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def polygonMapToolPbTriggered(self):
        if self.polygonMapToolPb.isChecked():
            self.polygonMapTool = PolygonMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.polygonMapTool)
            self.polygonMapToolRight = PolygonMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.polygonMapToolRight)
            self.polygonMapTool.deactivated.connect(lambda: self.polygonMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == PolygonMapTool_Web:
                    self.polygonMapTool.reset()
                    self.polygonMapToolRight.reset()
                    self.polygonMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def rectangleMapToolPbTriggered(self):
        if self.rectangleMapToolPb.isChecked():
            self.rectangleMapTool = RectangleMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.rectangleMapTool)
            self.rectangleMapToolRight = RectangleMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.rectangleMapToolRight)
            self.rectangleMapTool.deactivated.connect(lambda: self.rectangleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RectangleMapTool_Web:
                    self.rectangleMapTool.reset()
                    self.rectangleMapToolRight.reset()
                    self.rectangleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def circleMapToolPbTriggered(self):
        if self.circleMapToolPb.isChecked():
            self.circleMapTool = CircleMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.circleMapTool)
            self.circleMapToolRight = CircleMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.circleMapToolRight)
            self.circleMapTool.deactivated.connect(lambda: self.circleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == CircleMapTool_Web:
                    self.circleMapTool.reset()
                    self.circleMapToolRight.reset()
                    self.circleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def pointMapToolPbTriggered(self):
        if self.pointMapToolPb.isChecked():
            self.pointMapTool = PointMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.pointMapTool)
            self.pointMapToolRight = PointMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.pointMapToolRight)
            self.pointMapTool.deactivated.connect(lambda: self.pointMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == PointMapTool_Web:
                    self.pointMapTool.reset()
                    self.pointMapToolRight.reset()
                    self.pointMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def rejectPointMapToolPbTriggered(self):
        if self.rejectPointMapToolPb.isChecked():
            self.rejectPointMapTool = RejectPointMapTool_Web(self.spMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.taskProjectType,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.rejectPointMapTool)
            self.rejectPointMapToolRight = RejectPointMapTool_Web(self.rightMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.taskProjectType,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.rejectPointMapToolRight)
            self.rejectPointMapTool.deactivated.connect(lambda: self.rejectPointMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RejectPointMapTool_Web:
                    self.rejectPointMapTool.reset()
                    self.rejectPointMapToolRight.reset()
                    self.rejectPointMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def selectMapToolTriggered(self):
        if self.selectMapToolPb.isChecked():
            self.selectMapTool = SelectFeatureMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.selectMapTool)
            self.selectMapToolRight = SelectFeatureMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.selectMapToolRight)
            self.selectMapTool.deactivated.connect(lambda: self.selectMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == SelectFeatureMapTool_Web:
                    self.selectMapTool.reset()
                    self.selectMapToolRight.reset()
                    self.selectMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    # 外部导入矢量的选择工具
    def selectLocalVectorMapToolClicked(self,layer):
        if self.spMapCanvas.mapTool():
            self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
            self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
        self.localVectorSelectMapTool = RecTangleSelectFeatureMapTool(self.spMapCanvas,layer,self,
                                                                      otherCanvas=self.rightMapCanvas,allowCopy=True)
        self.spMapCanvas.setMapTool(self.localVectorSelectMapTool)

        self.localVectorSelectMapToolRight = RecTangleSelectFeatureMapTool(self.rightMapCanvas,layer,self,
                                                                      otherCanvas=self.spMapCanvas,allowCopy=True)
        self.rightMapCanvas.setMapTool(self.localVectorSelectMapToolRight)
        
    def rotateMapToolPbTriggered(self):
        if self.rotateMapToolPb.isChecked():
            self.rotateMapTool = RotatePolygonMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.rotateMapTool)
            self.rotateMapToolRight = RotatePolygonMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.rotateMapToolRight)
            self.rotateMapTool.deactivated.connect(lambda: self.rotateMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RotatePolygonMapTool_Web:
                    self.rotateMapTool.reset()
                    self.rotateMapToolRight.reset()
                    self.rotateMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def rescaleMapToolPbTriggered(self):
        if self.rescaleMapToolPb.isChecked():
            self.rescaleMapTool = RescalePolygonMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.rescaleMapTool)
            self.rescaleMapToolRight = RescalePolygonMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.rescaleMapToolRight)
            self.rescaleMapTool.deactivated.connect(lambda: self.rescaleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == RescalePolygonMapTool_Web:
                    self.rescaleMapTool.reset()
                    self.rescaleMapToolRight.reset()
                    self.rescaleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())

    def identifyMapToolPbTriggered(self):
        if self.identifyMapToolPb.isChecked():
            self.setIdentifyMapTool()
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == QgsMapToolIdentifyFeature or type(self.spMapCanvas.mapTool()) == IdentifyRasterMapTool:
                    self.setIdentifyMapTool(reset=True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def setIdentifyMapTool(self,reset=False):
        if len(self.layerTree.layerTreeView.selectedLayers()) == 1:
            layerName = self.layerTree.layerTreeView.currentLayer().name()
            tempItem = self.layerTree.layerTypeDict[layerName]
            if tempItem == Local_Type:
                if reset:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
                tempLayer: QgsMapLayer = self.layerTree.layerTreeView.currentLayer()
                if tempLayer.type() == QgsMapLayerType.VectorLayer:
                    self.identifyMapTool = QgsMapToolIdentifyFeature(self.spMapCanvas)
                    self.identifyMapTool.setCursor(Qt.CursorShape.WhatsThisCursor)
                    self.identifyMapTool.featureIdentified.connect(self.showFeaturesByShp)
                    self.identifyMapTool.setLayer(tempLayer)
                    self.spMapCanvas.setMapTool(self.identifyMapTool)

                    self.identifyMapToolRight = QgsMapToolIdentifyFeature(self.rightMapCanvas)
                    self.identifyMapToolRight.setCursor(Qt.CursorShape.WhatsThisCursor)
                    self.identifyMapToolRight.featureIdentified.connect(self.showFeaturesByShp)
                    self.identifyMapToolRight.setLayer(tempLayer)
                    self.rightMapCanvas.setMapTool(self.identifyMapToolRight)

                elif tempLayer.type() == QgsMapLayerType.RasterLayer:
                    self.identifyMapTool = IdentifyRasterMapTool(self.spMapCanvas,tempLayer,self)
                    self.identifyMapTool.setCursor(Qt.CursorShape.WhatsThisCursor)
                    self.spMapCanvas.setMapTool(self.identifyMapTool)

                    self.identifyMapToolRight = IdentifyRasterMapTool(self.rightMapCanvas,tempLayer,self)
                    self.identifyMapToolRight.setCursor(Qt.CursorShape.WhatsThisCursor)
                    self.rightMapCanvas.setMapTool(self.identifyMapToolRight)
                if reset:
                    self.identifyMapToolPb.setChecked(True)
            else:
                MessageBox('信息', "只有本地文件可以进行识别", self).exec_()
                self.identifyMapToolPb.setChecked(False)
        else:
            MessageBox('信息', "选中的图层数量必须为1", self).exec_()
            self.identifyMapToolPb.setChecked(False)
        

    def showFeaturesByShp(self,feature:QgsFeature):
        infoStr = ""
        index = 0
        for field,attr in zip(feature.fields(),feature.attributes()):
            infoStr += f"{field.name()}: {attr} _____________ "
            index += 1
            if index == 3:
                infoStr += "\n"
                index = 0
        MessageBox('识别信息', infoStr, self).exec_()

    def showFeatureByTif(self,bandInfo:dict,x,y):
        MessageBox('识别信息', f"{str(bandInfo)}", self).exec_()

    def line2PolyMapToolPbTriggered(self):
        if self.line2PolyMapToolPb.isChecked():
            self.line2PolyMapTool = Line2PolygonMapTool_Web(self.spMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.line2PolyMapTool)
            self.line2PolyMapToolRight = Line2PolygonMapTool_Web(self.rightMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.line2PolyMapToolRight)
            self.line2PolyMapTool.deactivated.connect(lambda: self.line2PolyMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == Line2PolygonMapTool_Web:
                    self.line2PolyMapTool.reset()
                    self.line2PolyMapToolRight.reset()
                    self.line2PolyMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def lineBuffer2PolyPbTriggered(self):
        if self.lineBuffer2PolyPb.isChecked():
            self.lineBuffer2PolyMapTool = LineBuffer2PolygonMapTool_Web(self.spMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.lineBuffer2PolyMapTool)
            self.lineBuffer2PolyMapToolRight = LineBuffer2PolygonMapTool_Web(self.rightMapCanvas,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.lineBuffer2PolyMapToolRight)
            self.lineBuffer2PolyMapTool.deactivated.connect(lambda: self.lineBuffer2PolyPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == LineBuffer2PolygonMapTool_Web:
                    self.lineBuffer2PolyMapTool.reset()
                    self.lineBuffer2PolyMapToolRight.reset()
                    self.lineBuffer2PolyPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def splitMapToolPbTriggered(self):
        if self.splitMapToolPb.isChecked():
            self.splitMapTool = SplitPolygonMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.splitMapTool)
            self.splitMapToolRight = SplitPolygonMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.splitMapToolRight)
            self.splitMapTool.deactivated.connect(lambda: self.splitMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == SplitPolygonMapTool_Web:
                    self.splitMapTool.reset()
                    self.splitMapToolRight.reset()
                    self.splitMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def vertexMapToolPbTriggered(self):
        if self.vertexMapToolPb.isChecked():
            self.vertexMapTool = EditVertexMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.vertexMapTool)
            self.vertexMapToolRight = EditVertexMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.vertexMapToolRight)
            self.vertexMapTool.deactivated.connect(lambda: self.vertexMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == EditVertexMapTool_Web:
                    self.vertexMapTool.reset()
                    self.vertexMapToolRight.reset()
                    self.vertexMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())

    def reshapeMapToolPbTriggered(self):
        if self.reshapeMapToolPb.isChecked():
            self.reshapeMapTool = ReShapePolygonMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.reshapeMapTool)
            self.reshapeMapToolRight = ReShapePolygonMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.reshapeMapToolRight)
            self.reshapeMapTool.deactivated.connect(lambda: self.reshapeMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == ReShapePolygonMapTool_Web:
                    self.reshapeMapTool.reset()
                    self.reshapeMapToolRight.reset()
                    self.reshapeMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def pasteMapToolPbTriggered(self):
        if self.pasteMapToolPb.isChecked():
            self.pasteMapTool = PastePolygonMapToo_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.pasteMapTool)
            self.pasteMapToolRight = PastePolygonMapToo_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.pasteMapToolRight)
            self.pasteMapTool.deactivated.connect(lambda: self.pasteMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == PastePolygonMapToo_Web:
                    self.pasteMapTool.reset()
                    self.pasteMapToolRight.reset()
                    self.pasteMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def fillHoleMapToolPbTriggered(self):
        if self.fillHoleMapToolPb.isChecked():
            self.fillHoleMapTool = FillHoleMapTool_Web(self.spMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.rightMapCanvas)
            self.spMapCanvas.setMapTool(self.fillHoleMapTool)
            self.fillHoleMapToolRight = FillHoleMapTool_Web(self.rightMapCanvas,
                                                          self.drawLayer,
                                                          self,
                                                          self.taskId,
                                                          self.parentWindow.userId,
                                                          self.spMapCanvas)
            self.rightMapCanvas.setMapTool(self.fillHoleMapToolRight)
            self.fillHoleMapTool.deactivated.connect(lambda: self.fillHoleMapToolPb.setChecked(False))
        else:
            if self.spMapCanvas.mapTool():
                if type(self.spMapCanvas.mapTool()) == FillHoleMapTool_Web:
                    self.fillHoleMapTool.reset()
                    self.fillHoleMapToolRight.reset()
                    self.fillHoleMapToolPb.setChecked(True)
                else:
                    self.spMapCanvas.unsetMapTool(self.spMapCanvas.mapTool())
                    self.rightMapCanvas.unsetMapTool(self.rightMapCanvas.mapTool())
    
    def deleteFeaturePbTriggered(self):
        yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
        tempSelectedIds = self.drawLayer.selectedFeatureIds()
        if tempSelectedIds:
            if len(tempSelectedIds) > 1:
                reply = MessageBox(
                    yoyiTrs._translate("警告"),
                    yoyiTrs._translate("确定要删除吗？"),
                    self
                )
                reply.yesButton.setText(yoyiTrs._translate("确定"))
                reply.cancelButton.setText(yoyiTrs._translate("取消"))
                if reply.exec():
                    pass
                else:
                    return
            beDeleteIds = []
            for id in tempSelectedIds:
                tempFeature = self.drawLayer.getFeature(id)
                beDeleteIds.append(tempFeature.attribute('FeatureId'))
            self.rsdmReq.deleteFeature(beDeleteIds)
        self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
        self.drawServerLayer.triggerRepaint()
        self.updateFeatureTable()
    
    def changeAttrPbTriggered(self):
        try:
            fishnetId = self.fishnetIdList[self.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        tempSelectedIds = self.drawLayer.selectedFeatureIds()
        if tempSelectedIds:
            if len(tempSelectedIds) == 1:
                tempFeature = self.drawLayer.getFeature(tempSelectedIds[0])
                remark1PreAttr = tempFeature.attribute('remark1')
                remark2PreAttr = tempFeature.attribute('remark2')
                remark3PreAttr = tempFeature.attribute('remark3')
            else:
                remark1PreAttr = None
                remark2PreAttr = None
                remark3PreAttr = None

            dialog = WebAttrEditDialogClass(remark1String=self.remark1String,
                                            remark1Type=self.remark1Type,
                                            remark1List=self.remark1List,
                                            remark1PreAttr=remark1PreAttr,
                                            remark2String=self.remark2String,
                                            remark2Type=self.remark2Type,
                                            remark2List=self.remark2List,
                                            remark2PreAttr=remark2PreAttr,
                                            remark3String=self.remark3String,
                                            remark3Type=self.remark3Type,
                                            remark3List=self.remark3List,
                                            remark3PreAttr=remark3PreAttr,
                                            parent=self
                                            )
            dialog.exec()
            if dialog.remark1Attr:
                for id in tempSelectedIds:
                    tempFeature = self.drawLayer.getFeature(id)
                    tempFeatureId = tempFeature.attribute('FeatureId')
                    self.rsdmReq.updateFeature(tempFeatureId,tempFeature.geometry().asWkt(),
                                               self.parentWindow.userId,self.taskId,
                                               dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
                #self.spMapCanvas.refresh()
                #self.rightMapCanvas.refresh()
                self.drawServerLayer.triggerRepaint()
                self.updateFeatureTable()
            dialog.deleteLater()
    def mergeMapToolTriggered(self):
        if len(self.drawLayer.selectedFeatureIds()) >1:
            try:
                fishnetId = self.fishnetIdList[self.TableWidget.selectedItems()[0].row()]
            except Exception as e:
                fishnetId = ""
            geom : QgsGeometry = None
            idList = []
            for featTemp in self.drawLayer.selectedFeatures():
                idList.append(featTemp.attribute('FeatureId'))
                if geom == None:
                    geom = featTemp.geometry()
                else:
                    geom = geom.combine(featTemp.geometry())
            
            if geom.type() == 2:
                dialog = WebAttrEditDialogClass(remark1String=self.remark1String,
                                            remark1Type=self.remark1Type,
                                            remark1List=self.remark1List,
                                            remark1PreAttr=None,
                                            remark2String=self.remark2String,
                                            remark2Type=self.remark2Type,
                                            remark2List=self.remark2List,
                                            remark2PreAttr=None,
                                            remark3String=self.remark3String,
                                            remark3Type=self.remark3Type,
                                            remark3List=self.remark3List,
                                            remark3PreAttr=None,
                                            parent=self
                                            )
                dialog.exec()
                if dialog.remark1Attr:
                    # print("idList:",idList)
                    self.rsdmReq.deleteFeature(idList)
                    self.rsdmReq.addFeature(geom.asWkt(),self.parentWindow.userId,self.taskId,
                                            dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
                    self.drawLayer.deleteFeatures(self.drawLayer.allFeatureIds())
                self.drawServerLayer.triggerRepaint()
                self.updateFeatureTable()
                dialog.deleteLater()
            else:
                MessageBox('信息', "合并失败，矢量过于复杂", self).exec_()
        
    def copyFeatures(self,geomList):
        try:
            fishnetId = self.fishnetIdList[self.TableWidget.selectedItems()[0].row()]
        except Exception as e:
            fishnetId = ""
        dialog = WebAttrEditDialogClass(remark1String=self.remark1String,
                                    remark1Type=self.remark1Type,
                                    remark1List=self.remark1List,
                                    remark1PreAttr=None,
                                    remark2String=self.remark2String,
                                    remark2Type=self.remark2Type,
                                    remark2List=self.remark2List,
                                    remark2PreAttr=None,
                                    remark3String=self.remark3String,
                                    remark3Type=self.remark3Type,
                                    remark3List=self.remark3List,
                                    remark3PreAttr=None,
                                    parent=self
                                    )
        dialog.exec()
        if dialog.remark1Attr:
            for geom in geomList:
                self.rsdmReq.addFeature(geom.asWkt(),self.parentWindow.userId,self.taskId,
                                        dialog.remark1Attr,dialog.remark2Attr,dialog.remark3Attr,fishnetId)
        
        self.drawServerLayer.triggerRepaint()
        self.updateFeatureTable()
        dialog.deleteLater()

    def rightBarConnectFunc(self):
        self.staticPb.clicked.connect(self.staticPbClicked)
    
    def staticPbClicked(self):
        if self.taskId:
            resList = self.rsdmReq.queryRemarkAmount(self.taskId)
            resString = ""
            for content in resList:
                resString += f"{content['name']}: {content['amount']} \n"
            MessageBox('属性统计', f"{resString}", self).exec_()
            
    
    
                
    

                
