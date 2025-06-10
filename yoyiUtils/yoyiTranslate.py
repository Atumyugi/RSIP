
# 副边栏
# 消息提示框
# "" : "",
# yoyiTrs : yoyiTrans = self.parentWindow.yoyiTrans
class yoyiTrans:
    def __init__(self,language="Ch"):
        self.language = language

        self.enDict = {
            # 通用语言
            "退出" : "Exit",
            "确认" : "Ok",
            "取消" : "Cancel",
            "错误" : "Error",
            "警告" : "Warning",
            "信息" : "Message",
            "关于" : "About",
            "设置" : "Setting",
            "关闭" : "Close",
            "打开" : "Open",

            # 协同标注相关
            "账号" : "Account",
            "账号角色" : "Account Role",
            "姓名" : "Name",
            "生日" : "Birthday",
            "性别" : "Sex",
            "电话" : "Phone",
            "修改密码" : "Change Password",


            # 图层树相关
            "展开" : "Expand All",
            "全部展开" : "Expand All",
            "折叠" : "Collapse All",
            "全部折叠" : "Collapse All",
            "清除图层" :"Clear Layers",
            "添加组" : "Add Group",
            "将选中为组" : "Set selected as Group",
            "移除选中图层" :"Close Selected Layers",
            "重命名组" :"Rename Group",
            "删除组" :"Delete Group",
            "缩放到图层" :"Zoom to Layer",
            "打开属性表" :"Open Attribute Table",
            "属性" :"Property",
            "标注" : "Labeling",
            "选择要素" : "Select Feature",


            "保存项目" : "Save Project",
            "另存项目" : "Save Project As",
            "保存成功" : "Save Successful",
            "敬请期待" : "Coming soon",
            "复制坐标" : "Copy Coordinates",
            "切换地图坐标系" : "Switch Map Coordinate System",


            "长光卫星技术股份有限公司" : "Chang Guang Satellite Technology CO.LTD",
            "进入官网" : "Visit the official website",
            "吉林一号遥感解译平台" : "RSIP",
            "检查更新" : "Check for Updates",
            "坐标系" : "Coordinate System",

            #文件系统
            "添加栅格图层" : "Add Raster Layer",
            "添加矢量图层" : "Add Vector Layer",
            "刷新" : "Refresh",
            "在文件管理系统中打开" : "Open in File Management System",
            #打开文件对话框
            "选择栅格影像" : "Select Raster File",
            "选择矢量文件" : "Select Vector File",
            "截图当前画布至图像" : "Capture the Current Canvas to an Image",
            "选择文件夹" : "Select Folder",
            
            #栅格算法名
            "创建渔网" : "Create Fishnet",
            "栅格转矢量" : "Raster vectorization",
            "栅格重排波段" : "Raster Recombine",
            "栅格降位" : "Raster Uint16 to Uint8",
            "栅格导出" : "Export Raster",
            "栅格构建金字塔" : "Generate OVR",
            "栅格裁剪" : "Raster Clip",
            "栅格重投影" : "Raster Reproject",
            "栅格合并" : "Raster Merge",
            "栅格计算器" : "Raster Calculator",
            "栅格分区统计" : "Raster Zonal Static",

            #其他算法
            "创建数据集" : "Generate Dataset",
            "划分数据集" : "Split Dataset",

            #矢量算法
            "矢量转栅格" : "Vector Rasterization",
            "矢量导出" : "Export Vector",
            "矢量几何修复" : "Vector Fix",
            "矢量裁剪" : "Vector Clip",
            "矢量相减" : "Vector Erase",
            "矢量简化" : "Vector Simply",
            "矢量缓冲" : "Vector Buffer",
            "矢量相交" : "Vector Intersect",
            "矢量正交" : "Vector Orth",
            "矢量计算质心" : "Cal Centroid",
            "矢量面积计算" : "Vector CalArea",
            "矢量融合" : "Vector Dissolve",
            "矢量转单部件" : "Multi to Single",
            "矢量平滑" : "Vector Smooth",
            "矢量合并" : "Vector Merge",
            "矢量转换投影" : "Vector Reproject",
            "矢量碎斑过滤" : "Remove Area",
            "矢量孔洞填充" : "Fill Hole",
            "矢量变化分析" : "Vector Change Analysis",


            #AI
            "当前软件未搜寻到GPU相关插件，禁止使用" : "The current software has not detected any GPU-related plugins and prohibits their use",
            "当前软件未搜寻到本地模型" : "The current software has not detected any local models.",
            "耕地" : "Cropland",
            "林地" : "Tree",
            "水体" : "Water",
            "建筑" : "Building",
            "塔吊" : "TowerCrane",
            "大棚" : "GreenHouse",
            "破损大棚" : "BrokenGH",
            "风机" : "WindTurbine",
            "体育场" : "Stadium",
            "语义分割" : "Segmentation",
            "实例语义分割" : "InstanceSegmentation",
            "目标检测" : "Detection",
            "水平框目标检测" : "Detection",
            "旋转框目标检测" : "ObbDetection",
            "变化检测" : "ChangeDection",

            #运行进程
            "开始" : "Start",
            "运行中" : "Running",
            "运行结束" : "Running Finished",
            "运行错误" : "Running Error",
            "结果路径" : "Result path",
            "进度" : "Progress",

            # 副边栏
            "主页" : "Home",
            "单景标注" : "SegAnno",
            "变化标注" : "CdAnno",
            "登录系统" : "Login",
            "协同勾画" : "WebAnno",
            "协同标注" : "WebAnno",
            "协同审核" : "WebReview",
            "数据处理" : "DataProcess",
            # 顶部标题
            "无标题" : "No Title",
            # 消息框标题
            
            # 消息框消息
            "确定要退出吗？" : "Do you want to confirm the exit?",
            "未知错误" : "Unkown Error",
            "输入格式非法" : "Input Format is Illegal",
            "您当前版本已经是最新版本!" : "You Are Already on the Latest Version!",
            "恢复默认设置" : "Restore Default Settings",
            "您确定要恢复默认设置吗？" : "Are You Sure Want to Restore Default Settings?",
            "XYZ切片图层无属性窗格" : "XYZ Tile Layer Has No Attribute Pane",
            "当前未选中图层" : "No Layer Currently Selected",
            "确定要移除图层？" : "Are you sure want to delete the layer?" ,
            "您确定要清空吗？" : "Are You Sure Want to Clear?",
            "图层树为空" : "Layer Tree is Empty",
            "确定要移除所有图层？" : "Are you sure want to delete all layers?",
            "至少需要两个图层!" : "At least two layers are required!",
            "未选中栅格图层" : "Unselected grid layer",
            "请输入样本库名称" : "Please Input Dataset Name",
            "请输入样本库描述" : "Please Input Dataset Describe",
            "请输入样本库创建人" : "Please Input Dataset Creator",
            "您勾选了使用字段生成数据集，请等待计算当前选择的字段唯一值列表" : "You have selected to use the field to generate a dataset; please wait while calculating the list of unique values for the current selection.",
            "您没有勾选字段，请填写生成像素值和目标类别" : "You have not selected any fields; please enter them manually.",
            "影像和标签匹配对少于10" : "The number of matches between images and labels is less than 10.",
            "为空" : "is Empty",
            "文件夹不为空" : "Directry is not empty",
            "没有可用GPU" : "not Valid GPU",
            "模型列表为空" : "not Valid Model List Content",
            "x或y的距离太大，至少需要是图层距离的两倍以上" : "The distance in either the x or y direction is too large; it needs to be at least twice the layer distance.",
            "预估格网数量已超过10万，是否要继续？" : "The estimated number of grid cells has exceeded 100,000. Do you want to proceed?",

            # -- 文件
            "不可覆盖原文件" : "Cannot overwrite the existing file",
            "地址非法" : "Address is Illegal",
            "没有有效图层" : "No Valid Layer",
            "没有有效影像" : "No Valid Raster",
            "请检查波段数量大于3,数据类型为Uint8" : "please check band > 3, dataType is Uint8",
            "请检查波段数量大于3,数据类型为Uint8,最小尺寸为1024X1024" : "please check band > 3, dataType is Uint8,miniSize is 1024X1024",
            # -- 矢量
            "没有有效矢量" : "No Valid Shapefile",
            
            "前后期影像一致" : "Consistent Pre and Post Raster",
            "前后期影像没有相交" : "Pre and Post Raster Don't Intersect",
            "前后期影像坐标系不一致" : "Pre and Post Raster Coordinate Systems are Inconsistent",
            "未选择感兴趣范围" : "Area of Interest Not Selected",
            "请输入后缀" : "Please enter the suffix",
            "表达式有效" : "Expression is Valid",
            "表达式无效!" : "Expression is Invalid!",
            "坐标系无效" : "Coordinate System is Invalid",
            "目标坐标系和源坐标系相同" : "Target Coordinate System is the Same as the Source Coordinate System",
            "范围无效" : "Extent is Invalid",
            "路径重复" : "Path Duplicate",
            "确认要清空列表?" : "Are you sure you want to clear the list?",
            "列表为空" : "List is Empty",
            "重组合顺序非法" : "Recombination Order is Illegal",
            "影像和矢量一个是文件一个是文件夹,会启用一对多机制" : "tif or shp is Illegal",
            "不能前后期影像一个是文件一个是文件夹" : "tif and tifII is Illegal",
             # -- 字段
            "没有数值型字段" : "No numeric fields",
            "字段名称非法" : "Field Name is Illegal",
            "未选中字段" : "Unselected fields",
            ## 编辑
            "当前仅限编辑面矢量" : "Only edit Polygon or MultiPolygon",
            "保存编辑" : "Save editing",
            "确定要将编辑内容保存到内存吗？" : "Save Editing?",
            "编辑图层坐标系与地图画布坐标系不符，禁止使用顶点编辑" : "The coordinate system of the editing layer does not match the coordinate system of the map canvas, and vertex editing is prohibited.",
            ## open
            "图层无效" : "Layer is illegal",
            ## xyztiles
            "项目名非法或为空" : "Project Name is Illegal or Empty",
            "XYZ切片地址非法或为空" : "XYZ Tiles is Illegal or Empty",
            # 图层属性
            "单一渲染" : "Single Rendering",
            "分类渲染" : "Categorized Rendering",
            # 智能解译
            "语义分割" : "Segmentation",
            "实例分割" : "InstanceSegmentation",
            "水平框目标检测" : "Detection",
            "旋转框目标检测" : "ObbDetection",
            "变化检测" : "ChangeDection",
            "耕地" : "Cropland",
            "林地" : "Tree",
            "水体" : "Water",
            "建筑" : "Building",
            "塔吊" : "TowerCrane",
            "大棚" : "GreenHouse",
            "风机" : "WindTurbine",
            "体育场" : "Stadium",
            "施工工地" : "ConstructionSite",
            "防尘网" : "DustNet",
            "变电站" : "Substation",
            "电塔" : "ElectricTower",
            "彩钢瓦" : "SteelTile",
            "农膜" : "AgriculturalFilm",
            # 右键菜单
            "删除所选" : "Delete Selected",
            "删除所选路径" : "Delete Selected Path",
            "未选中" : "Unselected",
            "确定要删除吗？" : "Are u sure to delete features?",
            # 标注
            "点击右上角↗创建项目" : "Click the upper right ↗ to create a project",
            "额外图层" : "Extra Layer",
            "底图图层" : "Bottom Layer",
            # snap
            "顶点" : "Vertex",
            "线段" : "Segment",
            "顶点与线段" : "VertexAndSegment",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",
            # "" : "",

        }
    
    def _translate(self,content):
        if self.language == "Ch":
            return content
        else:
            if content in self.enDict.keys():
                return self.enDict[content]
            else:
                return content

