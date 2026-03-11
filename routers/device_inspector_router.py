import base64
import json
import traceback
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger
import xml.etree.ElementTree as ET

# 假设你的 uiautomator2 / adb 连接管理已经在一个地方做好了
# 如果没有，你需要根据你的实际情况引入 device 实例
# 这里做个简单的模拟和错误提示
try:
    import uiautomator2 as u2
    # 也可以是你自己维护的连接池或全局单例
    # 此处假设用户只有一台设备或者连上了默认的一台
    device = u2.connect() 
except Exception as e:
    device = None
    logger.warning(f"uiautomator2 初始化失败或未连接设备: {e}")

router = APIRouter(prefix="/api/device/inspector")

class XPathRequest(BaseModel):
    bounds: str

@router.get("/dump")
async def dump_screen_and_hierarchy():
    if device is None:
        return {"success": False, "message": "设备未连接，请检查 USB 或 WiFi 连接并确保 uiautomator2 可用"}
        
    try:
        # 1. 截取屏幕
        import io
        image_pil = device.screenshot()
        buffered = io.BytesIO()
        image_pil.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # 2. 获取界面 XML 树
        xml_content = device.dump_hierarchy()
        
        # 3. 解析 XML 为扁平的节点列表，以减小传给前端的数据体积
        root = ET.fromstring(xml_content.encode('utf-8'))
        nodes = []
        for elem in root.iter('node'):
            # 将 xml 的 tag attrib 直接转换为字典
            attr = dict(elem.attrib)
            # 过滤掉一些意义不大的属性节约带宽
            if 'bounds' in attr and attr['bounds'] != '[0,0][0,0]':
                nodes.append(attr)
                
        return {
            "success": True, 
            "data": {
                "image_base64": image_base64,
                "nodes": nodes,
                # "xml": xml_content # 如果前端也需要完整的 xml 树结构
            }
        }
    except Exception as e:
        logger.error(f"设备信息拉取异常: {traceback.format_exc()}")
        return {"success": False, "message": f"设备信息拉取异常: {e}"}


@router.post("/xpath")
async def generate_xpath(request: XPathRequest):
    if device is None:
        return {"success": False, "message": "设备未连接"}
        
    try:
        target_bounds = request.bounds
        if not target_bounds:
             return {"success": False, "message": "缺少 bounds 参数"}
             
        # 实时获取当然最好，但为了避免瞬间截断，可以复用之前拉数据时的同一份 xml
        # 这里为了简单，我们重新 get 一次或者写算法
        xml_content = device.dump_hierarchy()
        
        # 使用 lxml 会更方便 XPath 的向上回溯计算，这里给出基于标准库的简单生成：
        from lxml import etree
        root = etree.fromstring(xml_content.encode('utf-8'))
        
        target_node = None
        for node in root.xpath('//node'):
            if node.get('bounds') == target_bounds:
                target_node = node
                break
                
        if target_node is None:
            return {"success": False, "message": "未在当前屏幕找到对应 bounds 的节点"}
            
        # 开始我们的简单生成算法
        # 1. 有 ID 直接用 ID
        # res_id = target_node.get('resource-id')
        # if res_id:
        #     return {"success": True, "data": {"xpath": f"//*[@resource-id='{res_id}']"}}
            
        # 绝对路径回溯算法
        current = target_node
        path_segments = []
        while current is not None and current.tag == 'node':
            node_class = current.get('class')
            if not node_class:
                break
            # 统计在父节点中，排在第几个同样的 class (用于生成类似 [1], [2] 的索引)
            preceding_siblings = current.xpath(f"./preceding-sibling::node[@class='{node_class}']")
            index = len(preceding_siblings) + 1
            
            segment = f"node[@class='{node_class}'][{index}]"
            path_segments.insert(0, segment)
            current = current.getparent()
            
        absolute_xpath = "//" + "/".join(path_segments)
        
        return {
            "success": True, 
            "data": {
                "xpath": absolute_xpath
            }
        }
    except Exception as e:
         logger.error(f"XPath生成异常: {traceback.format_exc()}")
         return {"success": False, "message": f"XPath生成异常: {e}"}
