import os
import json
import requests
from typing import Callable,Union

def select_clippings_sentence(clippings_list : dict):
    """
    选择需要发送给llm的字段, id, text, sentence
    """
    selected_clippings = []
    for clipping in clippings_list:
        selected_clipping = {
            "id" : clipping["id"],
            "text" : clipping["text"],
            "sentence" : clipping["sentence"]["text"]
        }
        selected_clippings.append(selected_clipping)
    return selected_clippings

def select_clippings_explanation(clippings_list : dict):
    """
    选择需要发送给llm的字段,id, text, explanation
    """
    selected_clippings = []
    for clipping in clippings_list:
        selected_clipping = {
            "id" : clipping["id"],
            "text" : clipping["text"],
            "explanation" : clipping["explanation"]
        }
        selected_clippings.append(selected_clipping)
    return selected_clippings

def select_output_snippet(result : dict, pre_correction : dict):

    """
    从模型返回的结果中选择需要的字段
    """
    return {
            'id': pre_correction['id'],
            "location_start": pre_correction['location_start'],
            "position_start": pre_correction['position_start'],
            "position_end": pre_correction['position_end'],
            'is_corrected': result['is_corrected'],
            'original_text': result['original_text'],
            'corrected_text': result['corrected_text'],
            'sentence': pre_correction['sentence'],
            "paragraph": pre_correction['paragraph'],
            'explanation': result['explanation'],
            "error_outside_snippet": result['error_outside_snippet']
            }

def select_output_nosnippet(result : dict, pre_correction : dict):
    """
    从模型返回的结果中选择需要的字段
    """
    return {
            'id': pre_correction['id'],
            "location_start": pre_correction['location_start'],
            "position_start": pre_correction['position_start'],
            "position_end": pre_correction['position_end'],
            'is_corrected': result['is_corrected'],
            'original_text': result['original_text'],
            'corrected_text': result['corrected_text'],
            'sentence': pre_correction['sentence'],
            "paragraph": pre_correction['paragraph'],
            'explanation': pre_correction['explanation'],
            "error_outside_snippet": False
            }


# 对于输入的json，筛选输出的字段
def filter_json(input : Union[dict,list] ):
    """ 
    筛选最后的输出，使得其方便人工审阅
    
    """
    output = []

    for input_item in  input : 
        output_item = {
            "id" : input_item["id"],
            "position_start" : input_item["position_start"],
            "position_end" : input_item["position_end"],
            "is_corrected": input_item["is_corrected"],
            "original_text": input_item["original_text"],
            "corrected_text": input_item["corrected_text"],
            "sentence": input_item["sentence"]["text"],
            "explanation": input_item["explanation"]
        }

        output.append(output_item)
    output.sort(key = lambda x: int(x["id"]),reverse=False)
    return output


def create_batch_prompt(llm_prompt : str, clippings_list : Union[dict,list], select_function : Callable):
    """
    V3版本：增加一个字段，用于标记片段之外是否存在错误。
    """
    tasks_json_string = json.dumps(select_function(clippings_list), indent=2, ensure_ascii=False)


    prompt_template = llm_prompt.replace("INPUT_TASKS_JSON_STRING", tasks_json_string)


    return prompt_template


def process_batch_with_custom_api(llm_settings : dict ,clippings_list : Union[dict,list], select_function : Callable):
    """
    调用自定义API，一次性处理一批校对任务。
    """
    # (这部分与之前的单次请求代码基本相同)
    url = llm_settings["llm_api_url"]
    api_key = llm_settings["llm_api_key"]


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 1. 使用新的函数创建批处理提示词
    final_prompt = create_batch_prompt(llm_settings["llm_prompt"],clippings_list,select_function)

    data = {
        "model": llm_settings["llm_model"],
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": llm_settings["llm_temperature"],
        "response_format": {"type": "json_object"}
    }

    print(f"正在向API发送包含 {len(clippings_list)} 个任务的批处理请求...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=180) # 批处理可能耗时更长，增加超时
        response.raise_for_status()
        
        response_data = response.json()
        #print(response_data)
        # 模型返回的content现在应该是一个包含结果列表的JSON字符串
        # 注意：这里的返回格式是我们在Prompt里要求的，所以路径可能需要调整
        # 很多模型会返回 {"results": [...]}, 我们假设它直接返回列表字符串
        # for gemini
        json_string = response_data['choices'][0]['message']['content']
        json_object = json.loads(json_string)

        if "results" in json_object:
            json_object = json_object["results"]


        # 解析这个列表字符串
        return json_object

    except Exception as e:
        print(f"批处理请求失败: {e}")
        return None
    

def get_correction(llm_settings : dict , pre_correction_list : Union[dict,list],  task_per_request : int, select_function : Callable , output_function : Callable):
    
    total_tasks = len(pre_correction_list)
    print(f"总共有 {total_tasks} 个任务需要处理。")

    number_of_requests = (total_tasks + task_per_request - 1) // task_per_request
    print(f"将分成 {number_of_requests} 次请求来处理这些任务。")

    total_result = []
    failed_corrections = []

    for i in range(number_of_requests):
        start_index = i * task_per_request
        end_index = min(start_index + task_per_request, total_tasks)
        clippings_list = pre_correction_list[start_index:end_index]

        correction_results = process_batch_with_custom_api(llm_settings, clippings_list, select_function)

        if correction_results is None:
            print(f"第 {i+1} 次请求失败，终止处理。")
            failed_corrections.extend(clippings_list)
            continue

        for j in range(len(correction_results)):
            result = correction_results[j]
            pre_correction = clippings_list[j]

            # 检测id,is_corrected,original_text,corrected_text是否存在

            if int(pre_correction['id']) != int(result['id']):
                print(f"错误: 预校对ID {pre_correction['id']} 与结果ID {result['id']} 不匹配。")
                failed_corrections.append(pre_correction)
                continue

            if pre_correction['text'] != result['original_text']:
                print(f"错误: 预校对文本与结果文本不匹配。预校对文本: {pre_correction['text']}, 结果文本: {result['original_text']}")
                failed_corrections.append(pre_correction)
                continue


            total_result.append(output_function(result, pre_correction))
            
    return total_result, failed_corrections


def process_error_data_split(data):
    """
    处理文本错误数据，返回处理后的结果和被筛掉的原始数据。

    Args:
        data (list): 包含错误信息的字典列表。

    Returns:
        tuple: 一个包含两个列表的元组 (processed_data, remaining_data)
               - processed_data: 处理和转换后的新字典列表。
               - remaining_data: 输入数据中未被处理的原始项列表。
    """
    processed_items = []
    
    # 使用一个集合来记录所有被处理过的句子的文本，以便后续筛选剩余项
    used_sentence_texts = set()

    # --- 步骤 1: 按句子文本对所有项进行分组 ---
    sentence_groups = {}
    for item in data:
        sentence_info = item.get('sentence', {})
        sentence_text = sentence_info.get('text')
        
        if sentence_text is None:
            continue

        if sentence_text not in sentence_groups:
            sentence_groups[sentence_text] = []
        sentence_groups[sentence_text].append(item)

    # --- 步骤 2: 处理满足条件2的分组（不同id，相同句子）---
    for sentence_text, items in sentence_groups.items():
        unique_ids = {item['id'] for item in items}

        if len(unique_ids) > 1:
            # 条件2：不同id下有相同的句子
            print(f"处理句子: {sentence_text}，包含 {len(items)} 个不同的id")
            base_item = items[0]
            all_explanations = "; ".join(sorted(list({item['explanation'] for item in items})))
            
            new_item = {
                "id": base_item['id'],
                "location_start": base_item['location_start'],
                "position_start": base_item['sentence']['start'],
                "position_end": base_item['sentence']['end'],
                "text": base_item['sentence']['text'],
                "sentence": base_item['sentence'],
                "paragraph": base_item['paragraph'],
                "explanation": all_explanations
            }
            processed_items.append(new_item)
            # 标记该句子已被使用
            used_sentence_texts.add(sentence_text)

    # --- 步骤 3: 处理满足条件1的项（error_outside_snippet为true）---
    for item in data:
        sentence_info = item.get('sentence', {})
        sentence_text = sentence_info.get('text')

        if not sentence_text or sentence_text in used_sentence_texts:
            # 如果句子为空或已被条件2处理过，则跳过
            continue

        if item.get("error_outside_snippet") is True:
            # 条件1
            new_item = {
                "id": item['id'],
                "location_start": item['location_start'],
                "position_start": item['sentence']['start'],
                "position_end": item['sentence']['end'],
                "text": item['sentence']['text'],
                "sentence": item['sentence'],
                "paragraph": item['paragraph'],
                "explanation": item['explanation']
            }
            processed_items.append(new_item)
            # 标记该句子已被使用
            used_sentence_texts.add(sentence_text)
            
    # --- 步骤 4: 筛选出未被处理的原始数据 ---
    remaining_data = []
    for item in data:
        sentence_text = item.get('sentence', {}).get('text')
        if sentence_text not in used_sentence_texts:
            remaining_data.append(item)

    return processed_items, remaining_data

    
    

if __name__ == "__main__":


    # 读取配置文件
    if not os.path.exists('config.json'):
        print("错误: 找不到配置文件 'config.json'")
        exit(1)
    
    config = json.load(open('config.json', 'r', encoding='utf-8'))

    llm_settings = config["pre_correction_to_correction"]["llm_settings"]

    llm_settings_2 = config["pre_correction_to_correction"]["llm_settings_2"]

    pre_correction_json_path = config["pre_correction_to_correction"]["pre_correction_json_path"]

    correction_json_path = config["pre_correction_to_correction"]["correction_json_path"]

    re_correction_enabled = config["pre_correction_to_correction"]["re_correction_enabled"]

    with open(pre_correction_json_path, 'r', encoding='utf-8') as f:
        pre_correction_list = json.load(f)

    if not pre_correction_list:
        print("错误: 预校对列表为空，请检查输入文件。")
        exit(1)

    total_result, failed_corrections = get_correction(llm_settings, pre_correction_list, llm_settings["task_per_request"],select_clippings_sentence,select_output_snippet)
            

            
    if failed_corrections:
        print(f"处理完成，但有 {len(failed_corrections)} 个任务未能成功校对。")
        if re_correction_enabled:
            print("正在重新处理未成功校对的任务...")
            re_correction_results, re_failed_corrections = get_correction(llm_settings, failed_corrections, 5 ,select_clippings_sentence,select_output_snippet)
            failed_correction = re_failed_corrections
            total_result.extend(re_correction_results)

        else:
            print("未启用重新校对功能，已将失败的校对任务保存到 'failed_corrections.json'。")



    print(f"处理完成，共生成 {len(total_result)} 条校对结果。")

    # 合并重复的句子，并将进一步校对
    further_correction, total_result = process_error_data_split(total_result)

    if further_correction:
        print(f"对句子中有多处错误的情况，处理 {len(further_correction)} 条数据。")
        further_correction_results, further_failed_corrections = get_correction(llm_settings_2, further_correction, llm_settings_2["task_per_request"],select_clippings_explanation,select_output_nosnippet)
        
        if further_failed_corrections:
            print(f"对于多处错误的情况，有 {len(further_failed_corrections)} 条数据未能成功校对。")

            if re_correction_enabled:
                print("正在重新处理未成功校对的任务...")
                re_correction_results, re_failed_corrections = get_correction(llm_settings_2, further_failed_corrections, 5 ,select_clippings_explanation,select_output_nosnippet)
            
                further_failed_corrections = re_failed_corrections
                further_correction_results.extend(re_correction_results)
            
            failed_corrections.extend(further_failed_corrections)
        
        total_result.extend(further_correction_results)


    if failed_corrections:    
        with open('failed_corrections.json', 'w', encoding='utf-8') as f:
            json.dump(failed_corrections, f, ensure_ascii=False, indent=4)


    print(f"最终校对结果包含 {len(total_result)} 条数据。")

    with open(correction_json_path, 'w', encoding='utf-8') as f:
        json.dump(filter_json(total_result), f, ensure_ascii=False, indent=4)
            

        




    







    
