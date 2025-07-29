import os
import re
import json

def find_text_in_source_txt(clipping : dict, 
                            source_txt_content : str,
                            total_chars : int, 
                            total_locs : int,
                            start_locs : int,
                            search_window : int):
    """
    使用比例换算法在源TXT文件中精确定位标注文本。
    
    :param clipping: 包含标注信息的字典，必须包含 'text', 'page', 'location_start' 键。
    
    :param source_txt_content: 源TXT文件的内容字符串。
    
    :param total_chars: 源TXT文件的总字符数。
    
    :param total_locs: 源TXT文件的总位置数。

    :param start_locs: 源TXT文件的起始位置数。

    :param search_window: 搜索窗口大小，单位为字符数。

    :return: 如果找到匹配的文本，返回一个包含起始和结束字符位置的列表 [start_pos, end_pos]；否则返回 None。    
    """
    print(f"\n正在处理标注: '{clipping['text'][:50]}...'")
    print(f"原始信息: 位置 #{clipping['location_start']}")

    estimated_char_pos = int((clipping['location_start'] - start_locs) / (total_locs - start_locs) * total_chars)
    print(f"估算出的字符位置: {estimated_char_pos}")

    highlighted_text = clipping['text']
    search_start = max(0, estimated_char_pos - search_window)
    search_end = min(total_chars, estimated_char_pos + len(highlighted_text) + search_window)

    found_pos = source_txt_content.find(highlighted_text, search_start, search_end)

    if found_pos != -1:
        print(f"✅ 成功定位! 文本位于源TXT文件的第 {found_pos} 个字符处。")
        return [found_pos,found_pos + len(clipping['text'])]
    else:
        print("❌ 错误: 未能在源文件中找到匹配的标注内容。")
        return None


    
def find_sentences_by_range(text: str, index_range : tuple):
    """
    根据给定的索引范围 (start, end)，找到一个包含该范围的完整句子或多个句子。

    返回的文本片段会从 start_index 所在句子的开头开始，
    到 end_index 所在句子的结尾结束。

    :param text: 待搜索的完整文本。
    :param index_range: 一个元组或列表，格式为 (start_index, end_index)。
    :return: 包含指定范围的、从句子开头到结尾的文本字符串。
    """
    start_index, end_index = index_range
    
    # 检查索引是否有效
    if not (0 <= start_index < len(text) and 0 <= end_index < len(text) and start_index <= end_index):
        print("错误: 索引范围无效。")
        return ""

    # 定义句子的结束符
    sentence_enders = {'。', '!', '！', '?', '？', '\n'}

    # 1. 寻找文本片段的真正起点
    # 从 `start_index` 向前搜索，找到它所在句子的起点
    sentence_start = 0
    for i in range(start_index, -1, -1):
        if text[i] in sentence_enders:
            sentence_start = i + 1  # 句子的真正起点是标点符号的后一个字符
            break
    
    # 去除可能存在的前导空格或换行符
    while sentence_start < len(text) and text[sentence_start].isspace():
        sentence_start += 1

    # 2. 寻找文本片段的真正终点
    # 从 `end_index` 向后搜索，找到它所在句子的终点
    sentence_end = len(text)
    for i in range(end_index, len(text)):
        if text[i] in sentence_enders:
            sentence_end = i + 1  # 句子的终点包含这个标点符号
            break

    return sentence_start, sentence_end, text[sentence_start:sentence_end]

def find_paragraph_by_range(text : str, index_range : tuple):
    """
    根据给定的索引范围 (start, end)，找到一个包含该范围的完整段落。

    返回的文本片段会从 start_index 所在段落的开头开始，
    到 end_index 所在段落的结尾结束。

    :param text: 待搜索的完整文本。
    :param index_range: 一个元组或列表，格式为 (start_index, end_index)。
    :return: 包含指定范围的、从段落开头到结尾的文本字符串。
    """
    start_index, end_index = index_range

    # 检查索引是否有效
    if not (0 <= start_index < len(text) and 0 <= end_index < len(text) and start_index <= end_index):
        print("错误: 索引范围无效。")
        return ""

    # 定义段落的结束符
    # 两个换行符，以及或一个换行符+中文空格
    paragraph_enders = {'\n\n', '\r\n\r\n' , '\n　'}

    # 1. 寻找文本片段的真正起点
    # 从 `start_index` 向前搜索，找到它所在段落的起点
    paragraph_start = 0
    for i in range(start_index, -1, -1):
        if text[i:i+2] in paragraph_enders:
            paragraph_start = i + 2  # 段落的真正起点是两个换行符之后
            break

    # 去除可能存在的前导空格或换行符
    while paragraph_start < len(text) and text[paragraph_start].isspace():
        paragraph_start += 1

    # 2. 寻找文本片段的真正终点
    # 从 `end_index` 向后搜索，找到它所在段落的终点
    paragraph_end = len(text)
    for i in range(end_index, len(text)):
        if text[i:i+2] in paragraph_enders:
            paragraph_end = i + 2  # 段落的终点包含两个换行符
            break

    return paragraph_start, paragraph_end, text[paragraph_start:paragraph_end]

if __name__ == "__main__":


    # 读取配置文件
    if not os.path.exists('config.json'):
        print("错误: 找不到配置文件 'config.json'")
        exit(1)
    
    config = json.load(open('config.json', 'r', encoding='utf-8'))

    clipping_json_path = config["clippings_to_pre_correction"]["clipping_json_path"]

    book_title_in_clipping = config["clippings_to_pre_correction"]["book_title_in_clipping"]

    book_path = config["clippings_to_pre_correction"]["book_path"]

    with open(clipping_json_path , "r" ,encoding="utf-8" ) as f :
        clipping_json = json.load(f)

    with open(book_path,"r",encoding="utf-8") as f :
        text = f.read()

    total_chars = len(text)

    total_locs = config["clippings_to_pre_correction"]["locations"]["end"]

    start_locs = config["clippings_to_pre_correction"]["locations"]["start"]

    search_window = int(config["clippings_to_pre_correction"]["search_window_in_percentage"] * total_chars)

    select_clipping = clipping_json[book_title_in_clipping] if book_title_in_clipping in clipping_json else None

    if not select_clipping:
        print(f"错误: 在标注文件中未找到书名 '{book_title_in_clipping}' 的标注。")
        exit(1)
    
    print(f"正在处理书名: '{book_title_in_clipping}' 的标注...")

    pos = []

    for clipping in select_clipping:

        pos_c = find_text_in_source_txt(clipping, text, total_chars, total_locs, start_locs, search_window)

        pos.append(pos_c)


    if None in pos:
        print("错误: 在源文件中未能找到所有标注的匹配文本。")
        print("请手动检查，或者设置更大的 search_window_in_percentage。")
        exit(1)

    print("所有标注文本已成功定位。")

    ans = []
    for i in range(len(pos)):

        sentence_start, sentence_end, sentence_text = find_sentences_by_range(text, pos[i])
        paragraph_start, paragraph_end, paragraph_text = find_paragraph_by_range(text, pos[i])


        ans.append({
            'id' : i,
            'location_start' : select_clipping[i]['location_start'],
            'position_start' : pos[i][0],
            'position_end' : pos[i][1],
            'text' : select_clipping[i]['text'],
            'sentence' : {
                'start' : sentence_start,
                'end' : sentence_end,
                'text' : sentence_text
            },
            'paragraph' : {
                'start' : paragraph_start,
                'end' : paragraph_end,
                'text' : paragraph_text 
            }
        })

    pre_correction_json_path = config["clippings_to_pre_correction"]["pre_correction_json_path"]

    with open(pre_correction_json_path,'w', encoding='utf-8') as json_file:
        json.dump(ans, json_file, ensure_ascii=False, indent=4)






