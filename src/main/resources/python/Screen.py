import sys
import json
import base64
import uiautomator2 as u2

def main():
    device_ip = sys.argv[1] if len(sys.argv) > 1 else None
    d = u2.connect(device_ip) if device_ip else u2.connect()

    # 获取截图
    image_bytes = d.screenshot(format='raw')
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # 获取 XML 控件树
    xml_content = d.dump_hierarchy()

    result = {
        "image": image_base64,
        "xml": xml_content
    }
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()