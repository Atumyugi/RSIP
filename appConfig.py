import os
import os.path as osp
from enum import Enum
from PyQt5.QtCore import Qt,QSettings


try:
    import torch
    GPUENABLE = True
    #raise(1)
except Exception as e:
    GPUENABLE = False

print('GPUENABLE:',GPUENABLE)

# ROOT
ROOT_PATH = osp.abspath((osp.dirname(__file__)))

PROJECT_STYLE_XML = osp.join(ROOT_PATH,"yoyi.xml")

# update app
UPDATE_APP_NEW = osp.join(ROOT_PATH,"autoUpdate.exe")
UPDATE_APP = osp.join(ROOT_PATH,"点我自动更新.exe")

APP_NAME = "rsdm"


# temp dir
TEMP_DIR = osp.join(ROOT_PATH,"RSDMTEMP")
if not osp.exists(TEMP_DIR):
    os.mkdir(TEMP_DIR)
# mobile sam
SAM_MOBILE_PTH = osp.join(ROOT_PATH,"sm.pt")
# onnx dll
MODEL_PATH = osp.join(ROOT_PATH,"runtimeLib")
ONNX_EXTRA_DLL = osp.join(ROOT_PATH,"runtimeLib","jl1runtime.dll")

# train tool
TRAIN_TOOL_CMD = osp.join(ROOT_PATH,"trainTool.exe").replace("\\","/")
JOINT_LABEL_CMD = osp.join(ROOT_PATH,"JointLabeling.exe").replace("\\","/")

# STRING
STRING_Classify = "classify"
STRING_01_Classify = "01Classify"
STRING_FullClassify = "AllCategory"
STRING_Right = "=>"
STRING_EXPRESSION_VALID = "表达式有效"
STRING_EXPRESSION_INVALID = "表达式无效!"

STRING_PROJECT_CONFIG = "project.config"
STRING_PROJECT_CODEMAP = 'project.codemap'
STRING_SNAPSHOT = "snapshot.png"

# 省市县 矢量
County_Boundary_Path = osp.join(ROOT_PATH,"cb.gpkg")
County_Boundary_Field = "PAC"

# 支持影像后缀
SUPPORT_TIF_POST_LIST = ["tif", "TIF", "TIFF", "GTIFF","png","PNG","jpg","JPG","JPEG"]

# WEB
SAM_HOST = "http://10.10.108.22:6023"
POSTGIS_HOST = "http://10.10.108.22:8080"
# ERROR
ERROR_TIME_OUT = 1

# draw type
DRAW_TYPE_SEG = 1
DRAW_TYPE_CD = 2
DRAW_TYPE_OD = 3
DRAW_TYPE_WMS_SEG = 4
DRAW_TYPE_WMS_CD = 5
DRAW_TYPE_WMS_OD = 6
 
# diy layer tree type
Local_Type = 2
Wms_Type = 3
Bottom_Draw = 4
Bottom_Fishnet = 5
Bottom_Tif = 6
Bottom_Tif2 = 7


# help pdf
HELP_PDF = osp.join(ROOT_PATH,"help.pdf")

# 示例png
EXAMPLE_PNG_PROJECTION = "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,298.257223563,AUTHORITY[\"EPSG\",\"7030\"]],AUTHORITY[\"EPSG\",\"6326\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AXIS[\"Latitude\",NORTH],AXIS[\"Longitude\",EAST],AUTHORITY[\"EPSG\",\"4326\"]]"
EXAMPLE_PNG_GEOTRANSFORM = (125.329939908, 4.492e-06, 0.0, 43.82449777800001, 0.0, -4.492e-06)

# 协同勾画 保存文件夹
Joint_Labeling_History_Dir = osp.join(ROOT_PATH,"jointLabelHistory")
if not osp.exists(Joint_Labeling_History_Dir):
    os.mkdir(Joint_Labeling_History_Dir)

# segTypeDict
SEG_TYPE_DICT = {
    "water": "水体",
    "cropland": "耕地",
    "tree": "林地",
    "building": "建筑物",
    "bareland": "裸土",
    "buildingArea": "建筑区",
    "tarpaulinNet": "苫盖",
    "classify": "全要素分类"
}

#roleCode
ROLE_CODE_DICT = {
    "choujian_manage" : "抽检主管",
    "inspection_user" : "抽检人员",
    "manage_user" : "项目主管",
    "auditor_user" : "质检人员",
    "produce_user" : "生产人员",
    "admin" : "管理员",
    "visitor" : "游客"
}

SEX_DICT = {
    0 : "女性",
    1 : "男性",
}

WEB_PROJECT_STATUS_DICT = {
    "501" : "未开始",
    "502" : "正在进行",
    "503" : "已完成",
}

DRAW_JINGXIU_STATUS_DICT = {
    "ALL" : None,
    "待精修" : '601',
    "待质检" : '603',
    "质检退回" : '604',
    "质检通过" : '605',
}

DRAW_ZHIJIAN_STATUS_DICT = {
    "ALL" : None,
    "待质检" : '603',
    "质检退回" : '604',
    "质检通过" : '605',
    "抽检通过" : '607',
    "抽检退回" : '608',
}

DRAW_CHOUJIAN_STATUS_DICT = {
    "ALL" : None,
    "质检通过" : '605',
    "抽检通过" : '607',
    "抽检退回" : '608',
}

DRAW_MODE_DICT = {
    0 : "普通模式",
    1 : "专业模式"
}

HomeUrlDict = {
    0 : 'forest.jl1.cn',
    1 : '1.1.1.1'
}

GeoserverUrlDict = {
    0 : 'http://1.1.1.1:1',
    1 : 'http://1.1.1.1:1',
}

Jl1TileUrlDict = {
    0 : 'https://1.1.1',
    1 : 'http://1.1.1'
}

SourceReplaceList = ['1','1','1','1']

# ENUM
class AttrType(Enum):
    List = "多选一"
    String = "文本"
    Int = "数值"

class WebDrawQueryType(Enum):
    Draw = "生产"
    Review = "质检"
    Random = "抽检"

class RejectPointReason(Enum):
    NeedAdd = "101"
    NeedDelete = "102"

class RejectPointDrawType(Enum):
    Review = "111"
    Random = "112"



class yoyiSetting():
    def __init__(self):
        self.configIni = osp.join(ROOT_PATH, "rsdmCfg.ini")
        self.configSettingReader = QSettings(self.configIni, QSettings.IniFormat)
        self.configSettingReader.setIniCodec("UTF8")
        if (not os.path.exists(self.configIni)):
            print("没有ini文件或ini文件损坏")
            self.reStoreSetting()
        
        self.checkSettingIsValid('appLanguage','Ch')
        self.checkSettingIsValid('windowStyle',0)
        self.checkSettingIsValid('windowColor','#ff21a1aa')   

        self.checkSettingIsValid('simpleFeature',True)
        self.checkSettingIsValid('horizontalRectangle',True)
        self.checkSettingIsValid('allowMoveFeature',True)
        self.checkSettingIsValid('minMovementDistance',10)
        self.checkSettingIsValid('autoComplete',True)
    
        self.checkSettingIsValid('samIp',"10.10.103.17:6025")
        self.checkSettingIsValid('serverHost',"forest.jl1.cn")
        self.checkSettingIsValid('netMode',0)
        self.checkSettingIsValid('localProject','C://drawLocalProject')

        self.checkSettingIsValid('allowSnap', False)
        self.checkSettingIsValid('snapType',0)
        self.checkSettingIsValid('snapDistance',12)
        self.checkSettingIsValid('streamTolerance',5)
        self.checkSettingIsValid('preloadMode',False)

        self.checkSettingIsValid('netMode',(254, 254, 254))
        self.checkSettingIsValid('darkBgColor',(32, 32, 32))
    
        self.checkSettingIsValid('user',"None")
        self.checkSettingIsValid('pswd',"None")
    
        self.checkSettingIsValid('width',1500)
        self.checkSettingIsValid('height',960)
    
        self.checkSettingIsValid('freeTk',"")
        

        # 内部的一些值
        self.windowTitle = "遥感解译平台"
        self.about = "©版权所有 ???"

    def checkSettingIsValid(self,attr,defaultValue):
        if not self.configSettingReader.contains(attr):
            print(f"不存在{attr}属性，将使用默认属性{defaultValue}")
            self.changeSetting(attr,defaultValue)

    def changeSetting(self,attr,value):
        print("设置默认值：",attr," ",value)
        self.configSettingReader.setValue(attr, value)

    def reStoreSetting(self):
        self.configSettingReader.setValue('appLanguage', 'Ch')
        self.configSettingReader.setValue('windowStyle', 0) # 0 亮色  1 暗色
        self.configSettingReader.setValue('windowColor', "#ff21a1aa")
        #self.configSettingReader.setValue('clickInterval', 180)

        # Labeling
        self.configSettingReader.setValue('simpleFeature', True)
        self.configSettingReader.setValue('horizontalRectangle',True)
        self.configSettingReader.setValue('allowMoveFeature',True)
        self.configSettingReader.setValue('minMovementDistance',10)
        self.configSettingReader.setValue('autoComplete',False)
        # snap
        self.configSettingReader.setValue('allowSnap', False)
        self.configSettingReader.setValue('snapType',0)
        self.configSettingReader.setValue('snapDistance',12)
        self.configSettingReader.setValue('streamTolerance',5)
        self.configSettingReader.setValue('preloadMode',False)

        self.configSettingReader.setValue('samIp', "10.10.103.17:6025")
        self.configSettingReader.setValue('serverHost', "forest.jl1.cn")
        self.configSettingReader.setValue('netMode', 0)
        self.configSettingReader.setValue('localProject',"C://drawLocalProject")

        self.configSettingReader.setValue('lightBgColor', (254, 254, 254))
        self.configSettingReader.setValue('darkBgColor', (32, 32, 32))

        self.configSettingReader.setValue('user', "None")
        self.configSettingReader.setValue('pswd', "None")

        self.configSettingReader.setValue('width',1500)
        self.configSettingReader.setValue('height',960)

        self.configSettingReader.setValue('freeTk',r"")