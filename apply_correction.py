# 读取correction.json文件，并对原文进行校正

import json
import os
def correct_text(original_text : str,correction : dict) :

    
    original_text_part = original_text[correction["position_start"]:correction["position_end"]]

    if correction["is_corrected"]:

        if original_text_part == correction["original_text"]:

            print(f"正在校正：{correction['original_text']} -> {correction['corrected_text']}")

            original_text = original_text[:correction["position_start"]] + correction["corrected_text"] + original_text[correction["position_end"]:]
        else:

            print("原文与校正内容不匹配！，跳过校正。")
            print(f"校正id: {correction['id']}")
            print(f"原文片段: {original_text_part}")
            print(f"预期片段: {correction['original_text']}")

    return original_text

if __name__ == "__main__":

    if not os.path.exists('config.json'):
        print("错误: 找不到配置文件 'config.json'")
        exit(1)

    config = json.load(open('config.json', 'r', encoding='utf-8'))

    book_path = config["correction_apply"]["book_path"]
    correction_json_path = config["correction_apply"]["correction_json_path"]
    output_path = config["correction_apply"]["output_path"]

    with open(correction_json_path, 'r', encoding='utf-8') as f:
        correction_list = json.load(f)

    if not correction_list:
        print("错误: 预校对列表为空，请检查输入文件。")
        exit(1)

    # 针对correction_list 按照 position_end 倒序排序
    correction_list.sort(key=lambda x: x["position_end"], reverse=True) 

    with open(book_path, 'r', encoding='utf-8') as f:
        original_text = f.read()

    for correction in correction_list:
        original_text = correct_text(original_text, correction)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(original_text)   