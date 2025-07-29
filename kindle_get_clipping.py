import os
import re
import json

def parse_and_group_clippings(file_path, output_json_path='grouped_clippings.json'):
    """
    解析 'My Clippings.txt' 文件，将标注按书名分组，并保存为JSON文件。
    兼容有无页码的情况。
    
    :param file_path: 'My Clippings.txt' 的文件路径。
    :param output_json_path: 输出的JSON文件的路径。
    """
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 '{file_path}'")
        return None

    print(f"正在解析 '{file_path}'...")
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    clippings_raw = content.split('==========\n')
    parsed_clippings = []
    
    # 正则表达式，用于匹配Kindle的标注格式
    pattern = re.compile(
        r"^(?P<title>.+?)(?:\s*\(.+?\))?\n"
        r"-\s*您在(?:第 (?P<page>\d+) 页（)?"
        r"位置 #(?P<loc_start>\d+)(?:-(?P<loc_end>\d+))?.+?\n\n"
        r"(?P<text>.+)",
        re.MULTILINE
    )

    for entry in clippings_raw:
        if not entry.strip():
            continue
        
        match = pattern.search(entry.strip())
        if match:
            data = match.groupdict()
            page_number = data.get('page')
            
            # 清理并提取信息
            parsed_clippings.append({
                'title': data['title'].strip().replace('\ufeff', ''),
                'page': int(page_number) if page_number else None,
                'location_start': int(data['loc_start']),
                'text': data['text'].strip()
            })
            
    if not parsed_clippings:
        print("没有找到任何有效的标注。")
        return None

    print(f"解析完成，共找到 {len(parsed_clippings)} 条标注。")

    # --- 按 'title' 分组 ---
    grouped_by_title = {}
    for clipping in parsed_clippings:
        title = clipping['title']
        # 如果字典中还没有这个title，就创建一个新列表
        if title not in grouped_by_title:
            grouped_by_title[title] = []
        # 将当前标注（为了不冗余，可以从标注中移除title）添加到对应的列表中
        clipping_data = clipping.copy()
        del clipping_data['title'] # 在每个条目中移除title，因为title已经是键了
        grouped_by_title[title].append(clipping_data)
    
    # --- 保存为JSON文件 ---
    print(f"正在将分组后的标注保存到 '{output_json_path}'...")
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            # ensure_ascii=False 确保中文等字符正确显示
            # indent=4 使JSON文件格式优美，易于阅读
            json.dump(grouped_by_title, json_file, ensure_ascii=False, indent=4)
        print("成功保存JSON文件。")
    except IOError as e:
        print(f"错误：无法写入文件 '{output_json_path}'。错误信息: {e}")
        return None

    return grouped_by_title

def get_clippings_file():

    import mtp.win_access as mtp_access # 明确导入MTP库

    def find_kindle():
        """查找连接的 Kindle 设备"""
        print("正在通过 MTP 查找 Kindle 设备...")
        devices = mtp_access.get_portable_devices()
        for dev in devices:
            # 使用 "Kindle" 或 "Scribe" 进行更可靠的识别
            if "Kindle" in dev.name or "Scribe" in dev.name:
                print(
                    f"找到设备: "
                    f"名称: {dev.name}, "
                    f"描述: {dev.description}"
                )
                return dev
        print("未找到连接的 Kindle 设备。请确保设备已连接、解锁并处于文件传输模式。")
        return None
    
    def find_document_folder(dev : mtp_access.PortableDevice):
        """查找 Kindle 设备上的 documents 文件夹"""
        # Kindle 的 MTP 路径通常不包含 "Internal Storage" 这层，而是直接是存储根
        # 我们直接在根目录寻找 documents
        for storage in dev.get_content():
            # content.get_child() 是查找直接子项的更可靠方法
            document_folder = storage.get_child("documents")
            if document_folder and document_folder.content_type == mtp_access.WPD_CONTENT_TYPE_DIRECTORY:
                print(f"找到 Documents 文件夹: {document_folder.full_filename}")
                return document_folder
            
        print("错误: 未在设备上找到 'documents' 文件夹。")
        return None
    
    def get_clippings_file_():

        devices = find_kindle()
        if not devices:
            return None
        document_folder = find_document_folder(devices)
        if not document_folder:
            devices.close() # 关闭设备连接
            return None
        # 在 documents 文件夹中查找 My Clippings.txt
        clippings_file = document_folder.get_child("My Clippings.txt")
        if clippings_file and clippings_file.content_type == mtp_access.WPD_CONTENT_TYPE_FILE:
            print(f"找到标注文件: {clippings_file.full_filename}")
            try:
                print(f"  -> 正在从设备下载文件...")
                clippings_file.download_file("My Clippings.txt")
            except Exception as e:
                print(f"错误: 无法下载文件 '{clippings_file.full_filename}'。错误信息: {e}")
                devices.close()
                return None 
            
            devices.close() # 关闭设备连接
            return True
        else:
            print("错误: 未在设备上找到 'My Clippings.txt' 文件。")
            devices.close()
            return None

        
    if get_clippings_file_():
        print("成功获取 'My Clippings.txt' 文件。")
        return "My Clippings.txt"
    else:
        return None
    
if __name__ == "__main__":

    my_clippings_file = get_clippings_file()
    if my_clippings_file:
        output_json = 'grouped_clippings.json'
        parse_and_group_clippings(my_clippings_file, output_json)
    else:
        print("无法获取 'My Clippings.txt' 文件，请检查设备连接和状态。")
        
    
       
        
        
    
    
