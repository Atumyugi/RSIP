import os
import os.path as osp

from ui.helpWindow import Ui_Frame

from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QIcon

from qfluentwidgets import Flyout


class HelpWidgetWindowClass(QFrame,Ui_Frame):
    def __init__(self,parent=None):
        super(HelpWidgetWindowClass, self).__init__(parent)
        self.parentWindow = parent 
        self.setupUi(self)
        self.setObjectName("Frame_Help")
        self.connectFunc()

    def connectFunc(self):
        self.panHelpPb.clicked.connect(self.showPanHelp)
        self.magicHelpPb.clicked.connect(self.showMagicHelp)
        self.polygonHelpPb.clicked.connect(self.showPolygonHelp)
        self.rectangleHelpPb.clicked.connect(self.showRectangleHelp)
        self.circleHelpPb.clicked.connect(self.showCircleHelp)

        self.selectHelpPb.clicked.connect(self.showSelectHelp)
        self.deleteHelpPb.clicked.connect(self.showDeleteHelp)
        self.clearHelpPb.clicked.connect(self.showClearHelp)
        self.mergeHelpPb.clicked.connect(self.showMergeHelp)                                                 
        self.createExtentHelpPb.clicked.connect(self.showCreateExtentHelp)

        self.copyHelpPb.clicked.connect(self.showCopyExtentHelp)
        self.vertexHelpPb.clicked.connect(self.showVertexExtentHelp)
        self.reshapeHelpPb.clicked.connect(self.showReshapeExtentHelp)
        self.splitHelpPb.clicked.connect(self.showSplitExtentHelp)
        self.fillHoleHelpPb.clicked.connect(self.showFillHoleExtentHelp)

    def showPanHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/gis_pan.png"), 
            title='漫游工具',
            content="快捷键： Q \n"
                    "使用方法： 按住鼠标拖动地图平移，转动滚轮缩放地图",
            target=self.panHelpPb,
            parent=self, 
            isClosable=True
        )   
 
    def showMagicHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/infer/clsfy_magic.png"),
            title='魔术棒工具',
            content="快捷键： W \n"
                    "使用方法： ①鼠标左键添加正标签，右键添加负标签，空格确认生成\n"
                    "②拖动鼠标绘制线条，松开鼠标确认生成\n"
                    "③Ctrl加左键直接生成结果，可以使用Ctrl加左键挖洞\n",
            target=self.magicHelpPb,
            parent=self,
            isClosable=True
        )

    def showPolygonHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/edit_polygon.png"),
            title='面要素工具',
            content="快捷键： E \n"
                    "使用方法： 勾画不规则面要素\n"
                    "左键添加点，右键确认生成\n"
                    "如果勾画错误可以点击回退键（BackSpace）撤回左键添加的点\n",
            target=self.polygonHelpPb,
            parent=self,
            isClosable=True
        )

    def showRectangleHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/edit_rectangle.png"),
            title='矩形要素工具',
            content="快捷键： R \n"
                    "使用方法： 勾画矩形面要素\n"
                    "左键添加顶点，右键确认生成矩形\n"
                    "使用该工具后，会弹出一个选择窗口，第一个为水平矩形，第二个为旋转矩形工具\n",
            target=self.rectangleHelpPb,
            parent=self,
            isClosable=True
        )

    def showCircleHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/edit_circle.png"),
            title='圆形要素工具',
            content="快捷键： T \n"
                    "使用方法： 勾画圆形面要素\n"
                    "左键添加圆心，右键确认生成圆形要素\n",
            target=self.circleHelpPb,
            parent=self,
            isClosable=True
        )

    def showSelectHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_select_multi.png"),
            title='选择要素工具',
            content="快捷键： S \n"
                    "使用方法： 选择要素\n"
                    "左键直接点击： 取消选中其他要素，并选中当前点击的要素\n"
                    "左键绘制矩形范围： 取消选中其他要素，并选中当前范围的要素\n"
                    "按住Ctrl不会取消选中其他要素\n"
                    "右键弹出菜单： ①删除所选要素 ②简化所选要素 ③拆分所选要素组件 ④填充所选要素孔洞",
            target=self.selectHelpPb,
            parent=self,
            isClosable=True
        )

    def showDeleteHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_delete_select.png"),
            title='删除要素',
            content="快捷键： DEL\n"
                    "使用方法： 删除所选要素\n",
            target=self.deleteHelpPb,
            parent=self,
            isClosable=True
        )

    def showClearHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_cleart_select.png"),
            title='取消选中',
            content="快捷键： 无\n"
                    "使用方法： 清除当前所选要素的选中状态，不是删除，只是取消选中\n",
            target=self.clearHelpPb,
            parent=self,
            isClosable=True
        )

    def showMergeHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_merge.png"),
            title='合并要素',
            content="快捷键： F1\n"
                    "使用方法： 将当前所选中的所有要素合并为一个要素\n",
            target=self.mergeHelpPb,
            parent=self,
            isClosable=True
        )

    def showCreateExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_extent.png"),
            title='创建边框',
            content="快捷键： F2\n"
                    "使用方法： 创建当前切片范围的矩形最大边框，当切片全部为一个类型时可以使用\n",
            target=self.createExtentHelpPb,
            parent=self,
            isClosable=True
        )

    def showCopyExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_paste.png"),
            title='复制要素工具',
            content="快捷键： V\n"
                    "使用方法： 直接复制当前选中的要素，按下左键即可复制\n",
            target=self.copyHelpPb,
            parent=self,
            isClosable=True
        )

    def showVertexExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_vertexTool.png"),
            title='顶点编辑工具',
            content="快捷键： X\n"
                    "使用方法： 单击左键选中要素\n"
                    "系统会生成两个判断标记，\n"
                    "大圆形为当前鼠标最近的顶点，十号为当前鼠标最近的边"
                    "单击左键移动最近的顶点，单机右键添加新顶点到最近的边\n"
                    "双击鼠标取消选中要素，再次单击左键选中要素",
            target=self.vertexHelpPb,
            parent=self,
            isClosable=True
        )

    def showReshapeExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_clip_1.png"),
            title='重塑要素工具',
            content="快捷键： C\n"
                    "使用方法： 重塑当前选中的要素\n"
                    "请注意，需要先使用选择要素工具(S)，选中需要重塑的要素\n"
                    "可以割掉自己不想要的地方，也可以添加自己想要的补丁",
            target=self.reshapeHelpPb,
            parent=self,
            isClosable=True
        )

    def showSplitExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_clip_polygon.png"),
            title='剪切要素工具',
            content="快捷键： Z\n"
                    "使用方法： 剪切当前选中的要素\n"
                    "请注意，需要先使用选择要素工具(S)，选中需要重塑的要素\n"
                    "绘制出跨越要素的线条，将要素一分为二",
            target=self.splitHelpPb,
            parent=self,
            isClosable=True
        )

    def showFillHoleExtentHelp(self):
        Flyout.create(
            icon=QIcon(":/img/icoNew/gis/shp_fillhole.png"),
            title='消除孔洞工具',
            content="快捷键： B\n"
                    "使用方法： 消除要素孔洞\n"
                    "单击左键，自动消除与当前点击位置相交的要素中的孔洞\n",
            target=self.fillHoleHelpPb,
            parent=self,
            isClosable=True
        )



