import os
import os.path as osp
from enum import Enum
from typing import List
SourceDir = osp.dirname(osp.dirname(__file__))
UserInfo = osp.join(SourceDir,"userInfo.cfg")

class InferType(Enum):
    Segmentation = "语义分割"
    InstanceSegmentation = "实例分割"
    Detection = "水平框目标检测"
    ObbDetection = "旋转框目标检测"
    ChangeDection = "变化检测"

class InferTypeName(Enum):
    Cropland = "耕地"
    Tree = "林地"
    Water = "水体"
    Building = "建筑"
    TowerCrane = "塔吊"
    GreenHouse = "大棚" 
    BrokenGH = "破损大棚"
    WindTurbine = "风机"
    Stadium = "体育场"
    ConstructionSite = "施工工地"
    DustNet = "防尘网"
    Substation = "变电站"
    ElectricTower = "电塔"
    SteelTile = "彩钢瓦"
    AgriculturalFilm = "农膜"
    Road = "道路"
    Custom = "自定义"

class yoyiCodeMap:
    def __init__(self,name,level,code,parentCode,r=255,g=0,b=0):
        self.name = name
        self.level = level
        self.code = code
        self.parentCode = parentCode
        self.r = r
        self.g = g
        self.b = b

class classifyCMClass:
    def __init__(self):
        self.cateIList = [
            yoyiCodeMap("耕地", 1, "01", None,85,255,0),
            yoyiCodeMap("园地", 1, "02", None,209,255,0),
            yoyiCodeMap("林地", 1, "03", None,49,173,105),
            yoyiCodeMap("草地", 1, "04", None,200,200,0),
            yoyiCodeMap("人工构筑物与堆掘地", 1, "05", None,197,154,140),
            yoyiCodeMap("建筑用地", 1, "06", None,229,103,102),
            yoyiCodeMap("交通运输用地", 1, "07", None,255,160,92),
            yoyiCodeMap("水体", 1, "08", None,74,111,163),
            yoyiCodeMap("荒漠与裸土地", 1, "09", None,215,200,185),
            yoyiCodeMap("湿地", 1, "10", None,100,219,242),
            yoyiCodeMap("特殊用地", 1, "11", None,254,39,37),
            yoyiCodeMap("其他", 1, "0H", None,60,60,60),
        ]

        self.cateIIList = [
            yoyiCodeMap("水田", 2, "0101", "01",0,168,227),
            yoyiCodeMap("旱地", 2, "0102", "01",255,251,177),
            yoyiCodeMap("其他耕地", 2, "010H", "01",90,100,90),

            yoyiCodeMap("果园", 2, "0201", "02",209,255,0),
            yoyiCodeMap("茶园", 2, "0202", "02",209,255,0),
            yoyiCodeMap("橡胶园", 2, "0203", "02",209,255,0),
            yoyiCodeMap("其他园地", 2, "020H", "02",209,255,0),

            yoyiCodeMap("乔木林地", 2, "0301", "03",49,173,105),
            yoyiCodeMap("灌木林地", 2, "0302", "03",100,185,104),
            yoyiCodeMap("乔灌混合林", 2, "0303", "03",40,200,135),
            yoyiCodeMap("竹林", 2, "0304", "03",151,207,178),
            yoyiCodeMap("其他林地", 2, "030H", "03",151,207,178),

            yoyiCodeMap("天然牧草地", 2, "0401", "04",200,200,0),
            yoyiCodeMap("人工牧草地", 2, "0402", "04",200,200,0),
            yoyiCodeMap("其他草地", 2, "040H", "04",200,200,0),

            yoyiCodeMap("工业设施用地", 2, "0501", "05",197,154,140),
            yoyiCodeMap("采矿用地", 2, "0502", "05",197,154,140),
            yoyiCodeMap("人工堆掘地", 2, "0503", "05",197,154,140),
            yoyiCodeMap("农业设施用地", 2, "0504", "05",197,154,140),
            yoyiCodeMap("能源设施用地", 2, "0505", "05",197,154,140),
            yoyiCodeMap("其他构筑物", 2, "050H", "05",197,154,140),

            yoyiCodeMap("城镇建筑用地", 2, "0601", "06",229,103,102),
            yoyiCodeMap("农村宅基地", 2, "0602", "06",229,103,102),
            yoyiCodeMap("居民区", 2, "0603", "06",236,137,138),
            yoyiCodeMap("其他建筑用地", 2, "060H", "06",229,103,102),

            yoyiCodeMap("铁路用地", 2, "0701", "07",255,160,92),
            yoyiCodeMap("公路用地", 2, "0702", "07",255,160,92),
            yoyiCodeMap("农村道路", 2, "0703", "07",255,160,92),
            yoyiCodeMap("其他交通运输用地", 2, "070H", "07",255,160,92),

            yoyiCodeMap("河流水面", 2, "0801", "08",74,111,163),
            yoyiCodeMap("湖泊水面", 2, "0802", "08",74,111,163),
            yoyiCodeMap("坑塘水面", 2, "0803", "08",74,111,163),
            yoyiCodeMap("沟渠", 2, "0804", "08",74,111,163),
            yoyiCodeMap("水工建筑", 2, "0805", "08",74,111,163),
            yoyiCodeMap("冰川积雪", 2, "0806", "08"),
            yoyiCodeMap("其他水体", 2, "080H", "08",215,237,251),

            yoyiCodeMap("盐碱地", 2, "0901", "09",200,190,170),
            yoyiCodeMap("沙地", 2, "0902", "09",200,190,170),
            yoyiCodeMap("裸土地", 2, "0903", "09",200,190,170),
            yoyiCodeMap("裸岩石砾地", 2, "0904", "09",200,190,170),
            yoyiCodeMap("其他荒漠与裸土地", 2, "090H", "09",200,190,170),

            yoyiCodeMap("红树林地", 2, "1001", "10"),
            yoyiCodeMap("森林沼泽", 2, "1002", "10"),
            yoyiCodeMap("灌丛沼泽", 2, "1003", "10"),
            yoyiCodeMap("沼泽草地", 2, "1004", "10"),
            yoyiCodeMap("盐田", 2, "1005", "10"),
            yoyiCodeMap("沿海滩涂", 2, "1006", "10"),
            yoyiCodeMap("内陆滩涂", 2, "1007", "10"),
            yoyiCodeMap("沼泽地", 2, "1008", "10"),
            yoyiCodeMap("其他湿地", 2, "100H", "10"),

            yoyiCodeMap("城市绿地", 2, "1101", "11",49,173,105),
            yoyiCodeMap("海岸线用地", 2, "1102", "11"),
            yoyiCodeMap("火烧迹地", 2, "1103", "11"),
            yoyiCodeMap("秸秆离田地块", 2, "1104", "11"),
            yoyiCodeMap("城市裸土", 2, "1105", "11"),
            yoyiCodeMap("其他特殊用地", 2, "110H", "11"),

            yoyiCodeMap("云", 2, "0H01", "0H"),
            yoyiCodeMap("阴影", 2, "0H02", "0H"),
            #yoyiCodeMap("积雪", 2, "0H03", "0H"),
        ]

        self.cateIIIList = [
            yoyiCodeMap("水稻", 3, "010101", "0101"),

            yoyiCodeMap("玉米", 3, "010201", "0102"),
            yoyiCodeMap("小麦", 3, "010205", "0102"),
            yoyiCodeMap("马铃薯", 3, "010203", "0102"),
            yoyiCodeMap("大豆", 3, "010204", "0102"),
            yoyiCodeMap("花生", 3, "010205", "0102"),
            yoyiCodeMap("油菜籽", 3, "010206", "0102"),
            yoyiCodeMap("棉花", 3, "010207", "0102"),
            yoyiCodeMap("高粱", 3, "010208", "0102"),
            yoyiCodeMap("烟叶", 3, "010209", "0102"),
            yoyiCodeMap("红薯", 3, "010210", "0102"),
            yoyiCodeMap("辣椒", 3, "010211", "0102"),
            yoyiCodeMap("姜", 3, "010212", "0102"),
            yoyiCodeMap("其他旱地", 3, "01020H", "0102"),

            yoyiCodeMap("葡萄园", 3, "020101", "0201"),
            yoyiCodeMap("苹果园", 3, "020102", "0201"),
            yoyiCodeMap("枸杞园", 3, "020103", "0201"),
            yoyiCodeMap("其他果园", 3, "02010H", "0201"),

            yoyiCodeMap("苫盖", 3, "050301", "0503"),
            yoyiCodeMap("其他堆掘地", 3, "05030H", "0503"),

            yoyiCodeMap("温室大棚", 3, "050401", "0504"),
            yoyiCodeMap("网箱养殖", 3, "050402", "0504"),
            yoyiCodeMap("人参大棚", 3, "050403", "0504"),
            yoyiCodeMap("覆膜", 3, "050404", "0504"),
            yoyiCodeMap("其他农业设施用地", 3, "05040H", "0504"),

            yoyiCodeMap("光伏", 3, "050501", "0505"),
            yoyiCodeMap("其他能源设施用地", 3, "05050H", "0505"),

            yoyiCodeMap("城市建筑", 3, "060101", "0601"),
            yoyiCodeMap("灾损建筑", 3, "060102", "0601"),
            yoyiCodeMap("其他城镇建筑", 3, "06010H", "0601"),

            yoyiCodeMap("农村建筑", 3, "060201", "0602"),

            yoyiCodeMap("工业厂房", 3, "060H01", "060H"),

            yoyiCodeMap("堤坝", 3, "080501", "0805"),
            yoyiCodeMap("工业厂房", 3, "08050H", "0805"),
        ]

        self.cateICodeDict = self.getCateIDict()
        self.cateINameDict = self.getCateIDict(nameKey=True)
        self.cateIICodeDict = self.getCateIIDict()
        self.cateIINameDict = self.getCateIIDict(nameKey=True)
        self.cateIIICodeDict = self.getCateIIIDict()
        self.cateIIINameDict = self.getCateIIIDict(nameKey=True)


    def getCateIDict(self,nameKey=False):
        resDict = {}
        for cateI in self.cateIList:
            if nameKey:
                resDict[cateI.name] = cateI
            else:
                resDict[cateI.code] = cateI
        return resDict

    def getCateIIDict(self,nameKey=False):
        resDict = {}
        for cateII in self.cateIIList:
            if nameKey:
                resDict[cateII.name] = cateII
            else:
                resDict[cateII.code] = cateII
        return resDict

    def getCateIIIDict(self,nameKey=False):
        resDict = {}
        for cateIII in self.cateIIIList:
            if nameKey:
                resDict[cateIII.name] = cateIII
            else:
                resDict[cateIII.code] = cateIII
        return resDict

    def getName_IdDict(self):
        resDict = {}
        for yoyiCM in self.cateIList:
            resDict[yoyiCM.name] = yoyiCM.code
        for yoyiCM in self.cateIIList:
            resDict[yoyiCM.name] = yoyiCM.code
        for yoyiCM in self.cateIIIList:
            resDict[yoyiCM.name] = yoyiCM.code
        return resDict

    def getCodeByName(self, name):
        if name in self.cateINameDict.keys():
            tempycm : yoyiCodeMap = self.cateINameDict[name]
        else:
            if name in self.cateIINameDict.keys():
                tempycm: yoyiCodeMap = self.cateIINameDict[name]
            else:
                if name in self.cateIIINameDict.keys():
                    tempycm: yoyiCodeMap = self.cateIIINameDict[name]
                else:
                    return "None"
        return tempycm.code

    def getColorMapByNameList(self,nameList):
        resColorMap = {}
        for name in nameList:
            if name in self.cateINameDict:
                tempCate : yoyiCodeMap = self.cateINameDict[name]
                resColorMap[name] = [name,tempCate.r,tempCate.g,tempCate.b]
            elif name in self.cateIINameDict:
                tempCate : yoyiCodeMap = self.cateIINameDict[name]
                resColorMap[name] = [name,tempCate.r,tempCate.g,tempCate.b]
            elif name in self.cateIIINameDict:
                tempCate : yoyiCodeMap = self.cateIIINameDict[name]
                resColorMap[name] = [name,tempCate.r,tempCate.g,tempCate.b]
            else:
                resColorMap[name] = [name,255,0,0]
        
        return resColorMap


class detecCMClass:
    def __init__(self):
        self.cateIList = [
            yoyiCodeMap("飞机", 1, "01", None),
            yoyiCodeMap("船舶", 1, "02", None),
            yoyiCodeMap("火车", 1, "03", None),
            yoyiCodeMap("车辆", 1, "04", None),
            yoyiCodeMap("体育设施", 1, "05", None),
            yoyiCodeMap("交通设施", 1, "06", None),
            yoyiCodeMap("设备及构筑物", 1, "07", None),
            yoyiCodeMap("综合地物", 1, "08", None),
            yoyiCodeMap("其他", 1, "0H", None),
        ]

        self.cateIIList = [
            yoyiCodeMap("客机", 2, "0101", "01"),
            yoyiCodeMap("小型飞机", 2, "0102", "01"),
            yoyiCodeMap("货物运输机", 2, "0103", "01"),
            yoyiCodeMap("直升机", 2, "0104", "01"),

            yoyiCodeMap("摩托艇", 2, "0201", "02"),
            yoyiCodeMap("快艇", 2, "0202", "02"),
            yoyiCodeMap("帆船", 2, "0203", "02"),
            yoyiCodeMap("拖船", 2, "0204", "02"),
            yoyiCodeMap("驳船", 2, "0205", "02"),
            yoyiCodeMap("渔船", 2, "0206", "02"),
            yoyiCodeMap("渡船", 2, "0207", "02"),
            yoyiCodeMap("货柜船", 2, "0208", "02"),
            yoyiCodeMap("油轮", 2, "0209", "02"),
            yoyiCodeMap("工程船舶", 2, "0210", "02"),
            yoyiCodeMap("采砂船", 2, "0211", "02"),

            yoyiCodeMap("轿车", 2, "0401", "04"),
            yoyiCodeMap("货车", 2, "0402", "04"),
            yoyiCodeMap("挖掘机", 2, "0403", "04"),
            yoyiCodeMap("农机", 2, "0405", "04"),

            yoyiCodeMap("田径场", 2, "0501", "05"),
            yoyiCodeMap("篮球场", 2, "0502", "05"),
            yoyiCodeMap("网球场", 2, "0503", "05"),
            yoyiCodeMap("游泳池", 2, "0504", "05"),
            yoyiCodeMap("足球场", 2, "0505", "05"),
            yoyiCodeMap("高尔夫球场", 2, "0506", "05"),

            yoyiCodeMap("港口", 2, "0601", "06"),
            yoyiCodeMap("火车站", 2, "0602", "06"),
            yoyiCodeMap("机场", 2, "0603", "06"),
            yoyiCodeMap("立交桥", 2, "0604", "06"),
            yoyiCodeMap("直升机坪", 2, "0605", "06"),
            yoyiCodeMap("停车场", 2, "0606", "06"),
            yoyiCodeMap("机库", 2, "0607", "06"),
            yoyiCodeMap("环岛", 2, "0608", "06"),
            yoyiCodeMap("交叉路口", 2, "0609", "06"),
            yoyiCodeMap("高速路服务区", 2, "0610", "06"),
            yoyiCodeMap("高速路收费站", 2, "0611", "06"),
            yoyiCodeMap("桥梁", 2, "0612", "06"),

            yoyiCodeMap("在建工程", 2, "0701", "07"),
            yoyiCodeMap("特殊建筑", 2, "0702", "07"),
            yoyiCodeMap("塔吊", 2, "0703", "07"),
            yoyiCodeMap("风力发电机", 2, "0704", "07"),
            yoyiCodeMap("集装箱", 2, "0705", "07"),
            yoyiCodeMap("油罐", 2, "0706", "07"),
            yoyiCodeMap("高压电塔", 2, "0707", "07"),
            yoyiCodeMap("污水处理池", 2, "0708", "07"),
            yoyiCodeMap("排污口", 2, "0709", "07"),

            yoyiCodeMap("垃圾堆", 2, "0801", "08"),
            yoyiCodeMap("垃圾站", 2, "0802", "08"),
            yoyiCodeMap("变电站", 2, "0803", "08"),
            yoyiCodeMap("污水处理厂", 2, "0804", "08"),
            yoyiCodeMap("陵园墓地", 2, "0805", "08"),

            yoyiCodeMap("火", 2, "0H01", "0H"),
            yoyiCodeMap("烟", 2, "0H02", "0H"),
        ]

        self.cateICodeDict = self.getCateIDict()
        self.cateINameDict = self.getCateIDict(nameKey=True)
        self.cateIICodeDict = self.getCateIIDict()
        self.cateIINameDict = self.getCateIIDict(nameKey=True)

    def getCateIDict(self, nameKey=False):
        resDict = {}
        for cateI in self.cateIList:
            if nameKey:
                resDict[cateI.name] = cateI
            else:
                resDict[cateI.code] = cateI
        return resDict

    def getCateIIDict(self, nameKey=False):
        resDict = {}
        for cateII in self.cateIIList:
            if nameKey:
                resDict[cateII.name] = cateII
            else:
                resDict[cateII.code] = cateII
        return resDict

    def getName_IdDict(self):
        resDict = {}
        for yoyiCM in self.cateIList:
            resDict[yoyiCM.name] = yoyiCM.code
        for yoyiCM in self.cateIIList:
            resDict[yoyiCM.name] = yoyiCM.code
        return resDict

    def getCodeByName(self, name):
        if name in self.cateINameDict.keys():
            tempycm: yoyiCodeMap = self.cateINameDict[name]
        else:
            if name in self.cateIINameDict.keys():
                tempycm: yoyiCodeMap = self.cateIINameDict[name]
            else:
                return "None"
        return tempycm.code


if __name__ == "__main__":

    a = InferTypeName['Cropland']
    print(type(a),a)